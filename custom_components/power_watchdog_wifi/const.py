"""Constants for the Power Watchdog WiFi integration."""

DOMAIN = "power_watchdog_wifi"
PLATFORMS = ["sensor", "binary_sensor"]

# Config-entry keys persisted from config flow / cloud metadata.
CONF_ACCOUNT = "account"
CONF_PASSWORD = "password"
CONF_DEVICE_NO = "device_no"
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_NAME = "device_name"
CONF_FIRMWARE = "firmware"
CONF_MCU_FIRMWARE = "mcu_firmware"
CONF_CONNECT_TYPE = "connect_type"
CONF_SOCKET_STATE = "socket_state"
CONF_START_FROM = "start_from"

API_BASE_URL = "https://api.watchdogsrv.com/api"
WS_URL = "ws://ws.watchdogsrv.com:5521/ws"
APP_VERSION = "1.0.15"
APP_DEVICE = "android"

# Runtime tuning defaults.
WS_RECONNECT_MIN_SECONDS = 5
WS_RECONNECT_MAX_SECONDS = 300
TELEMETRY_AVAILABILITY_TIMEOUT_SECONDS = 120
DEVICE_METADATA_REFRESH_INTERVAL_SECONDS = 3600
DERIVED_ROLLING_POWER_WINDOW_SECONDS = 300
DERIVED_ENERGY_STATE_PERSIST_INTERVAL_SECONDS = 300
DERIVED_ENERGY_STORAGE_KEY = "power_watchdog_wifi_derived_energy"
DERIVED_ENERGY_STORAGE_VERSION = 1
