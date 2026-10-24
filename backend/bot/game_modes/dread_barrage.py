from utils.settings import Settings
from utils.message_log import MessageLog
from utils.image_utils import ImageUtils
from utils.mouse_utils import MouseUtils
from bot.combat_mode import CombatMode


class DreadBarrageException(Exception):
    def __init__(self, message):
        super().__init__(message)


class DreadBarrage:
    """
    Provides the navigation and any necessary utility functions to handle the Dread Barrage game mode.
    """

    @staticmethod
    def _difficulty_index() -> int:
        """Return the one-based Dread Barrage difficulty index from the mission setting."""
        for index in range(1, 6):
            if Settings.mission_name.startswith(f"{index} Star"):
                return index

        raise DreadBarrageException(f"Unsupported Dread Barrage mission: {Settings.mission_name}")

    @staticmethod
    def _confirm_event_page() -> bool:
        """Confirm the Dread Barrage landing page using DOM state, then image fallback."""
        from bot.game import Game

        if getattr(Settings, "enable_dom_clicking", False):
            is_dread_barrage = Game.evaluate_dom_js("""(() => {
                const hash = window.location.hash || '';
                const page = document.querySelector('.cnt-teamforce');
                return hash.includes('event/teamforce') && Boolean(page && page.offsetParent !== null);
            })()""")
            if is_dread_barrage:
                MessageLog.print_message("[DREAD.BARRAGE] Confirmed Dread Barrage page via DOM.")
                return True

        return ImageUtils.confirm_location("dread_barrage")

    @staticmethod
    def _click_difficulty_dom(difficulty_index: int) -> bool:
        """Click an unlocked Dread Barrage difficulty using its stable DOM index."""
        from bot.game import Game

        if not getattr(Settings, "enable_dom_clicking", False):
            return False

        click_result = Game.evaluate_dom_js(f"""(() => {{
            const selector = ".cnt-teamforce .btn-start-quest.open[data-enemy-index='{difficulty_index}']";
            const target = Array.from(document.querySelectorAll(selector)).find(el => {{
                if (el.offsetParent === null) return false;
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
            }});
            if (!target) return {{success: false}};

            try {{ target.scrollIntoView({{block: 'center', behavior: 'instant'}}); }} catch (e) {{}}

            if (window.$) {{
                try {{
                    $(target).trigger('tap');
                    return {{success: true, method: 'tap'}};
                }} catch (e) {{}}
            }}

            try {{
                target.click();
                return {{success: true, method: 'click'}};
            }} catch (e) {{
                return {{success: false}};
            }}
        }})()""")

        if isinstance(click_result, dict) and click_result.get("success"):
            MessageLog.print_message(
                f"[DREAD.BARRAGE] Selected {difficulty_index} Star via DOM ({click_result.get('method', 'click')})."
            )
            return True

        return False

    @staticmethod
    def _navigate():
        """Navigates to the specified Dread Barrage mission.

        Returns:
            None
        """
        from bot.game import Game

        # Scroll down the screen a little bit and then click the Dread Barrage banner.
        MessageLog.print_message(f"\n[DREAD.BARRAGE] Now navigating to Dread Barrage...")
        Game.go_back_home(confirm_location_check = True)

        # Navigate to the Dread Barrage banner.
        tries = 30
        while tries > 0:
            if Game.find_and_click_button("dread_barrage", tries = 1) is False:
                MouseUtils.scroll_screen_from_home_button(-200)
                tries -= 1
                if tries <= 0:
                    raise DreadBarrageException("Failed to navigate to Dread Barrage from the Home screen.")
            else:
                break

        Game.wait(3.0)

        if DreadBarrage._confirm_event_page():
            # Check if there is already a hosted Dread Barrage mission.
            if ImageUtils.confirm_location("resume_quests"):
                MessageLog.print_message(f"\n[WARNING] Detected that there is already a hosted Dread Barrage mission.")
                expiry_time_in_seconds = 0

                while ImageUtils.confirm_location("resume_quests", tries = 1):
                    # If there is already a hosted Dread Barrage mission, the bot will wait for a total of 1 hour and 30 minutes
                    # for either the raid to expire or for anyone in the room to clear it.
                    MessageLog.print_message(f"\n[WARNING] The bot will now either wait for the expiry time of 1 hour and 30 minutes or for someone else in the room to clear it.")
                    MessageLog.print_message(f"[WARNING] The bot will now refresh the page every 30 seconds to check if it is still there before proceeding.")
                    MessageLog.print_message(f"[WARNING] User can either wait it out, revive and fight it to completion, or retreat from the mission manually.")
                    Game.wait(30)

                    Game.find_and_click_button("reload")
                    Game.wait(2)

                    expiry_time_in_seconds += 30
                    if expiry_time_in_seconds >= 5400:
                        break

                MessageLog.print_message(f"\n[SUCCESS] Hosted Dread Barrage mission is now gone either because of timeout or someone else in the room killed it. Moving on...\n")

            difficulty_index = DreadBarrage._difficulty_index()
            MessageLog.print_message(
                f"[DREAD.BARRAGE] Now starting {difficulty_index} Star Dread Barrage Raid..."
            )

            if not DreadBarrage._click_difficulty_dom(difficulty_index):
                # Retain image matching for browsers where DevTools/DOM access is unavailable.
                dread_barrage_play_button_locations = ImageUtils.find_all("dread_barrage_play")
                if len(dread_barrage_play_button_locations) < difficulty_index:
                    raise DreadBarrageException(
                        f"Failed to find the unlocked {difficulty_index} Star Dread Barrage Play button. "
                        f"Detected {len(dread_barrage_play_button_locations)} Play button(s)."
                    )

                target = dread_barrage_play_button_locations[difficulty_index - 1]
                MouseUtils.move_and_click_point(target[0], target[1], "dread_barrage_play")

            Game.wait(2)
        else:
            raise DreadBarrageException("Failed to arrive at Dread Barrage page.")

    @staticmethod
    def start(first_run: bool):
        """Starts the process to complete a run for Dread Barrage Farming Mode and returns the number of items detected.

        Args:
            first_run (bool): Flag that determines whether or not to run the navigation process again. Should be False if the Farming Mode supports the "Play Again" feature for repeated runs.

        Returns:
            None
        """
        from bot.game import Game

        # Start the navigation process.
        if first_run:
            DreadBarrage._navigate()
        elif Game.find_and_click_button("play_again"):
            Game.check_for_popups()
        else:
            # If the bot cannot find the "Play Again" button, check for Pending Battles and then perform navigation again.
            Game.check_for_pending()
            DreadBarrage._navigate()

        # Check for AP.
        Game.check_for_ap()

        # Check if the bot is at the Summon Selection screen.
        if ImageUtils.confirm_location("select_a_summon", tries = 30):
            summon_check = Game.select_summon(Settings.summon_list, Settings.summon_element_list)
            if summon_check:
                # Select the Party.
                Game.find_party_and_start_mission(Settings.group_number, Settings.party_number)

                # Now start Combat Mode and detect any item drops.
                if CombatMode.start_combat_mode():
                    Game.collect_loot_safe(is_completed = True)
        else:
            raise DreadBarrageException("Failed to arrive at the Summon Selection screen.")

        return None
