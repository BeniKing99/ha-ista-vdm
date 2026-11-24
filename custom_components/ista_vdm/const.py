"""Constants for the ista VDM integration."""

from homeassistant.const import Platform

DOMAIN = "ista_vdm"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

# Configuration keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# Update interval (once per day since data is only updated monthly)
UPDATE_INTERVAL = 86400  # 24 hours in seconds

# Default sensor names
DEFAULT_NAME = "Ista VDM"

# Keys of all per-flat sensors. Before multi-flat support (<= 1.0.4) their unique
# IDs were "<entry_id>_<key>"; they are now "<entry_id>_<flat_id>_<key>".
SENSOR_KEYS: tuple[str, ...] = (
    "heating_consumption",
    "hot_water_consumption",
    "cold_water_consumption",
    "last_updated",
    "flat_city",
    "flat_street",
    "flat_housenumber",
    "flat_door",
    "flat_squaremeter",
    "flat_postalcode",
)

# API Constants
BASE_URL = "https://ista-vdm.at"
LOGIN_URL = "https://login.ista.com/realms/vdm/protocol/openid-connect/auth"
TOKEN_URL = "https://login.ista.com/realms/vdm/protocol/openid-connect/token"