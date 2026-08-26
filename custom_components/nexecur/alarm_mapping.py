"""Helpers for Videofied alarm mode mapping."""


def resolve_videofied_arm_mode(requested_mode: str, panel_sp2_available: bool, invert_status: bool) -> str:
    """Return the Videofied command mode to send to API: ``home`` or ``away``."""
    if requested_mode not in ("home", "away"):
        raise ValueError("requested_mode must be 'home' or 'away'")

    if requested_mode == "away":
        if not panel_sp2_available:
            return "home"
        return "home" if invert_status else "away"

    if panel_sp2_available and invert_status:
        return "away"
    return "home"
