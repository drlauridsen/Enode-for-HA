"""Constants for the Enode integration."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
)

class Environment(Enum):
    """Enum for Enode environments."""
    SANDBOX = "sandbox"
    PRODUCTION = "production"

# Switch environments by uncommenting the one you want:
#CURRENT_ENVIRONMENT = Environment.SANDBOX
CURRENT_ENVIRONMENT = Environment.PRODUCTION  # Uncomment for production

# Base URL parts
BASE_API_URL = "enode-api.{domain}.enode.io"
BASE_OAUTH_URL = "oauth.{domain}.enode.io"

# Dynamic URL generation
def get_api_url(environment: Environment) -> str:
    domain = "sandbox" if environment == Environment.SANDBOX else "production"
    return f"https://{BASE_API_URL.format(domain=domain)}"

def get_oauth_url(environment: Environment) -> str:
    domain = "sandbox" if environment == Environment.SANDBOX else "production"
    return f"https://{BASE_OAUTH_URL.format(domain=domain)}/oauth2/token"

DOMAIN = "enodeforha"
PLATFORMS = ["sensor", "binary_sensor", "switch", "device_tracker"]

CONF_DEBUG_NOTIFICATIONS = "debug_notifications"
DEFAULT_DEBUG_NOTIFICATIONS = False
DEBUG_NOTIFICATION_INTERVAL = 600  # 10 minutes in seconds

# API Configuration
API_BASE_URL = get_api_url(CURRENT_ENVIRONMENT)
OAUTH_URL = get_oauth_url(CURRENT_ENVIRONMENT)
API_VEHICLES_PATH = "/vehicles"
API_CHARGING = "/charging"  # Single endpoint for both start and stop

# Configuration keys
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_ACCESS_TOKEN = "access_token"
CONF_TOKEN_EXPIRY = "token_expiry"
CONF_VEHICLE_ID = "vehicle_id"
CONF_VEHICLE_IDS = "vehicle_ids"
CONF_ENVIRONMENT = "environment"
CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL = 60  # seconds
MIN_UPDATE_INTERVAL = 5  # seconds
MAX_UPDATE_INTERVAL = 3600  # seconds (60 minutes)
CONF_INTEGRATION_ID = "integration_id"  # Unique ID for the integration instance
# Token configuration
TOKEN_VALIDITY_PERIOD = 3600  # Token is valid for 1 hour (in seconds)
TOKEN_EXPIRY_BUFFER = 300    # Renew 5 minutes before expiry (in seconds)

CONF_SELECTED_SENSORS = "selected_sensors"
DEFAULT_SELECTED_SENSORS = [
    "token_renewal",  # Always enabled
    "vehicle_information",  # Always enabled
    "battery_capacity",
    "battery_level",
    "charge_limit",
    "charge_rate",
    "charge_time_remaining",
    "charging",
    "fully_charged",
    "last_seen",
    "odometer",
    "plugged_in",
    "power_delivery",
    "range",
    "reachable",
    "charge_control",
    "smart_charging",
    "location"
]

AVAILABLE_SENSORS = {
    "battery_capacity": "Battery Capacity",
    "battery_level": "Battery Level",
    "charge_limit": "Charge Limit",
    "charge_rate": "Charge Rate",
    "charge_time_remaining": "Charge Time Remaining",
    "charging": "Charging",
    "fully_charged": "Fully Charged",
    "last_seen": "Last Seen",
    "odometer": "Odometer",
    "plugged_in": "Plugged In",
    "power_delivery": "Power Delivery",
    "range": "Range",
    "reachable": "Reachable",
    "charge_control": "Charge Control",
    "smart_charging": "Smart Charging",
    "location": "Location"
}

@dataclass
class EnodeSensorEntityDescription:
    """Class describing Enode sensor entities."""
    key: str
    name: str
    value_key: str
    native_unit_of_measurement: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    icon: str | None = None

@dataclass
class EnodeBinarySensorEntityDescription:
    """Class describing Enode binary sensor entities."""
    key: str
    name: str
    value_key: str
    device_class: BinarySensorDeviceClass | None = None
    icon: str | None = None

# Sensor definitions
SENSOR_TYPES: tuple[EnodeSensorEntityDescription, ...] = (
    EnodeSensorEntityDescription(
        key="battery_level",
        name="Battery Level",
        value_key="charge.level",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnodeSensorEntityDescription(
        key="charging_power",
        name="Charging Power",
        value_key="charge.power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnodeSensorEntityDescription(
        key="range",
        name="Range",
        value_key="charge.range",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnodeSensorEntityDescription(
        key="charge_limit",
        name="Charge Limit",
        value_key="chargeState.chargeLimit",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EnodeSensorEntityDescription(
        key="last_seen",
        name="Last Seen",
        value_key="lastSeen",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    EnodeSensorEntityDescription(
        key="vehicle_info",
        name="Vehicle Info",
        value_key="information",
        icon="mdi:car-info",
    ),
)

# Binary sensor definitions
BINARY_SENSOR_TYPES: tuple[EnodeBinarySensorEntityDescription, ...] = (
    EnodeBinarySensorEntityDescription(
        key="is_charging",
        name="Charging Status",
        value_key="charge.isCharging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    EnodeBinarySensorEntityDescription(
        key="is_plugged_in",
        name="Plug Status",
        value_key="charge.isPluggedIn",
        device_class=BinarySensorDeviceClass.PLUG,
    ),
    EnodeBinarySensorEntityDescription(
        key="power_delivery",
        name="Power Delivery",
        value_key="chargeState.powerDeliveryState",
        device_class=BinarySensorDeviceClass.POWER,
    ),
)