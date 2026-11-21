"""Tests for the Videofied panel status mapping."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "nexecur"))

from alarm_mapping import (
    hikvision_panel_state,
    resolve_videofied_arm_status,
    videofied_panel_state,
)


class TestVideofiedPanelState:
    def test_documented_statuses(self):
        assert videofied_panel_state(0) == "disarmed"
        assert videofied_panel_state(1) == "armed_away"
        assert videofied_panel_state(2) == "armed_home"
        assert videofied_panel_state(3) == "armed_night"
        assert videofied_panel_state(4) == "arming"
        assert videofied_panel_state(5) == "triggered"
        assert videofied_panel_state(6) == "disarmed"

    def test_triggered_is_never_reported_as_disarmed(self):
        """A live intrusion must not look like a disarmed panel."""
        assert videofied_panel_state(5) == "triggered"
        assert videofied_panel_state(5, invert_status=True) == "triggered"

    def test_unknown_statuses_are_unknown_not_disarmed(self):
        for status in (10, 11, 12, 99, -1):
            assert videofied_panel_state(status) is None

    def test_inverted_swaps_full_and_partial_1_only(self):
        assert videofied_panel_state(1, invert_status=True) == "armed_home"
        assert videofied_panel_state(2, invert_status=True) == "armed_away"
        assert videofied_panel_state(3, invert_status=True) == "armed_night"
        assert videofied_panel_state(0, invert_status=True) == "disarmed"


class TestHikvisionPanelState:
    def test_known_statuses(self):
        assert hikvision_panel_state(0) == "disarmed"
        assert hikvision_panel_state(1) == "armed_home"
        assert hikvision_panel_state(2) == "armed_away"

    def test_unknown_status(self):
        assert hikvision_panel_state(7) is None


class TestResolveVideofiedArmStatus:
    def test_all_modes_available(self):
        assert resolve_videofied_arm_status("away", True, True) == 1
        assert resolve_videofied_arm_status("home", True, True) == 2
        assert resolve_videofied_arm_status("night", True, True) == 3

    def test_away_never_depends_on_partial_modes(self):
        assert resolve_videofied_arm_status("away", False, False) == 1

    def test_missing_partial_falls_back_to_wider_arming(self):
        assert resolve_videofied_arm_status("night", True, False) == 2
        assert resolve_videofied_arm_status("night", False, False) == 1
        assert resolve_videofied_arm_status("home", False, False) == 1

    def test_inverted(self):
        assert resolve_videofied_arm_status("away", True, True, invert_status=True) == 2
        assert resolve_videofied_arm_status("home", True, True, invert_status=True) == 1
        assert resolve_videofied_arm_status("night", True, True, invert_status=True) == 3

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            resolve_videofied_arm_status("invalid", True, True)
