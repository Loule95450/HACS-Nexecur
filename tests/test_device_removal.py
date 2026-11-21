"""
Tests for deciding which Nexecur devices may be deleted from Home Assistant
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur'))

from device_removal import current_sub_device_identifiers, is_stale_sub_device

DOMAIN = "nexecur"
MAIN = "hikvision_user@example.com"
DATA = {
    "zones": [{"id": 1, "name": "Door"}, {"id": 9, "name": "New heat detector"}],
    "keypads": [{"id": 1}],
    "sirens": [{"id": 1}],
}


def ids(value):
    return {(DOMAIN, value)}


class TestCurrentSubDeviceIdentifiers:
    def test_lists_zones_keypads_and_sirens(self):
        assert current_sub_device_identifiers(MAIN, DATA) == {
            f"{MAIN}_zone_1",
            f"{MAIN}_zone_9",
            f"{MAIN}_keypad_1",
            f"{MAIN}_siren_1",
        }

    def test_skips_items_without_id(self):
        assert current_sub_device_identifiers(MAIN, {"zones": [{"name": "x"}]}) == set()


class TestIsStaleSubDevice:
    def test_zone_no_longer_reported_is_removable(self):
        assert is_stale_sub_device(ids(f"{MAIN}_zone_3"), DOMAIN, MAIN, DATA)

    def test_keypad_and_siren_no_longer_reported_are_removable(self):
        assert is_stale_sub_device(ids(f"{MAIN}_keypad_2"), DOMAIN, MAIN, DATA)
        assert is_stale_sub_device(ids(f"{MAIN}_siren_5"), DOMAIN, MAIN, DATA)

    def test_reported_zone_is_kept(self):
        assert not is_stale_sub_device(ids(f"{MAIN}_zone_9"), DOMAIN, MAIN, DATA)

    def test_panel_is_kept(self):
        assert not is_stale_sub_device(ids(MAIN), DOMAIN, MAIN, DATA)

    def test_camera_is_kept(self):
        assert not is_stale_sub_device(ids("123_ABCDEF"), DOMAIN, MAIN, DATA)

    def test_other_account_is_kept(self):
        other = "hikvision_other@example.com_zone_3"
        assert not is_stale_sub_device(ids(other), DOMAIN, MAIN, DATA)

    def test_other_domain_is_kept(self):
        assert not is_stale_sub_device({("zha", f"{MAIN}_zone_3")}, DOMAIN, MAIN, DATA)

    def test_kept_without_data(self):
        assert not is_stale_sub_device(ids(f"{MAIN}_zone_3"), DOMAIN, MAIN, None)
        assert not is_stale_sub_device(ids(f"{MAIN}_zone_3"), DOMAIN, MAIN, {})

    def test_kept_when_a_sub_device_list_is_missing(self):
        partial = {"zones": DATA["zones"], "keypads": []}
        assert not is_stale_sub_device(ids(f"{MAIN}_zone_3"), DOMAIN, MAIN, partial)

    def test_zone_id_prefix_does_not_match_longer_id(self):
        # zone_1 is reported; zone_10 is not and must be removable
        assert is_stale_sub_device(ids(f"{MAIN}_zone_10"), DOMAIN, MAIN, DATA)
