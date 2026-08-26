DOMAIN = "nexecur"
PLATFORMS = ["alarm_control_panel", "camera", "switch", "sensor", "binary_sensor"]
DEFAULT_NAME = "Nexecur Alarm"

# Sub-device types
DEVICE_TYPE_ZONE = "zone"
DEVICE_TYPE_KEYPAD = "keypad"
DEVICE_TYPE_SIREN = "siren"
DEVICE_TYPE_BASE = "base"

# Detector types mapping to device classes
DETECTOR_TYPE_PIR = "pir"
DETECTOR_TYPE_PIRCAM = "pircam"
DETECTOR_TYPE_MAGNET = "magnetDetector"
DETECTOR_TYPE_MAGNET_SHOCK = "magnetShockDetector"
DETECTOR_TYPE_SMOKE = "wirelessSmokeDetector"
DETECTOR_TYPE_CO = "wirelessCODetector"
DETECTOR_TYPE_GLASS = "glassBreak"
DETECTOR_TYPE_WATER = "waterDetector"
DETECTOR_TYPE_GAS = "gasDetector"

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
CONF_DISARM_CODE = "disarm_code"
CONF_ARM_CODE = "arm_code"
CONF_INVERT_STATUS = "invert_status"

# Videofied specific
CONF_ID_SITE = "id_site"

# Hikvision specific
CONF_PHONE = "phone"
CONF_EMAIL = "email"
CONF_ACCOUNT = "account"  # Stores the actual phone or email value
CONF_COUNTRY_CODE = "country_code"
CONF_SSID = "ssid"
# Stable hardware fingerprint sent to the Hikvision cloud at login.
# Must stay identical across restarts: the cloud binds it to the account
# as a trusted terminal, and rejects unknown ones.
CONF_FEATURE_CODE = "feature_code"
# One-time code sent by the cloud to enrol a new terminal
CONF_SMS_CODE = "sms_code"
# Persisted Hikvision session. The cloud refuses a plain password login from a
# terminal it does not already trust, so the session -- refreshed rather than
# re-created -- is what keeps the integration working across restarts.
CONF_SESSION_ID = "session_id"
CONF_RF_SESSION_ID = "rf_session_id"
CONF_USER_INFO = "user_info"
CONF_API_DOMAIN = "api_domain"
