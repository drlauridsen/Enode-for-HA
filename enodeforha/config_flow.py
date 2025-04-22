"""Config flow for Enode integration."""
from __future__ import annotations
import aiohttp
import logging
from typing import Any
from datetime import datetime, timezone
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ACCESS_TOKEN,
    CONF_TOKEN_EXPIRY,
    CONF_VEHICLE_ID,
    CONF_UPDATE_INTERVAL,
    CONF_DEBUG_NOTIFICATIONS,
    CONF_SELECTED_SENSORS,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_DEBUG_NOTIFICATIONS,
    DEFAULT_SELECTED_SENSORS,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
    API_BASE_URL,
    API_VEHICLES_PATH,
    OAUTH_URL,
    CONF_INTEGRATION_ID,
    TOKEN_EXPIRY_BUFFER,
    AVAILABLE_SENSORS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_CLIENT_ID): str,
    vol.Required(CONF_CLIENT_SECRET): str,
})

def is_token_valid(token_info: dict[str, Any]) -> bool:
    """Check if token is valid and not near expiry."""
    if not token_info or CONF_TOKEN_EXPIRY not in token_info:
        return False
    
    current_time = datetime.now(timezone.utc).timestamp()
    expiry_time = token_info[CONF_TOKEN_EXPIRY]
    return current_time < (expiry_time - TOKEN_EXPIRY_BUFFER)

async def validate_credentials(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate credentials with Enode API."""
    session = async_get_clientsession(hass)
    auth = aiohttp.BasicAuth(data[CONF_CLIENT_ID], data[CONF_CLIENT_SECRET])
    
    try:
        async with session.post(
            OAUTH_URL,
            auth=auth,
            data={"grant_type": "client_credentials"},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status != 200:
                raise ValueError(f"API returned status {response.status}")
            
            token_data = await response.json()
            expiry_time = datetime.now(timezone.utc).timestamp() + int(token_data.get("expires_in", 3600))
            
            return {
                CONF_CLIENT_ID: data[CONF_CLIENT_ID],
                CONF_CLIENT_SECRET: data[CONF_CLIENT_SECRET],
                CONF_ACCESS_TOKEN: token_data["access_token"],
                CONF_TOKEN_EXPIRY: expiry_time
            }
    except Exception as err:
        raise ValueError(f"Authentication failed: {err}") from err

async def get_vehicles(hass: HomeAssistant, access_token: str) -> list[dict[str, Any]]:
    """Get list of available vehicles from Enode API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    session = async_get_clientsession(hass)
    url = f"{API_BASE_URL}{API_VEHICLES_PATH}"
    
    async with session.get(
        url,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=10)
    ) as response:
        response.raise_for_status()
        data = await response.json()
        return data.get("data", [])

class EnodeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Enode."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._vehicles: list[dict[str, Any]] = []
        self._token_info: dict[str, Any] = {}
        self._vehicle: dict[str, Any] = {}
        self._integration_id: str = None
        self._interval_data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> EnodeOptionsFlow:
        """Get the options flow for this handler."""
        return EnodeOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                if DOMAIN not in self.hass.data:
                    self.hass.data[DOMAIN] = {
                        "next_id": 1,
                        "tokens": {},
                        "renewal_tasks": {},
                        "coordinators": {}
                    }

                existing_entries = [
                    entry for entry in self.hass.config_entries.async_entries(DOMAIN)
                    if entry.data.get(CONF_CLIENT_ID) == user_input[CONF_CLIENT_ID]
                ]
                
                if existing_entries:
                    self._integration_id = existing_entries[0].data[CONF_INTEGRATION_ID]
                    existing_token = self.hass.data[DOMAIN]["tokens"].get(self._integration_id)
                    
                    if existing_token and is_token_valid(existing_token):
                        _LOGGER.debug("Reusing existing valid token for integration %s", self._integration_id)
                        self._token_info = existing_token
                    else:
                        _LOGGER.debug("Existing token for integration %s is invalid or expired, creating new token", self._integration_id)
                        self._token_info = await validate_credentials(self.hass, user_input)
                        self.hass.data[DOMAIN]["tokens"][self._integration_id] = self._token_info
                else:
                    self._integration_id = f"{DOMAIN}_{self.hass.data[DOMAIN]['next_id']}"
                    self.hass.data[DOMAIN]["next_id"] += 1
                    self._token_info = await validate_credentials(self.hass, user_input)
                    self.hass.data[DOMAIN]["tokens"][self._integration_id] = self._token_info
                    _LOGGER.debug("Created new integration %s", self._integration_id)
                
                try:
                    self._vehicles = await get_vehicles(
                        self.hass,
                        self._token_info[CONF_ACCESS_TOKEN]
                    )
                except Exception as err:
                    _LOGGER.error("Failed to get vehicles with token: %s", err)
                    if existing_entries and self._token_info == existing_token:
                        _LOGGER.debug("Existing token failed, creating new token")
                        self._token_info = await validate_credentials(self.hass, user_input)
                        self.hass.data[DOMAIN]["tokens"][self._integration_id] = self._token_info
                        self._vehicles = await get_vehicles(
                            self.hass,
                            self._token_info[CONF_ACCESS_TOKEN]
                        )
                
                if not self._vehicles:
                    return self.async_abort(reason="no_vehicles")
                
                return await self.async_step_vehicle()
                
            except Exception as err:
                _LOGGER.error("Authentication failed: %s", err, exc_info=True)
                errors["base"] = "invalid_auth" if isinstance(err, ValueError) else "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors
        )

    async def async_step_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let user select a vehicle to configure."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._vehicle = next(v for v in self._vehicles if v["id"] == user_input[CONF_VEHICLE_ID])
            await self.async_set_unique_id(user_input[CONF_VEHICLE_ID])
            self._abort_if_unique_id_configured()
            return await self.async_step_interval()

        current_entries = self.hass.config_entries.async_entries(DOMAIN)
        configured_vehicle_ids = {
            entry.data.get(CONF_VEHICLE_ID) for entry in current_entries
        }

        vehicle_options = {
            v["id"]: f"{v.get('information', {}).get('displayName', 'Unknown')} ({v.get('information', {}).get('brand', 'Unknown')})"
            for v in self._vehicles
            if v["id"] not in configured_vehicle_ids
        }

        if not vehicle_options:
            return self.async_abort(reason="no_vehicles_available")

        return self.async_show_form(
            step_id="vehicle",
            data_schema=vol.Schema({
                vol.Required(CONF_VEHICLE_ID): vol.In(vehicle_options)
            }),
            errors=errors
        )

    async def async_step_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the update interval configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._interval_data = user_input
            return await self.async_step_sensors()

        data_schema = vol.Schema({
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=DEFAULT_UPDATE_INTERVAL
            ): vol.All(
                cv.positive_int,
                vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                description="update_interval_description"
            ),
            vol.Required(
                CONF_DEBUG_NOTIFICATIONS,
                default=DEFAULT_DEBUG_NOTIFICATIONS
            ): bool
        })

        return self.async_show_form(
            step_id="interval",
            data_schema=data_schema,
            description_placeholders={
                "min_value": str(MIN_UPDATE_INTERVAL),
                "max_value": str(MAX_UPDATE_INTERVAL),
                "default_value": str(DEFAULT_UPDATE_INTERVAL),
                "debug_help": "Aktiver for at få detaljerede notifikationer til fejlfinding"
            },
            errors=errors
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle sensor selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Always include required sensors
            selected_sensors = list(set(user_input.get(CONF_SELECTED_SENSORS, []) + 
                                 ["token_renewal", "vehicle_information"]))
            
            vehicle_info = self._vehicle.get('information', {})
            title = f"Enode {vehicle_info.get('displayName', 'Vehicle')}"
            
            return self.async_create_entry(
                title=title,
                data={
                    CONF_INTEGRATION_ID: self._integration_id,
                    CONF_CLIENT_ID: self._token_info[CONF_CLIENT_ID],
                    CONF_CLIENT_SECRET: self._token_info[CONF_CLIENT_SECRET],
                    CONF_VEHICLE_ID: self._vehicle["id"],
                },
                options={
                    CONF_UPDATE_INTERVAL: self._interval_data[CONF_UPDATE_INTERVAL],
                    CONF_DEBUG_NOTIFICATIONS: self._interval_data[CONF_DEBUG_NOTIFICATIONS],
                    CONF_SELECTED_SENSORS: selected_sensors
                }
            )

        sensors = {k: v for k, v in AVAILABLE_SENSORS.items()}
        
        return self.async_show_form(
            step_id="sensors",
            data_schema=vol.Schema({
                vol.Required(CONF_SELECTED_SENSORS, 
                           default=list(sensors.keys())): cv.multi_select(sensors)
            }),
            errors=errors
        )

class EnodeOptionsFlow(config_entries.OptionsFlow):
    """Handle Enode options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._current_interval = config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            DEFAULT_UPDATE_INTERVAL
        )
        self._current_debug = config_entry.options.get(
            CONF_DEBUG_NOTIFICATIONS,
            DEFAULT_DEBUG_NOTIFICATIONS
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                update_interval = user_input[CONF_UPDATE_INTERVAL]
                if not MIN_UPDATE_INTERVAL <= update_interval <= MAX_UPDATE_INTERVAL:
                    errors["base"] = "invalid_update_interval"
                else:
                    return self.async_create_entry(
                        title="",
                        data={
                            CONF_UPDATE_INTERVAL: update_interval,
                            CONF_DEBUG_NOTIFICATIONS: user_input[CONF_DEBUG_NOTIFICATIONS],
                            # Keep the existing selected sensors from the config entry
                            CONF_SELECTED_SENSORS: self._config_entry.options.get(CONF_SELECTED_SENSORS, DEFAULT_SELECTED_SENSORS)
                        }
                    )
            except Exception:
                _LOGGER.exception("Unexpected error saving options")
                errors["base"] = "unknown"

        data_schema = vol.Schema({
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=self._current_interval
            ): vol.All(
                cv.positive_int,
                vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                description="update_interval_description"
            ),
            vol.Required(
                CONF_DEBUG_NOTIFICATIONS,
                default=self._current_debug
            ): bool
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            description_placeholders={
                "min_value": str(MIN_UPDATE_INTERVAL),
                "max_value": str(MAX_UPDATE_INTERVAL),
                "current_value": str(self._current_interval),
                "debug_help": "Aktiver for at få detaljerede notifikationer til fejlfinding"
            },
            errors=errors
        )