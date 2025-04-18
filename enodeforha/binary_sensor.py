"""Binary sensor platform for Enode integration."""
from __future__ import annotations
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Enode binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    
    if not coordinator.data:
        _LOGGER.warning(
            "No data available for vehicle %s during binary sensor setup",
            coordinator.vehicle_id
        )
        return

    vehicle_id = coordinator.vehicle_id
    vehicle_data = coordinator.data
    
    _LOGGER.debug(
        "Setting up binary sensors for vehicle %s (%s %s)",
        vehicle_data.get("information", {}).get("displayName", vehicle_id),
        vehicle_data.get("information", {}).get("brand", "Unknown"),
        vehicle_data.get("information", {}).get("model", "Unknown")
    )

    binary_sensors = [
        EnodePluggedInBinarySensor(coordinator, vehicle_id),
        EnodeChargingBinarySensor(coordinator, vehicle_id),
        EnodeFullyChargedBinarySensor(coordinator, vehicle_id),
        EnodeReachableBinarySensor(coordinator, vehicle_id),
    ]

    async_add_entities(binary_sensors)

class EnodeBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for Enode binary sensors."""

    def __init__(self, coordinator, vehicle_id):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_device_info = coordinator.device_info.get(vehicle_id)
        self._attr_has_entity_name = True
        self._attr_should_poll = False

    @property
    def available(self) -> bool:
        """Return True if vehicle is reachable."""
        return self.coordinator.data.get("isReachable", False)

class EnodePluggedInBinarySensor(EnodeBinarySensorBase):
    """Representation of an Enode plugged in binary sensor."""

    _attr_name = "Plugged in"
    _attr_device_class = BinarySensorDeviceClass.PLUG

    def __init__(self, coordinator, vehicle_id):
        """Initialize the binary sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_plugged_in"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        charge_state = self.coordinator.data.get("chargeState")
        return charge_state.get("isPluggedIn") if charge_state else None

class EnodeChargingBinarySensor(EnodeBinarySensorBase):
    """Representation of an Enode charging binary sensor."""

    _attr_name = "Charging"
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    def __init__(self, coordinator, vehicle_id):
        """Initialize the binary sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_charging"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        charge_state = self.coordinator.data.get("chargeState")
        return charge_state.get("isCharging") if charge_state else None

class EnodeFullyChargedBinarySensor(EnodeBinarySensorBase):
    """Representation of an Enode fully charged binary sensor."""

    _attr_name = "Fully charged"
    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, coordinator, vehicle_id):
        """Initialize the binary sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_fully_charged"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        charge_state = self.coordinator.data.get("chargeState")
        return charge_state.get("isFullyCharged") if charge_state else None

class EnodeReachableBinarySensor(EnodeBinarySensorBase):
    """Representation of an Enode reachable binary sensor."""

    _attr_name = "Reachable"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, vehicle_id):
        """Initialize the binary sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_reachable"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.coordinator.data.get("isReachable")