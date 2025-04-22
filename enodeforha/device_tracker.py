"""Device tracker platform for Enode integration."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_SELECTED_SENSORS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device tracker for Enode."""
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]

    if not coordinator.data:
        return

    vehicle_id = coordinator.vehicle_id
    selected_sensors = coordinator.selected_sensors

    # Only create the device tracker if it's selected
    if "location" in selected_sensors:
        async_add_entities([EnodeDeviceTracker(coordinator, vehicle_id)])


class EnodeDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Representation of an Enode vehicle tracker."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator, vehicle_id):
        """Initialize the tracker."""
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_unique_id = f"{vehicle_id}_tracker"
        self._attr_name = coordinator.data.get("information", {}).get(
            "displayName", f"Vehicle {vehicle_id[:8]}"
        )
        self._attr_device_info = coordinator.device_info.get(vehicle_id)

    @property
    def latitude(self):
        """Return latitude value of the device."""
        return self.coordinator.data.get("location", {}).get("latitude") or 0.0

    @property
    def longitude(self):
        """Return longitude value of the device."""
        return self.coordinator.data.get("location", {}).get("longitude") or 0.0

    @property
    def location_accuracy(self):
        """Return the gps accuracy of the device."""
        return self.coordinator.data.get("location", {}).get("accuracy") or 0.0

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        location_data = self.coordinator.data.get("location", {})
        last_updated_enode = location_data.get("lastUpdated")
        return {
            "last_updated_enode": last_updated_enode,
            "last_updated_ha": datetime.now().isoformat(timespec="seconds"),
        }

    async def handle_coordinator_update(self) -> None:
        """Manually trigger state update when coordinator updates."""
        await super().handle_coordinator_update()
        self.async_write_ha_state()