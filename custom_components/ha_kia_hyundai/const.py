# Configuration Constants
from homeassistant.const import Platform

DOMAIN: str = "ha_kia_hyundai"
CONF_VEHICLE_ID: str = "vehicle_id"
CONF_OTP_TYPE: str = "otp_type"
CONF_OTP_CODE: str = "otp_code"
CONF_DEVICE_ID: str = "device_id"
CONF_REFRESH_TOKEN: str = "refresh_token"
CONF_ACCESS_TOKEN: str = "access_token"
CONFIG_FLOW_TEMP_VEHICLES: str = "vehicles"
DEFAULT_SCAN_INTERVAL: int = 10
DELAY_BETWEEN_ACTION_IN_PROGRESS_CHECKING: int = 20
TEMPERATURE_MIN = 62
TEMPERATURE_MAX = 82

# Integration Setting Constants
CONFIG_FLOW_VERSION: int = 3
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.DEVICE_TRACKER,
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Sensor Specific Constants
DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"

# Seat heating/cooling settings
SEAT_STATUS = {
    (0, 1): "Off",
    (1, 4): "High Heat",
    (1, 3): "Medium Heat",
    (1, 2): "Low Heat",
    (2, 4): "High Cool",
    (2, 3): "Medium Cool",
    (2, 2): "Low Cool",
}

# We'll define our own seat settings since we're not using the old library
class SeatSettings:
    NONE = (0, 1)
    HeatHigh = (1, 4)
    HeatMedium = (1, 3)
    HeatLow = (1, 2)
    CoolHigh = (2, 4)
    CoolMedium = (2, 3)
    CoolLow = (2, 2)

STR_TO_ENUM = {
    "Off": SeatSettings.NONE,
    "High Heat": SeatSettings.HeatHigh,
    "Medium Heat": SeatSettings.HeatMedium,
    "Low Heat": SeatSettings.HeatLow,
    "High Cool": SeatSettings.CoolHigh,
    "Medium Cool": SeatSettings.CoolMedium,
    "Low Cool": SeatSettings.CoolLow,
}
