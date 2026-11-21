"""Decide whether a Nexecur device may be removed from Home Assistant.

Kept free of Home Assistant imports so it can be unit tested on its own.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

# Sub-device type, as used in device identifiers, -> coordinator data key.
# Must match DEVICE_TYPE_ZONE / _KEYPAD / _SIREN in const.py.
SUB_DEVICE_DATA_KEYS = {"zone": "zones", "keypad": "keypads", "siren": "sirens"}


def current_sub_device_identifiers(
    main_device_id: str, data: Mapping[str, Any]
) -> set[str]:
    """Identifiers of the sub-devices the alarm reports right now."""
    identifiers: set[str] = set()
    for device_type, data_key in SUB_DEVICE_DATA_KEYS.items():
        for item in data.get(data_key) or []:
            item_id = item.get("id")
            if item_id is not None:
                identifiers.add(f"{main_device_id}_{device_type}_{item_id}")
    return identifiers


def is_stale_sub_device(
    identifiers: Iterable[tuple[str, str]],
    domain: str,
    main_device_id: str,
    data: Mapping[str, Any] | None,
) -> bool:
    """True when the device is a zone/keypad/siren the alarm no longer reports.

    Anything else (the panel itself, cameras, or a sub-device that is still
    reported) must stay, as must everything when no fresh data is available.
    """
    if not data or any(key not in data for key in SUB_DEVICE_DATA_KEYS.values()):
        return False

    own = [value for dom, value in identifiers if dom == domain]
    if not own:
        return False

    prefixes = tuple(f"{main_device_id}_{t}_" for t in SUB_DEVICE_DATA_KEYS)
    current = current_sub_device_identifiers(main_device_id, data)
    return all(value.startswith(prefixes) and value not in current for value in own)
