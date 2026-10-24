import os
import sys
import unittest
from unittest.mock import patch


BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from bot.game import Game
from bot.game_modes.dread_barrage import DreadBarrage, DreadBarrageException
from utils.image_utils import ImageUtils
from utils.settings import Settings


class DreadBarrageDomTests(unittest.TestCase):
    def test_confirm_event_page_uses_teamforce_dom_state(self):
        with patch.object(Settings, "enable_dom_clicking", True), \
                patch.object(Game, "evaluate_dom_js", return_value=True) as evaluate, \
                patch.object(ImageUtils, "confirm_location") as image_confirm:
            self.assertTrue(DreadBarrage._confirm_event_page())

        self.assertIn("event/teamforce", evaluate.call_args.args[0])
        self.assertIn(".cnt-teamforce", evaluate.call_args.args[0])
        image_confirm.assert_not_called()

    def test_confirm_event_page_falls_back_to_image_matching(self):
        with patch.object(Settings, "enable_dom_clicking", True), \
                patch.object(Game, "evaluate_dom_js", return_value=False), \
                patch.object(ImageUtils, "confirm_location", return_value=True) as image_confirm:
            self.assertTrue(DreadBarrage._confirm_event_page())

        image_confirm.assert_called_once_with("dread_barrage")

    def test_click_difficulty_dom_targets_unlocked_enemy_index(self):
        with patch.object(Settings, "enable_dom_clicking", True), \
                patch.object(Game, "evaluate_dom_js", return_value={"success": True, "method": "tap"}) as evaluate:
            self.assertTrue(DreadBarrage._click_difficulty_dom(4))

        javascript = evaluate.call_args.args[0]
        self.assertIn(".btn-start-quest.open", javascript)
        self.assertIn("data-enemy-index='4'", javascript)

    def test_difficulty_index_rejects_unknown_mission(self):
        with patch.object(Settings, "mission_name", "Unknown"):
            with self.assertRaises(DreadBarrageException):
                DreadBarrage._difficulty_index()


if __name__ == "__main__":
    unittest.main()
