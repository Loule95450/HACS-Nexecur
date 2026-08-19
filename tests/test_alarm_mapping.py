"""Tests for Videofied arm mode mapping."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "nexecur"))

from alarm_mapping import resolve_videofied_arm_mode


class TestResolveVideofiedArmMode:
    def test_away_not_inverted_with_sp2(self):
        assert resolve_videofied_arm_mode("away", panel_sp2_available=True, invert_status=False) == "away"

    def test_away_inverted_with_sp2(self):
        assert resolve_videofied_arm_mode("away", panel_sp2_available=True, invert_status=True) == "home"

    def test_home_not_inverted_with_sp2(self):
        assert resolve_videofied_arm_mode("home", panel_sp2_available=True, invert_status=False) == "home"

    def test_home_inverted_with_sp2(self):
        assert resolve_videofied_arm_mode("home", panel_sp2_available=True, invert_status=True) == "away"

    def test_away_without_sp2_falls_back_home(self):
        assert resolve_videofied_arm_mode("away", panel_sp2_available=False, invert_status=False) == "home"
        assert resolve_videofied_arm_mode("away", panel_sp2_available=False, invert_status=True) == "home"

    def test_home_without_sp2_stays_home(self):
        assert resolve_videofied_arm_mode("home", panel_sp2_available=False, invert_status=False) == "home"
        assert resolve_videofied_arm_mode("home", panel_sp2_available=False, invert_status=True) == "home"

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            resolve_videofied_arm_mode("invalid", panel_sp2_available=True, invert_status=False)
