import unittest
from unittest.mock import patch

from bot.combat_mode import CombatMode, CombatModeException
from bot.game import Game
from utils.image_utils import ImageUtils
from utils.settings import Settings


class CombatSafetyTimeoutTests(unittest.TestCase):
    def test_timeout_uses_existing_raid_limit(self):
        with patch.object(Settings, "enable_no_timeout", False), \
                patch.object(Settings, "time_allowed_until_auto_exit_raid", 600):
            self.assertEqual(CombatMode._combat_safety_timeout_seconds(), 600.0)

    def test_timeout_can_be_explicitly_disabled(self):
        with patch.object(Settings, "enable_no_timeout", True):
            self.assertIsNone(CombatMode._combat_safety_timeout_seconds())

    def test_timeout_raises_recoverable_combat_event(self):
        with patch.object(Settings, "enable_no_timeout", False), \
                patch.object(Settings, "time_allowed_until_auto_exit_raid", 600), \
                patch("bot.combat_mode.time.time", return_value = 601), \
                patch.object(CombatMode, "_combat_safety_timeout_seconds", return_value = 600), \
                patch("bot.combat_mode.MessageLog.print_message"):
            with self.assertRaisesRegex(CombatModeException, "Time Exceeded"):
                CombatMode._check_monitor_safety_timeout(0, "Full Auto monitor")


class HomeRecoveryTests(unittest.TestCase):
    def test_dom_route_recovery_does_not_require_template_match(self):
        dom_results = [False, False, True, True, True]
        with patch.object(Game, "evaluate_dom_js", side_effect = dom_results), \
                patch.object(ImageUtils, "confirm_location", return_value = False), \
                patch.object(Game, "find_and_click_button") as click_mock, \
                patch.object(Game, "wait"), \
                patch("bot.game.MessageLog.print_message"):
            Game.go_back_home(confirm_location_check = True)

        click_mock.assert_not_called()

    def test_visible_home_control_is_used_when_cdp_is_unavailable(self):
        dom_results = [False, False, False, False, True]
        image_results = [False, False, True]

        def click_result(button_name, **_kwargs):
            if button_name == "home":
                return (100, 100)
            return None

        with patch.object(Game, "evaluate_dom_js", side_effect = dom_results), \
                patch.object(ImageUtils, "confirm_location", side_effect = image_results), \
                patch.object(Game, "find_and_click_button", side_effect = click_result) as click_mock, \
                patch.object(Game, "wait"), \
                patch("bot.game.MessageLog.print_message"):
            Game.go_back_home(confirm_location_check = True)

        self.assertTrue(any(call.args[0] == "home" for call in click_mock.call_args_list))

    def test_failed_recovery_is_bounded_and_reloads_once(self):
        with patch.object(Game, "_is_home_state", return_value = False), \
                patch.object(Game, "evaluate_dom_js", return_value = False), \
                patch.object(Game, "find_and_click_button", return_value = None) as click_mock, \
                patch.object(Game, "wait"), \
                patch("bot.game.MessageLog.print_message"):
            recovered = Game._recover_to_home(max_attempts = 2)

        self.assertFalse(recovered)
        reload_calls = [call for call in click_mock.call_args_list if call.args[0] == "reload"]
        self.assertEqual(len(reload_calls), 1)


if __name__ == "__main__":
    unittest.main()
