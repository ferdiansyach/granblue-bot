import unittest
from unittest.mock import patch

from bot.combat_mode import CombatMode
from bot.game import Game
from utils.image_utils import ImageUtils
from utils.settings import Settings


class RaidElixirRecoveryTests(unittest.TestCase):
    def setUp(self):
        CombatMode._retreat_check = False

    def tearDown(self):
        CombatMode._retreat_check = False

    def test_successful_raid_revive_keeps_combat_running(self):
        with patch.object(Settings, "farming_mode", "Raid"), \
                patch.object(Settings, "enable_dom_clicking", True), \
                patch("bot.dom_clicker.DomClicker.element_exists", side_effect = [True, False]), \
                patch.object(CombatMode, "_revive_raid_party_with_elixir", return_value = True) as revive, \
                patch.object(ImageUtils, "find_button", return_value = None), \
                patch.object(Game, "go_back_home") as go_home:
            CombatMode._check_for_wipe()

        revive.assert_called_once_with(None)
        go_home.assert_not_called()
        self.assertFalse(CombatMode._retreat_check)

    def test_failed_raid_revive_recovers_home_and_stops_combat(self):
        with patch.object(Settings, "farming_mode", "Raid"), \
                patch.object(Settings, "enable_dom_clicking", True), \
                patch("bot.dom_clicker.DomClicker.element_exists", side_effect = [True, False]), \
                patch.object(CombatMode, "_revive_raid_party_with_elixir", return_value = False), \
                patch.object(ImageUtils, "find_button", return_value = None), \
                patch.object(Game, "go_back_home") as go_home:
            CombatMode._check_for_wipe()

        go_home.assert_called_once_with(confirm_location_check = True)
        self.assertTrue(CombatMode._retreat_check)

    def test_revive_helper_confirms_restored_party(self):
        with patch.object(CombatMode, "_click_raid_elixir_prompt", side_effect = [False, True]), \
                patch.object(CombatMode, "_raid_party_revive_state", return_value = True), \
                patch.object(ImageUtils, "find_button", return_value = (100, 200)), \
                patch.object(ImageUtils, "confirm_location", return_value = False), \
                patch.object(Game, "wait"), \
                patch("bot.combat_mode.MouseUtils.move_and_click_point") as click:
            revived = CombatMode._revive_raid_party_with_elixir()

        self.assertTrue(revived)
        click.assert_called_once_with(100, 200, "party_wipe_indicator")


if __name__ == "__main__":
    unittest.main()
