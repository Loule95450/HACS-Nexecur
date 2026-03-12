"""
Mock responses for Nexecur HACS tests
Based on actual API responses from Videofied and Hikvision
"""

# =====================
# Videofied API Responses
# =====================

VIDEOFIED_LOGIN_SUCCESS = {
    "message": "OK",
    "status": 0,
    "token": "test_videofied_token_12345",
    "id_device": "device_12345"
}

VIDEOFIED_SALT_SUCCESS = {
    "message": "OK",
    "status": 0,
    "salt": "SaltedBase64String=="
}

VIDEOFIED_SITE_DISARMED = {
    "message": "OK",
    "status": 0,
    "token": "test_token_refreshed",
    "panel_status": 0,  # Disarmed
    "panel_sp1": 1,
    "panel_sp2": 1,
    "panel_sp1_nom": "Home",
    "panel_sp2_nom": "Away",
    "devices": [
        {
            "serial": "CAM001",
            "device_id": 1,
            "name": "Camera 1",
            "picture": ""
        }
    ],
    "badges": [],
    "evenements": []
}

VIDEOFIED_SITE_ARMED_PARTIAL = {
    "message": "OK",
    "status": 0,
    "panel_status": 1,  # SP1 - Partial/Home
    "panel_sp1": 1,
    "panel_sp2": 1,
}

VIDEOFIED_SITE_ARMED_TOTAL = {
    "message": "OK",
    "status": 0,
    "panel_status": 2,  # SP2 - Total/Away
    "panel_sp1": 1,
    "panel_sp2": 1,
}

VIDEOFIED_PANEL_STATUS_SUCCESS = {
    "message": "OK",
    "status": 0,
    "pending": 0
}

VIDEOFIED_PANEL_STATUS_PENDING = {
    "message": "OK",
    "status": 0,
    "pending": 1
}

VIDEOFIED_CHECK_STATUS_DONE = {
    "message": "OK",
    "status": 0,
    "still_pending": 0
}

VIDEOFIED_CHECK_STATUS_PENDING = {
    "message": "OK",
    "status": 0,
    "still_pending": 1
}

VIDEOFIED_STREAM_SUCCESS = {
    "message": "OK",
    "status": 0,
    "uri": "rtsp://stream.example.com/live"
}

# =====================
# Hikvision API Responses
# =====================

HIKVISION_LOGIN_SUCCESS = {
    "meta": {"code": "200", "message": "Login successful"},
    "loginSession": {"sessionId": "hikvision_session_12345"},
    "loginUser": {
        "username": "330612345678",
        "customno": "custom123",
        "areaId": 1
    },
    "loginArea": {"apiDomain": "apiieu.guardingvision.com"}
}

HIKVISION_LOGIN_INVALID_CREDENTIALS = {
    "meta": {"code": "401", "message": "Invalid credentials"}
}

HIKVISION_DEVICES_SUCCESS = {
    "deviceInfos": [
        {
            "deviceSerial": "DSI12345678",
            "name": "AX PRO",
            "deviceId": 123456,
            "picture": "",
            "online": 1
        }
    ]
}

HIKVISION_SECURITY_INFO = """HTTP/1.1 200 OK
Content-Type: application/json

{"nonce":"test-nonce-12345","realm":"DVRNVRDVS","List":[{"CloudUserManage":{"salt":"test-salt","salt2":"test-salt2","userNameSessionAuthInfo":"test-auth-hash"}}]}"""

HIKVISION_STATUS_AWAY = """HTTP/1.1 200 OK
Content-Type: application/json

{"AlarmHostStatus":{"communiStatus":"online","SubSysList":[{"SubSys":{"id":1,"arming":"away"}}]}}"""

HIKVISION_STATUS_STAY = """HTTP/1.1 200 OK
Content-Type: application/json

{"AlarmHostStatus":{"communiStatus":"online","SubSysList":[{"SubSys":{"id":1,"arming":"stay"}}]}}"""

HIKVISION_STATUS_DISARMED = """HTTP/1.1 200 OK
Content-Type: application/json

{"AlarmHostStatus":{"communiStatus":"online","SubSysList":[{"SubSys":{"id":1,"arming":"disarm"}}]}}"""

HIKVISION_ARM_SUCCESS = """HTTP/1.1 200 OK
Content-Type: application/json

{"errorCode": 0, "message": "success"}"""

HIKVISION_DISARM_SUCCESS = """HTTP/1.1 200 OK
Content-Type: application/json

{"errorCode": 0, "message": "success"}"""

# =====================
# Error Responses
# =====================

ERROR_INVALID_CREDENTIALS = {
    "message": "Invalid credentials",
    "status": 1
}

ERROR_NO_TOKEN = {
    "message": "No token",
    "status": 1
}

ERROR_DEVICE_NOT_FOUND = {
    "message": "Device not found",
    "status": 1
}
