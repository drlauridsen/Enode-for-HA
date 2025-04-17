"""Switch platform for Enode integration."""
# Updated: 2025-04-13 15:31:54 by drlauridsen

from __future__ import annotations

from typing import Any
import logging
from datetime import datetime, timezone

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components import persistent_notification
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    API_BASE_URL,
    API_VEHICLES_PATH,
    API_CHARGING,
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET
)

_LOGGER = logging.getLogger(__name__)

class EnodeStateCondition(Exception):
    """Represents a normal state condition that should not be treated as an error."""

@callback
def handle_state_condition(func):
    """Decorator to handle state conditions without logging errors."""
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except EnodeStateCondition as condition:
            # Return False to indicate the operation didn't complete, but not due to an error
            return False
    return wrapper

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Enode switches from a config entry."""
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    
    if not coordinator.data:
        _LOGGER.warning("No data available for vehicle %s", coordinator.vehicle_id)
        return

    vehicle_id = coordinator.vehicle_id
    vehicle_data = coordinator.data
    
    switches = []
    capabilities = vehicle_data.get("capabilities", {})
    
    if capabilities.get("smartCharging", {}).get("isCapable", False):
        switches.append(EnodeSmartChargingSwitch(coordinator, vehicle_id))
    
    if capabilities.get("startCharging", {}).get("isCapable", False):
        switches.append(EnodeChargeControlSwitch(coordinator, vehicle_id))
    
    async_add_entities(switches)

class EnodeSwitchBase(CoordinatorEntity, SwitchEntity):
    """Base class for Enode switches."""

    _attr_assumed_state = True
    _attr_attribution = "Data provided by Enode"

    def __init__(self, coordinator: Any, vehicle_id: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_device_info = coordinator.device_info.get(vehicle_id)
        self._attr_has_entity_name = True
        self._local_state = None
        self._attr_should_poll = False
        self._last_update = dt_util.utcnow()
        self._last_action = None

    @property
    def available(self) -> bool:
        """Return True if vehicle is reachable."""
        return self.coordinator.data.get("isReachable", False)

    def _get_headers(self) -> dict:
        """Get authorization headers using shared token."""
        token_info = self.hass.data[DOMAIN]["tokens"].get(self.coordinator._integration_id)
        return {
            "Authorization": f"Bearer {token_info[CONF_ACCESS_TOKEN]}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def _show_message(self, message: str, is_error: bool = False) -> None:
        """Show a message to the user.
        
        Args:
            message: The message to show.
            is_error: Whether this is an error message. If True, logs as error,
                     if False, logs as debug.
        """
        notification_id = f"enode_{self._vehicle_id}_{self._attr_name.lower().replace(' ', '_')}"
        
        if is_error:
            _LOGGER.error(message)
        else:
            _LOGGER.debug(message)

        persistent_notification.async_create(
            self.hass,
            message,
            title=f"Enode {self._attr_name}",
            notification_id=notification_id
        )

class EnodeSmartChargingSwitch(EnodeSwitchBase):
    """Representation of an Enode smart charging switch."""

    _attr_name = "Smart charging"
    _attr_icon = "mdi:auto-mode"

    def __init__(self, coordinator: Any, vehicle_id: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_smart_charging"

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if self._local_state is not None:
            return self._local_state
            
        policy = self.coordinator.data.get("smartChargingPolicy")
        return policy.get("isEnabled") if policy else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "last_update": self._last_update.isoformat(),
            "last_action": self._last_action,
            "policy_status": self.coordinator.data.get("smartChargingPolicy", {}).get("status"),
        }

    @handle_state_condition
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self.is_on:
            message = "Smart charging is already enabled"
            await self._show_message(message)
            raise EnodeStateCondition(message)

        self._local_state = True
        self._last_action = "enable"
        self.async_write_ha_state()
        await self._set_smart_charging(True)
        return True

    @handle_state_condition
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self.is_on is False:
            message = "Smart charging is already disabled"
            await self._show_message(message)
            raise EnodeStateCondition(message)

        self._local_state = False
        self._last_action = "disable"
        self.async_write_ha_state()
        await self._set_smart_charging(False)
        return True

    async def _set_smart_charging(self, state: bool) -> None:
        """Make API call to set smart charging state."""
        try:
            session = async_get_clientsession(self.hass)
            url = f"{API_BASE_URL}{API_VEHICLES_PATH}/{self._vehicle_id}/smart-charging"
            
            async with session.post(
                url,
                headers=self._get_headers(),
                json={"isEnabled": state},
                timeout=15
            ) as response:
                if response.status == 400:
                    error_data = await response.json()
                    error_message = error_data.get('message', 'Unknown error')
                    message = f"Cannot {'enable' if state else 'disable'} smart charging: {error_message}"
                    await self._show_message(message)
                    raise EnodeStateCondition(message)
                
                response.raise_for_status()
                self._local_state = None
                self._last_update = dt_util.utcnow()
                await self.coordinator.async_request_refresh()
                
        except Exception as err:
            self._local_state = None
            self.async_write_ha_state()
            message = f"Error setting smart charging: {str(err)}"
            await self._show_message(message, is_error=True)
            raise HomeAssistantError(message)

class EnodeChargeControlSwitch(EnodeSwitchBase):
    """Representation of an Enode charge control switch."""

    _attr_name = "Charge control"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator: Any, vehicle_id: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_charge_control"

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if self._local_state is not None:
            return self._local_state
            
        charge_state = self.coordinator.data.get("chargeState")
        return charge_state.get("isCharging") if charge_state else None

    @property
    def available(self) -> bool:
        """Return True if switch can be operated."""
        # First check if vehicle is reachable
        if not super().available:
            return False

        charge_state = self.coordinator.data.get("chargeState", {})
        
        # Check if plugged in status is known
        if charge_state.get("isPluggedIn") is None:
            return False
            
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        charge_state = self.coordinator.data.get("chargeState", {})
        return {
            "last_update": self._last_update.isoformat(),
            "last_action": self._last_action,
            "is_plugged_in": charge_state.get("isPluggedIn", False),
            "is_fully_charged": charge_state.get("isFullyCharged", False),
            "battery_level": charge_state.get("batteryLevel"),
            "target_charge_level": charge_state.get("chargeLimit"),
            "charge_rate": charge_state.get("chargeRate"),
            "chargeTimeRemaining": charge_state.get("chargeTimeRemaining"),
        }

    def _can_start_charging(self) -> tuple[bool, str]:
        """Check if charging can be started."""
        charge_state = self.coordinator.data.get("chargeState", {})
        
        # Check if already charging
        if charge_state.get("isCharging"):
            return False, "Vehicle is already charging"
            
        # Check if plugged in
        if not charge_state.get("isPluggedIn"):
            return False, "Vehicle is not plugged in"
            
        # Check if fully charged
        if charge_state.get("isFullyCharged"):
            return False, "Vehicle is already fully charged"
            
        # Check battery level against target
        battery_level = charge_state.get("batteryLevel")
        target_level = charge_state.get("chargeLimit")
        if battery_level is not None and battery_level >= target_level:
            return False, f"Battery level ({battery_level}%) is at or above target ({target_level}%)"
            
        return True, ""

    def _can_stop_charging(self) -> tuple[bool, str]:
        """Check if charging can be stopped."""
        charge_state = self.coordinator.data.get("chargeState", {})
        
        # Check if charge state is available
        if charge_state is None:
            return False, "Unable to determine charging status"
        
        # Check if actually charging
        if not charge_state.get("isCharging"):
            # Add more context if available
            if not charge_state.get("isPluggedIn"):
                return False, "Vehicle is not plugged in"
            elif charge_state.get("isFullyCharged"):
                return False, "Vehicle is fully charged"
            else:
                return False, "Vehicle is not currently charging"
            
        return True, ""

    @handle_state_condition
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on (start charging)."""
        can_start, reason = self._can_start_charging()
        if not can_start:
            message = f"Cannot start charging: {reason}"
            await self._show_message(message)
            raise EnodeStateCondition(message)

        self._local_state = True
        self._last_action = "start"
        self.async_write_ha_state()
        await self._control_charging("START")
        return True

    @handle_state_condition
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off (stop charging)."""
        can_stop, reason = self._can_stop_charging()
        if not can_stop:
            message = f"Cannot stop charging: {reason}"
            await self._show_message(message)
            raise EnodeStateCondition(message)

        self._local_state = False
        self._last_action = "stop"
        self.async_write_ha_state()
        await self._control_charging("STOP")
        return True

    async def _control_charging(self, action: str) -> None:
        """Make API call to control charging."""
        try:
            session = async_get_clientsession(self.hass)
            url = f"{API_BASE_URL}{API_VEHICLES_PATH}/{self._vehicle_id}{API_CHARGING}"
            
            async with session.post(
                url,
                headers=self._get_headers(),
                json={"action": action},
                timeout=15
            ) as response:
                if response.status == 400:
                    error_data = await response.json()
                    error_message = error_data.get('message', 'Unknown error')
                    message = f"Cannot {action.lower()} charging: {error_message}"
                    await self._show_message(message)
                    raise EnodeStateCondition(message)
                
                response.raise_for_status()
                self._local_state = None
                self._last_update = dt_util.utcnow()
                await self.coordinator.async_request_refresh()
                
        except Exception as err:
            self._local_state = None
            self.async_write_ha_state()
            message = f"Error controlling charging: {str(err)}"
            await self._show_message(message, is_error=True)
            raise HomeAssistantError(message)