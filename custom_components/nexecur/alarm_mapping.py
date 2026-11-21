"""Mapping between Videofied panel statuses and Home Assistant states.

Kept free of any Home Assistant import so it can be unit tested on its own.
States are the plain values of ``AlarmControlPanelState``.
"""

# Panel statuses reported by the Mon NEXECUR web services.
PANEL_DISARMED = 0
PANEL_ARMED_AWAY = 1  # full arming
PANEL_ARMED_PARTIAL_1 = 2  # "SP1"
PANEL_ARMED_PARTIAL_2 = 3  # "SP2"
PANEL_ARMING = 4
PANEL_TRIGGERED = 5
PANEL_TRIGGERED_RESTORED = 6
PANEL_DISCONNECTED = 10
PANEL_CONNECTED = 11
PANEL_CAMERA_DETECTION = 12

STATE_BY_STATUS = {
    PANEL_DISARMED: "disarmed",
    PANEL_ARMED_AWAY: "armed_away",
    PANEL_ARMED_PARTIAL_1: "armed_home",
    PANEL_ARMED_PARTIAL_2: "armed_night",
    PANEL_ARMING: "arming",
    PANEL_TRIGGERED: "triggered",
    PANEL_TRIGGERED_RESTORED: "disarmed",
}

# Hikvision cloud panels report their own, smaller set of codes.
HIKVISION_STATE_BY_STATUS = {
    0: "disarmed",
    1: "armed_home",
    2: "armed_away",
}

ARM_STATUS_BY_MODE = {
    "away": PANEL_ARMED_AWAY,
    "home": PANEL_ARMED_PARTIAL_1,
    "night": PANEL_ARMED_PARTIAL_2,
}

# Installations wired the other way round: the two partial modes are swapped.
_INVERTED = {PANEL_ARMED_AWAY: PANEL_ARMED_PARTIAL_1, PANEL_ARMED_PARTIAL_1: PANEL_ARMED_AWAY}


def videofied_panel_state(status: int, invert_status: bool = False) -> str | None:
    """Return the Home Assistant state for a panel status.

    ``None`` means "unknown": a status that carries no arming information
    (disconnected panel, camera detection) must never be reported as disarmed.
    """
    if invert_status:
        status = _INVERTED.get(status, status)
    return STATE_BY_STATUS.get(status)


def hikvision_panel_state(status: int) -> str | None:
    """Return the Home Assistant state for a Hikvision panel status."""
    return HIKVISION_STATE_BY_STATUS.get(status)


def resolve_videofied_arm_status(
    requested_mode: str,
    panel_sp1_available: bool,
    panel_sp2_available: bool,
    invert_status: bool = False,
) -> int:
    """Return the panel status to send for an arm request.

    A partial mode the site does not expose falls back to a wider arming:
    arming less than asked would leave the home unprotected without saying so.
    """
    if requested_mode not in ARM_STATUS_BY_MODE:
        raise ValueError("requested_mode must be 'away', 'home' or 'night'")

    status = ARM_STATUS_BY_MODE[requested_mode]
    if status == PANEL_ARMED_PARTIAL_2 and not panel_sp2_available:
        status = PANEL_ARMED_PARTIAL_1
    if status == PANEL_ARMED_PARTIAL_1 and not panel_sp1_available:
        status = PANEL_ARMED_AWAY

    if invert_status:
        status = _INVERTED.get(status, status)
    return status
