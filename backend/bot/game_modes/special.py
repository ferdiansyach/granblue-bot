import json

from utils.settings import Settings
from utils.message_log import MessageLog
from utils.image_utils import ImageUtils
from utils.mouse_utils import MouseUtils
from bot.combat_mode import CombatMode


class SpecialException(Exception):
    def __init__(self, message):
        super().__init__(message)


class Special:
    """
    Provides the navigation and any necessary utility functions to handle the Special game mode.
    """

    _dimensional_halo_amount = 0

    @staticmethod
    def _is_quest_page() -> bool:
        """Confirm the main Quest page through its route before image fallback."""
        from bot.game import Game

        dom_match = Game.evaluate_dom_js("""(() => {
            const hash = window.location.hash || '';
            return hash === '#quest' || hash.startsWith('#quest/index') ||
                Boolean(document.querySelector('.btn-extra-quest, [data-href="quest/extra"]'));
        })()""")
        if dom_match:
            return True

        return bool(ImageUtils.confirm_location(
            "quest", tries = 1, suppress_error = True
        ))

    @staticmethod
    def _is_special_page() -> bool:
        """Confirm the modern Special Quest page, with the old header as fallback."""
        from bot.game import Game

        dom_match = Game.evaluate_dom_js("""(() => {
            const hash = window.location.hash || '';
            const list = document.querySelector('.prt-extra, .prt-quest-list');
            return hash.includes('quest/extra') && Boolean(list);
        })()""")
        if dom_match:
            return True

        return bool(ImageUtils.confirm_location(
            "special", tries = 1, suppress_error = True
        ))

    @staticmethod
    def _special_card_exists(card_title: str) -> bool:
        """Return whether a named card exists on the modern Special Quest page."""
        from bot.game import Game

        title_json = json.dumps(card_title)
        return bool(Game.evaluate_dom_js(f"""(() => {{
            const wanted = {title_json};
            return Array.from(document.querySelectorAll('.lis-event-list .txt-quest-title'))
                .some(title => title.textContent.trim() === wanted &&
                    title.closest('.lis-event-list')?.querySelector('.btn-stage-detail'));
        }})()"""))

    @staticmethod
    def _click_special_card(card_title: str) -> bool:
        """Open a named modern Special Quest card through its own Select control."""
        from bot.game import Game

        title_json = json.dumps(card_title)
        clicked = Game.evaluate_dom_js(f"""(() => {{
            const wanted = {title_json};
            const title = Array.from(document.querySelectorAll(
                '.lis-event-list .txt-quest-title'
            )).find(el => el.textContent.trim() === wanted);
            const card = title?.closest('.lis-event-list');
            const button = card?.querySelector('.btn-stage-detail');
            if (!button) return false;
            if (window.$ && typeof window.$(button).trigger === 'function') {{
                window.$(button).trigger('tap');
            }} else {{
                button.click();
            }}
            return true;
        }})()""")
        if clicked:
            MessageLog.print_message(
                f"[SPECIAL] Opened the modern Special Quest card: {card_title}."
            )
        return bool(clicked)

    @staticmethod
    def _click_special_difficulty(difficulty: str = "", chapter_name: str = "") -> bool:
        """Select a quest row in the currently visible modern Special Quest dialog."""
        from bot.game import Game

        difficulty_values = {
            "Normal": "1",
            "Hard": "2",
            "Very Hard": "3",
            "Extreme": "4",
        }
        if not difficulty and not chapter_name:
            return False
        if difficulty and difficulty not in difficulty_values:
            return False
        difficulty_json = json.dumps(difficulty_values.get(difficulty, ""))
        chapter_json = json.dumps(chapter_name)
        return bool(Game.evaluate_dom_js(f"""(() => {{
            const difficulty = {difficulty_json};
            const chapter = {chapter_json};
            const popup = Array.from(document.querySelectorAll('.pop-quest-detail'))
                .find(el => el.offsetParent !== null);
            if (!popup) return false;

            const rows = Array.from(popup.querySelectorAll('.btn-set-quest'));
            const button = rows.find(el =>
                !el.classList.contains('disable') &&
                (!difficulty || el.dataset.difficulty === difficulty) &&
                (!chapter || el.dataset.chapterName === chapter)
            );
            if (!button) return false;
            if (window.$ && typeof window.$(button).trigger === 'function') {{
                window.$(button).trigger('tap');
            }} else {{
                button.click();
            }}
            return true;
        }})()"""))

    @staticmethod
    def check_for_dimensional_halo():
        """Checks for Dimensional Halo and if it appears and the user enabled it in user settings, start it.

        Returns:
            (bool): Return True if Dimensional Halo was detected and successfully completed. Otherwise, return False.
        """
        from bot.game import Game

        modern_dimension_halo = Special._special_card_exists("Dimension Halo")
        legacy_dimension_halo = False
        if not modern_dimension_halo:
            legacy_dimension_halo = ImageUtils.confirm_location(
                "limited_time_quests", tries = 3, suppress_error = True
            )

        if Settings.enable_nightmare and (modern_dimension_halo or legacy_dimension_halo):
            MessageLog.print_message("\n[D.HALO] Detected Dimensional Halo. Starting it now...")
            Special._dimensional_halo_amount += 1

            MessageLog.print_message("\n********************************************************************************")
            MessageLog.print_message("********************************************************************************")
            MessageLog.print_message(f"[D.HALO] Dimensional Halo")
            MessageLog.print_message(f"[D.HALO] Dimensional Halo Summon Elements: {Settings.nightmare_summon_elements_list}")
            MessageLog.print_message(f"[D.HALO] Dimensional Halo Summons: {Settings.nightmare_summon_list}")
            MessageLog.print_message(f"[D.HALO] Dimensional Halo Group Number: {Settings.nightmare_group_number}")
            MessageLog.print_message(f"[D.HALO] Dimensional Halo Party Number: {Settings.nightmare_party_number}")
            MessageLog.print_message(f"[D.HALO] Dimensional Halo Combat Script: {Settings.nightmare_combat_script_name}")
            MessageLog.print_message("********************************************************************************")
            MessageLog.print_message("********************************************************************************\n")

            if modern_dimension_halo:
                if not Special._click_special_card("Dimension Halo"):
                    raise SpecialException("Failed to open the Dimension Halo card.")
                Game.wait(0.5)
                if not Special._click_special_difficulty(chapter_name = "Dimension Halo"):
                    raise SpecialException("Failed to select the modern Dimension Halo quest row.")
            else:
                # Compatibility fallback for the old Limited-Time Quests popup.
                Game.find_and_click_button("play_next")

            Game.wait(1)

            # Once the bot is at the Summon Selection screen, select your Summon and Party and start the mission.
            if ImageUtils.confirm_location("select_a_summon", tries = 30):
                Game.select_summon(Settings.nightmare_summon_list, Settings.nightmare_summon_elements_list)
                start_check = Game.find_party_and_start_mission(int(Settings.nightmare_group_number), int(Settings.nightmare_party_number), bypass_first_run = True)

                # Once preparations are completed, start Combat Mode.
                if start_check and CombatMode.start_combat_mode(is_nightmare = True):
                    Game.collect_loot_safe(is_completed = False, is_event_nightmare = True)
                    return True

        elif not Settings.enable_nightmare and (modern_dimension_halo or legacy_dimension_halo):
            MessageLog.print_message("\n[D.HALO] Dimensional Halo detected but user opted to not run it. Moving on...")
            if legacy_dimension_halo:
                Game.find_and_click_button("close")
        else:
            MessageLog.print_message("\n[D.HALO] No Dimensional Halo detected. Moving on...")

        return False

    @staticmethod
    def _navigate():
        """Navigates to the specified Special mission.

        Returns:
            None
        """
        from bot.game import Game

        MessageLog.print_message(f"\n[SPECIAL] Beginning process to navigate to the mission: {Settings.mission_name}...")

        # Go to the Home screen.
        Game.go_back_home(confirm_location_check = True)

        # Go to the Quest screen.
        Game.find_and_click_button("quest", suppress_error = True)

        # Check for the "You retreated from the raid battle" popup.
        Game.wait(3.0)
        if ImageUtils.confirm_location("you_retreated_from_the_raid_battle", tries = 3):
            Game.find_and_click_button("ok")

        if Special._is_quest_page():
            # Go to the Special screen.
            Game.find_and_click_button("special")
            Game.wait(1.0)

            # Remove the difficulty prefix from the mission name.
            difficulty = ""
            if Settings.mission_name.find("N ") == 0:
                difficulty = "Normal"
                formatted_mission_name = Settings.mission_name[2:]
            elif Settings.mission_name.find("H ") == 0:
                difficulty = "Hard"
                formatted_mission_name = Settings.mission_name[2:]
            elif Settings.mission_name.find("VH ") == 0:
                difficulty = "Very Hard"
                formatted_mission_name = Settings.mission_name[3:]
            elif Settings.mission_name.find("EX ") == 0:
                difficulty = "Extreme"
                formatted_mission_name = Settings.mission_name[3:]
            else:
                formatted_mission_name = Settings.mission_name

            if Special._is_special_page():
                tries = 2

                # Try to select the specified Special mission for a number of tries.
                while tries != 0:
                    scrolled = False
                    # Scroll the screen down if its any of the Special Quests that are more towards the bottom of the page to alleviate problems for smaller screens.
                    if Settings.map_name != "Campaign-Exclusive Quest" and Settings.map_name != "Uncap Treasure Quests" and Settings.map_name != "Shiny Slime Search!":
                        MouseUtils.scroll_screen_from_home_button(-500)
                        scrolled = True

                    modern_angel_halo = Settings.map_name == "Angel Halo" and \
                        Special._special_card_exists("Angel Halo")

                    if modern_angel_halo:
                        mission_select_button = True
                    elif Settings.map_name == "Showdowns" or Settings.map_name == "Xeno Clash":
                        mission_select_button = ImageUtils.find_button("special_showdowns_xeno_clashes")
                    else:
                        mission_select_button = ImageUtils.find_button(Settings.map_name.lower().replace(" ", "_").replace("-", "_"))

                    if mission_select_button is not None:
                        MessageLog.print_message(f"[SPECIAL] Navigating to {Settings.map_name}...")

                        # Find all instances of the Select button.
                        select_buttons = ImageUtils.find_all("select")
                        if scrolled is False and Settings.map_name != "Campaign-Exclusive Quest" and \
                                ImageUtils.find_button("Campaign-Exclusive Quest".lower().replace(" ", "_").replace("-", "_")) is not None:
                            select_buttons.pop(0)

                        if Settings.map_name == "Uncap Treasure Quests":
                            MouseUtils.move_and_click_point(select_buttons[0][0], select_buttons[0][1], "select")
                            Game.wait(1)

                            locations = ImageUtils.find_all("play_round_button")

                            if formatted_mission_name == "Fire Trial":
                                MessageLog.print_message(f"[SPECIAL] Selecting Fire Trial...")
                                MouseUtils.move_and_click_point(locations[0][0], locations[0][1], "play_round_button")
                            elif formatted_mission_name == "Water Trial":
                                MessageLog.print_message(f"[SPECIAL] Selecting Water Trial...")
                                MouseUtils.move_and_click_point(locations[1][0], locations[1][1], "play_round_button")
                            elif formatted_mission_name == "Earth Trial":
                                MessageLog.print_message(f"[SPECIAL] Selecting Earth Trial...")
                                MouseUtils.move_and_click_point(locations[2][0], locations[2][1], "play_round_button")
                            elif formatted_mission_name == "Wind Trial":
                                MessageLog.print_message(f"[SPECIAL] Selecting Wind Trial...")
                                MouseUtils.move_and_click_point(locations[3][0], locations[3][1], "play_round_button")
                            elif formatted_mission_name == "Light Trial":
                                MessageLog.print_message(f"[SPECIAL] Selecting Light Trial...")
                                MouseUtils.move_and_click_point(locations[4][0], locations[4][1], "play_round_button")
                            elif formatted_mission_name == "Dark Trial":
                                MessageLog.print_message(f"[SPECIAL] Selecting Dark Trial...")
                                MouseUtils.move_and_click_point(locations[5][0], locations[5][1], "play_round_button")

                            Game.wait(1)

                            # Now start the Trial with the specified difficulty.
                            MessageLog.print_message(f"[SPECIAL] Now navigating to {difficulty}...")
                            locations = ImageUtils.find_all("play_round_button")

                            if difficulty == "Normal":
                                MouseUtils.move_and_click_point(locations[0][0], locations[0][1], "play_round_button")
                            elif difficulty == "Hard":
                                MouseUtils.move_and_click_point(locations[1][0], locations[1][1], "play_round_button")
                            elif difficulty == "Very Hard":
                                MouseUtils.move_and_click_point(locations[2][0], locations[2][1], "play_round_button")

                        elif Settings.map_name == "Shiny Slime Search!":
                            # Start up the Shiny Slime Search! mission by selecting its difficulty.
                            MessageLog.print_message(f"[SPECIAL] Selecting {difficulty} Shiny Slime Search!...")

                            MouseUtils.move_and_click_point(select_buttons[1][0], select_buttons[1][1], "select")
                            Game.wait(1)

                            locations = ImageUtils.find_all("play_round_button")

                            if difficulty == "Normal":
                                MouseUtils.move_and_click_point(locations[0][0], locations[0][1], "play_round_button")
                            elif difficulty == "Hard":
                                MouseUtils.move_and_click_point(locations[1][0], locations[1][1], "play_round_button")
                            elif difficulty == "Very Hard":
                                MouseUtils.move_and_click_point(locations[2][0], locations[2][1], "play_round_button")

                        elif Settings.map_name == "Showdowns" or "Xeno" in Settings.map_name:
                            if scrolled:
                                MouseUtils.move_and_click_point(select_buttons[len(select_buttons) - 1 - 2][0], select_buttons[len(select_buttons) - 1 - 2][1], "select")
                            else:
                                MouseUtils.move_and_click_point(select_buttons[2][0], select_buttons[2][1], "select")
                            Game.wait(1)

                            if "Showdown" in formatted_mission_name:
                                # Click on the Showdowns banner.
                                Game.find_and_click_button("special_showdown")
                                locations = ImageUtils.find_all("play_round_button")

                                if formatted_mission_name == "Ifrit Showdown":
                                    # Navigate to Ifrit Showdown.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Ifrit Showdown...")
                                    MouseUtils.move_and_click_point(locations[0][0], locations[0][1], "play_round_button")
                                elif formatted_mission_name == "Cocytus Showdown":
                                    # Navigate to Cocytus Showdown.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Cocytus Showdown...")
                                    MouseUtils.move_and_click_point(locations[1][0], locations[1][1], "play_round_button")
                                elif formatted_mission_name == "Vohu Manah Showdown":
                                    # Navigate to Vohu Manah Showdown.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Vohu Manah Showdown...")
                                    MouseUtils.move_and_click_point(locations[2][0], locations[2][1], "play_round_button")
                                elif formatted_mission_name == "Sagittarius Showdown":
                                    # Navigate to Sagittarius Showdown.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Sagittarius Showdown...")
                                    MouseUtils.move_and_click_point(locations[3][0], locations[3][1], "play_round_button")
                                elif formatted_mission_name == "Corow Showdown":
                                    # Navigate to Corow Showdown.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Corow Showdown...")
                                    MouseUtils.move_and_click_point(locations[4][0], locations[4][1], "play_round_button")
                                elif formatted_mission_name == "Diablo Showdown":
                                    # Navigate to Diablo Showdown.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Diablo Showdown...")
                                    MouseUtils.move_and_click_point(locations[5][0], locations[5][1], "play_round_button")

                                Game.wait(1)
                                MessageLog.print_message(f"[SPECIAL] Now navigating to {difficulty}...")
                                locations = ImageUtils.find_all("play_round_button")
                                if difficulty == "Hard":
                                    MouseUtils.move_and_click_point(locations[0][0], locations[0][1], "play_round_button")
                                elif difficulty == "Very Hard":
                                    MouseUtils.move_and_click_point(locations[1][0], locations[1][1], "play_round_button")
                                elif difficulty == "Extreme":
                                    MouseUtils.move_and_click_point(locations[2][0], locations[2][1], "play_round_button")
                            elif "Xeno" in formatted_mission_name:
                                # Click on the Clashes banner.
                                Game.find_and_click_button("special_xeno_clash")
                                locations = ImageUtils.find_all("play_round_button")

                                if "Xeno Ifrit" in formatted_mission_name:
                                    # Navigate to Xeno Ifrit.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Xeno Ifrit...")
                                    MouseUtils.move_and_click_point(locations[0][0], locations[0][1], "play_round_button")
                                elif "Xeno Cocytus" in formatted_mission_name:
                                    # Navigate to Xeno Cocytus.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Xeno Cocytus...")
                                    MouseUtils.move_and_click_point(locations[1][0], locations[1][1], "play_round_button")
                                elif "Xeno Vohu Manah" in formatted_mission_name:
                                    # Navigate to Xeno Vohu Manah.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Xeno Vohu Manah...")
                                    MouseUtils.move_and_click_point(locations[2][0], locations[2][1], "play_round_button")
                                elif "Xeno Sagittarius" in formatted_mission_name:
                                    # Navigate to Xeno Sagittarius.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Xeno Sagittarius...")
                                    MouseUtils.move_and_click_point(locations[3][0], locations[3][1], "play_round_button")
                                elif "Xeno Corow" in formatted_mission_name:
                                    # Navigate to Xeno Corow.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Xeno Corow...")
                                    MouseUtils.move_and_click_point(locations[4][0], locations[4][1], "play_round_button")
                                elif "Xeno Diablo" in formatted_mission_name:
                                    # Navigate to Xeno Diablo.
                                    MessageLog.print_message(f"[SPECIAL] Selecting Xeno Diablo...")
                                    MouseUtils.move_and_click_point(locations[5][0], locations[5][1], "play_round_button")

                                Game.wait(1)
                                MessageLog.print_message(f"[SPECIAL] Now navigating to Level 60 for Xeno...")
                                locations = ImageUtils.find_all("play_round_button")
                                MouseUtils.move_and_click_point(locations[0][0], locations[0][1], "play_round_button")

                        elif Settings.map_name == "Campaign-Exclusive Quest":
                            MessageLog.print_message(f"[SPECIAL] Selecting Campaign-Exclusive Quest...")

                            MouseUtils.move_and_click_point(select_buttons[0][0], select_buttons[0][1], "select")
                            Game.wait(1)

                            locations = ImageUtils.find_all("play_round_button")

                            # There is only one round "Play" button for this time-limited quest.
                            MouseUtils.move_and_click_point(locations[0][0], locations[0][1], "play_round_button")

                        else:
                            # Start up the Angel Halo mission by selecting its difficulty.
                            MessageLog.print_message(f"[SPECIAL] Selecting {difficulty} Angel Halo...")

                            if modern_angel_halo:
                                if not Special._click_special_card("Angel Halo"):
                                    raise SpecialException("Failed to open the modern Angel Halo card.")
                            elif scrolled:
                                MouseUtils.move_and_click_point(select_buttons[len(select_buttons) - 1 - 1][0], select_buttons[len(select_buttons) - 1 - 1][1], "select")
                            else:
                                MouseUtils.move_and_click_point(select_buttons[3][0], select_buttons[3][1], "select")
                            Game.wait(1)

                            if not Special._click_special_difficulty(difficulty = difficulty):
                                locations = ImageUtils.find_all("play_round_button")

                                if difficulty == "Normal":
                                    MouseUtils.move_and_click_point(locations[0][0], locations[0][1], "play_round_button")
                                elif difficulty == "Hard":
                                    MouseUtils.move_and_click_point(locations[1][0], locations[1][1], "play_round_button")
                                elif difficulty == "Very Hard":
                                    MouseUtils.move_and_click_point(locations[2][0], locations[2][1], "play_round_button")

                        break
                    else:
                        # Scroll the screen down more if on a smaller screen and it obscures the targeted mission.
                        MouseUtils.scroll_screen(Settings.home_button_location[0], Settings.home_button_location[1] - 50, -500)
                        tries -= 1
            else:
                raise SpecialException("Failed to arrive at the Special page to continue with Special navigation.")
        else:
            raise SpecialException("Failed to arrive at the Quest page to continue with Special navigation.")

        return None

    @staticmethod
    def start(first_run: bool):
        """Starts the process to complete a run for Special Farming Mode and returns the number of items detected.

        Args:
            first_run (bool): Flag that determines whether or not to run the navigation process again. Should be False if the Farming Mode supports the "Play Again" feature for repeated runs.

        Returns:
            None
        """
        from bot.game import Game

        # A stocked Dimension Halo is now rendered as a regular card on the
        # Special Quest page instead of the old Limited-Time Quests popup.
        # If the user deliberately starts there, clear it first and then
        # continue with the configured VH Angel Halo run in the same cycle.
        ran_open_dimension_halo = False
        if first_run and Settings.enable_nightmare and \
                Settings.mission_name == "VH Angel Halo" and \
                Settings.item_name == "Angel Halo Weapons" and \
                Special._is_special_page() and \
                Special._special_card_exists("Dimension Halo"):
            ran_open_dimension_halo = Special.check_for_dimensional_halo()

        # Start the navigation process.
        if first_run or ran_open_dimension_halo:
            Special._navigate()
        elif Game.find_and_click_button("play_again"):
            if Game.check_for_popups():
                Special._navigate()
        else:
            # If the bot cannot find the "Play Again" button, check for Pending Battles and then perform navigation again.
            Game.check_for_pending()
            Special._navigate()

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
            raise SpecialException("Failed to arrive at the Summon Selection screen.")

        return None
