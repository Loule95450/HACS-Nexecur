DOMAIN = "nexecur"
PLATFORMS = ["alarm_control_panel", "camera", "switch"]
DEFAULT_NAME = "Nexecur Alarm"

# Alarm version types
ALARM_VERSION_VIDEOFIED = "videofied"
ALARM_VERSION_HIKVISION = "hikvision"

# Hikvision login method
LOGIN_METHOD_PHONE = "phone"
LOGIN_METHOD_EMAIL = "email"

# Common configuration
CONF_ALARM_VERSION = "alarm_version"
CONF_PASSWORD = "password"
CONF_DEVICE_NAME = "device_name"
CONF_LOGIN_METHOD = "login_method"

# Videofied specific
CONF_ID_SITE = "id_site"

# Hikvision specific
CONF_PHONE = "phone"
CONF_EMAIL = "email"
CONF_ACCOUNT = "account"  # Stores the actual phone or email value
CONF_COUNTRY_CODE = "country_code"
CONF_SSID = "ssid"
