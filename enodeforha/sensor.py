"""Sensor platform for Enode integration."""
from __future__ import annotations
from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfTime,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_TOKEN_EXPIRY,
    TOKEN_EXPIRY_BUFFER,
    CONF_INTEGRATION_ID,
    CONF_VEHICLE_ID,
    CONF_CLIENT_ID,
    CONF_SELECTED_SENSORS,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Enode sensors from a config entry."""
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    
    if not coordinator.data:
        _LOGGER.warning(
            "No data available for vehicle %s during sensor setup",
            coordinator.vehicle_id
        )
        return

    vehicle_id = coordinator.vehicle_id
    vehicle_data = coordinator.data
    selected_sensors = coordinator.selected_sensors
    
    _LOGGER.debug(
        "Setting up sensors for vehicle %s (%s %s)",
        vehicle_data.get("information", {}).get("displayName", vehicle_id),
        vehicle_data.get("information", {}).get("brand", "Unknown"),
        vehicle_data.get("information", {}).get("model", "Unknown")
    )
    
    # Create a mapping of sensor types to their classes
    sensor_classes = {
        "battery_level": EnodeBatteryLevelSensor,
        "battery_capacity": EnodeBatteryCapacitySensor,
        "range": EnodeRangeSensor,
        "charge_rate": EnodeChargeRateSensor,
        "charge_time_remaining": EnodeChargeTimeRemainingSensor,
        "odometer": EnodeOdometerSensor,
        "charge_limit": EnodeChargeLimitSensor,
        "last_seen": EnodeLastSeenSensor,
        "token_renewal": EnodeTokenRenewalSensor,
        "vehicle_information": EnodeVehicleInfoSensor,
    }

    # Initialize the sensors that are selected
    sensors = []
    for sensor_type, sensor_class in sensor_classes.items():
        if sensor_type in selected_sensors:
            if sensor_type == "token_renewal":
                sensors.append(sensor_class(coordinator, vehicle_id, entry.entry_id))
            else:
                sensors.append(sensor_class(coordinator, vehicle_id))

    async_add_entities(sensors, update_before_add=True)

class EnodeSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Enode sensors."""

    def __init__(self, coordinator, vehicle_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_device_info = coordinator.device_info.get(vehicle_id)
        self._attr_has_entity_name = True
        self._attr_should_poll = False

    @property
    def available(self) -> bool:
        """Return True if vehicle is reachable."""
        return self.coordinator.data.get("isReachable", False)

class EnodeBatteryLevelSensor(EnodeSensorBase):
    """Representation of an Enode battery level sensor."""

    _attr_name = "Battery level"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, vehicle_id):
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_battery_level"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        charge_state = self.coordinator.data.get("chargeState")
        return charge_state.get("batteryLevel") if charge_state else None

class EnodeBatteryCapacitySensor(EnodeSensorBase):
    """Representation of an Enode battery capacity sensor."""

    _attr_name = "Battery capacity"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY_STORAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, vehicle_id):
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_battery_capacity"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        charge_state = self.coordinator.data.get("chargeState")
        return charge_state.get("batteryCapacity") if charge_state else None

class EnodeRangeSensor(EnodeSensorBase):
    """Representation of an Enode range sensor."""

    _attr_name = "Range"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, vehicle_id):
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_range"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        charge_state = self.coordinator.data.get("chargeState")
        return charge_state.get("range") if charge_state else None

class EnodeChargeRateSensor(EnodeSensorBase):
    """Representation of an Enode charge rate sensor."""

    _attr_name = "Charge rate"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, vehicle_id):
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_charge_rate"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        charge_state = self.coordinator.data.get("chargeState")
        return charge_state.get("chargeRate") if charge_state else None

class EnodeChargeTimeRemainingSensor(EnodeSensorBase):
    """Representation of an Enode charge time remaining sensor."""

    _attr_name = "Charge time remaining"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, vehicle_id):
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_charge_time_remaining"

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        charge_state = self.coordinator.data.get("chargeState")
        return charge_state.get("chargeTimeRemaining") if charge_state else None

class EnodeOdometerSensor(EnodeSensorBase):
    """Representation of an Enode odometer sensor."""

    _attr_name = "Odometer"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, vehicle_id):
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_odometer"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        odometer = self.coordinator.data.get("odometer")
        return odometer.get("distance") if odometer else None

class EnodeChargeLimitSensor(EnodeSensorBase):
    """Representation of an Enode charge limit sensor."""

    _attr_name = "Charge limit"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:battery-arrow-up"

    def __init__(self, coordinator, vehicle_id):
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_charge_limit"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        charge_state = self.coordinator.data.get("chargeState")
        return charge_state.get("chargeLimit") if charge_state else None

class EnodeLastSeenSensor(EnodeSensorBase):
    """Representation of an Enode last seen sensor."""

    _attr_name = "Last seen"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator, vehicle_id):
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_last_seen"

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        last_seen = self.coordinator.data.get("lastSeen")
        if not last_seen:
            return None
        return dt_util.parse_datetime(last_seen)

class EnodeVehicleInfoSensor(EnodeSensorBase):
    """Representation of an Enode vehicle information sensor."""

    _attr_name = "Vehicle Info"
    _attr_icon = "mdi:car-info"

    def __init__(self, coordinator, vehicle_id):
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_vehicle_info"
        self._attr_extra_state_attributes = {}
        self._last_refresh_time = None

    @property
    def native_value(self) -> str:
        """Return the display name as the main value."""
        info = self.coordinator.data.get("information", {})
        return info.get("displayName") or f"{info.get("brand")} {info.get("model")}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        data = self.coordinator.data
        info = data.get("information", {})
        odometer = data.get("odometer", {})
        
        last_seen = None
        if data.get("lastSeen"):
            last_seen = dt_util.parse_datetime(data["lastSeen"])

        if self.coordinator.last_update_success:
            self._last_refresh_time = dt_util.utcnow()
        
        return {
            "display_name": info.get("displayName") or f"{info.get("brand")} {info.get("model")}",
            "brand": info.get("brand"),
            "model": info.get("model"),
            "year": str(info.get("year")),
            "vin": info.get("vin"),
            "Enode id": data.get("id"),
            "Vehicle id": self._vehicle_id,
            "odometer": f"{odometer.get('distance')} {UnitOfLength.KILOMETERS}" if odometer.get("distance") is not None else None,
            "last_seen": last_seen.isoformat() if last_seen else None,
            "last_refresh": self._last_refresh_time.isoformat() if self._last_refresh_time else None,
        }

class EnodeTokenRenewalSensor(EnodeSensorBase):
    """Representation of a token renewal sensor."""
    
    _attr_name = "Token Renewal"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"
    
    def __init__(self, coordinator, vehicle_id, entry_id):
        """Initialize the sensor."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{coordinator._integration_id}_token_renewal_{entry_id}"
        self.entity_id = f"sensor.{DOMAIN}_{vehicle_id}_token_renewal"
        
    @property
    def available(self) -> bool:
        """Return True if token info is available."""
        if DOMAIN not in self.hass.data:
            return False
            
        token_info = self.hass.data[DOMAIN]["tokens"].get(self.coordinator._integration_id)
        return token_info is not None and CONF_TOKEN_EXPIRY in token_info

    @property
    def native_value(self) -> datetime | None:
        """Return the next scheduled renewal time."""
        if not self.available:
            return None
            
        token_info = self.hass.data[DOMAIN]["tokens"][self.coordinator._integration_id]
        expiry = token_info[CONF_TOKEN_EXPIRY]
        return dt_util.as_local(datetime.fromtimestamp(expiry - TOKEN_EXPIRY_BUFFER, tz=timezone.utc))

    @property
    def extra_state_attributes(self):
        """Return additional token information."""
        if not self.available:
            return None
            
        token_info = self.hass.data[DOMAIN]["tokens"][self.coordinator._integration_id]
        now = datetime.now(timezone.utc).timestamp()
        expiry_time = token_info[CONF_TOKEN_EXPIRY]
        next_renewal = expiry_time - TOKEN_EXPIRY_BUFFER

        # Count vehicles using this token
        vehicle_count = len([
            c for c in self.hass.data[DOMAIN]["coordinators"].values() 
            if c._integration_id == self.coordinator._integration_id
        ])

        return {
            "integration_id": self.coordinator._integration_id,
            "client_id": token_info.get(CONF_CLIENT_ID, ""),
            "token_expiry": dt_util.as_local(
                datetime.fromtimestamp(expiry_time, tz=timezone.utc)
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "renewal_status": "scheduled" if next_renewal > now else "pending",
            "next_renewal_in": f"{(next_renewal - now)/60:.1f} minutes" if next_renewal > now else "0 minutes",
            "scheduled": dt_util.as_local(
                datetime.fromtimestamp(next_renewal, tz=timezone.utc)
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "shared_across_vehicles": True,
            "vehicle_count": vehicle_count,
            "vehicles_using_token": [
                entry.data.get(CONF_VEHICLE_ID)
                for entry in self.hass.config_entries.async_entries(DOMAIN)
                if entry.data.get(CONF_INTEGRATION_ID) == self.coordinator._integration_id
            ]
        }