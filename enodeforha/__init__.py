"""The Enode integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed
)
from homeassistant.helpers import event

from .const import (
    DOMAIN,
    API_BASE_URL,
    API_VEHICLES_PATH,
    CONF_TOKEN_EXPIRY,
    CONF_VEHICLE_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    PLATFORMS,
    OAUTH_URL,
    CONF_INTEGRATION_ID,
    TOKEN_EXPIRY_BUFFER,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Enode integration."""
    hass.data.setdefault(DOMAIN, {
        "next_id": 1,
        "tokens": {},
        "renewal_tasks": {},
        "coordinators": {}
    })
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Enode from a config entry."""
    integration_id = entry.data[CONF_INTEGRATION_ID]
    
    if DOMAIN not in hass.data:
        await async_setup(hass, {})

    # Try to get token from storage or create new one if missing
    if integration_id not in hass.data[DOMAIN]["tokens"]:
        try:
            _LOGGER.debug("Attempting to create token for integration %s", integration_id)
            session = async_get_clientsession(hass)
            auth = aiohttp.BasicAuth(
                entry.data[CONF_CLIENT_ID],
                entry.data[CONF_CLIENT_SECRET]
            )
            
            async with session.post(
                OAUTH_URL,
                auth=auth,
                data={"grant_type": "client_credentials"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                token_data = await response.json()
                expiry_time = datetime.now(timezone.utc).timestamp() + 3600  # 1 hour validity
                
                token_info = {
                    CONF_CLIENT_ID: entry.data[CONF_CLIENT_ID],
                    CONF_CLIENT_SECRET: entry.data[CONF_CLIENT_SECRET],
                    CONF_ACCESS_TOKEN: token_data["access_token"],
                    CONF_TOKEN_EXPIRY: expiry_time
                }
                hass.data[DOMAIN]["tokens"][integration_id] = token_info
                _LOGGER.info("Successfully created token for integration %s", integration_id)
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during token creation for integration %s: %s", 
                         integration_id, str(err))
            raise ConfigEntryNotReady from err
        except Exception as err:
            _LOGGER.error("Failed to create token for integration %s: %s", 
                         integration_id, str(err), exc_info=True)
            return False

    coordinator = EnodeCoordinator(hass, entry, hass.data[DOMAIN]["tokens"][integration_id])
    
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Could not set up Enode integration: %s", err)
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator

    # Schedule initial token renewal
    expiry_time = hass.data[DOMAIN]["tokens"][integration_id][CONF_TOKEN_EXPIRY]
    await coordinator.schedule_token_renewal(expiry_time)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN]["coordinators"].pop(entry.entry_id)
        integration_id = entry.data[CONF_INTEGRATION_ID]
        
        # Clean up renewal task if this is the last coordinator using this integration
        if not any(
            c._integration_id == integration_id 
            for c in hass.data[DOMAIN]["coordinators"].values()
        ):
            if task := hass.data[DOMAIN]["renewal_tasks"].pop(integration_id, None):
                task()
            hass.data[DOMAIN]["tokens"].pop(integration_id, None)
        
        # Clean up domain data if no more coordinators
        if not hass.data[DOMAIN]["coordinators"]:
            hass.data.pop(DOMAIN)
    
    return unload_ok

class EnodeCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Enode data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, token_info: dict):
        """Initialize with shared token info."""
        update_interval = timedelta(
            seconds=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_VEHICLE_ID]}",
            update_interval=update_interval,
            update_method=self._async_update_data
        )
        self.entry = entry
        self.vehicle_id = entry.data[CONF_VEHICLE_ID]
        self._integration_id = entry.data[CONF_INTEGRATION_ID]
        self._token_info = token_info
        self._device_info: dict[str, DeviceInfo] = {}
        self._token_lock = asyncio.Lock()
        self._renewal_attempted = False

    @property
    def device_info(self) -> dict[str, DeviceInfo]:
        """Return the device info dictionary."""
        return self._device_info

    async def schedule_token_renewal(self, expiry_timestamp: float) -> None:
        """Schedule token renewal for 5 minutes before expiry."""
        renewal_time = datetime.fromtimestamp(
            expiry_timestamp - TOKEN_EXPIRY_BUFFER, 
            tz=timezone.utc
        )
        
        if self._integration_id in self.hass.data[DOMAIN]["renewal_tasks"]:
            self.hass.data[DOMAIN]["renewal_tasks"][self._integration_id]()
        
        self.hass.data[DOMAIN]["renewal_tasks"][self._integration_id] = event.async_track_point_in_time(
            self.hass,
            self.renew_token,
            renewal_time
        )
        
        _LOGGER.debug(
            "Next token renewal scheduled for %s",
            renewal_time.strftime("%Y-%m-%d %H:%M:%S")
        )

    async def renew_token(self, *_) -> None:
        """Renew the access token."""
        async with self._token_lock:
            try:
                session = async_get_clientsession(self.hass)
                auth = aiohttp.BasicAuth(
                    self._token_info[CONF_CLIENT_ID],
                    self._token_info[CONF_CLIENT_SECRET]
                )
                
                async with session.post(
                    OAUTH_URL,
                    auth=auth,
                    data={"grant_type": "client_credentials"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    response.raise_for_status()
                    token_data = await response.json()
                    
                    expiry_time = datetime.now(timezone.utc).timestamp() + 3600  # 1 hour validity
                    
                    new_token_info = {
                        **self._token_info,
                        CONF_ACCESS_TOKEN: token_data["access_token"],
                        CONF_TOKEN_EXPIRY: expiry_time
                    }
                    
                    self.hass.data[DOMAIN]["tokens"][self._integration_id] = new_token_info
                    self._token_info = new_token_info
                    await self.schedule_token_renewal(expiry_time)
                    self._renewal_attempted = False
                    
            except Exception as err:
                _LOGGER.error("Token renewal failed: %s", str(err))
                raise

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Enode API."""
        headers = {
            "Authorization": f"Bearer {self._token_info[CONF_ACCESS_TOKEN]}",
            "Accept": "application/json"
        }
        
        try:
            session = async_get_clientsession(self.hass)
            url = f"{API_BASE_URL}{API_VEHICLES_PATH}"
            
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 401 and not self._renewal_attempted:
                    # Single retry on 401
                    self._renewal_attempted = True
                    await self.renew_token()
                    
                    # Retry with new token
                    headers["Authorization"] = f"Bearer {self._token_info[CONF_ACCESS_TOKEN]}"
                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as retry_response:
                        retry_response.raise_for_status()
                        result = await retry_response.json()
                else:
                    response.raise_for_status()
                    result = await response.json()

            # Reset renewal attempt flag on successful request
            self._renewal_attempted = False
            
            vehicle_data = next(
                (v for v in result.get('data', []) if v.get('id') == self.vehicle_id),
                None
            )

            if not vehicle_data:
                raise ValueError(f"Vehicle {self.vehicle_id} not found in API response")

            # Update device info
            info = vehicle_data.get('information', {})
            self._device_info = {
                self.vehicle_id: DeviceInfo(
                    identifiers={(DOMAIN, self.vehicle_id)},
                    name=info.get('displayName', f"Enode {self.vehicle_id[:8]}"),
                    manufacturer=info.get('brand'),
                    model=info.get('model'),
                    hw_version=str(info.get('year')) if info.get('year') else 'Unknown',
                    serial_number=info.get('vin') if info.get('vin') else 'Unknown',
                )
            }
            
            return vehicle_data

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error updating data for vehicle %s: %s", 
                         self.vehicle_id, str(err))
            raise UpdateFailed(f"Network error: {err}") from err
        except Exception as err:
            _LOGGER.error("Error updating data for vehicle %s: %s", 
                         self.vehicle_id, str(err), exc_info=True)
            raise UpdateFailed(f"Error updating data: {err}") from err