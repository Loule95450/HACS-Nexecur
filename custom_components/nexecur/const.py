from homeassistant.const import Platform

DOMAIN = "nexecur"
PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.CAMERA]
DEFAULT_NAME = "Nexecur Alarm"

CONF_ID_SITE = "id_site"
CONF_PASSWORD = "password"
CONF_DEVICE_NAME = "device_name"
