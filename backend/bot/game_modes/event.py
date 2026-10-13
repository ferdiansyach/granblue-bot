from utils.settings import Settings
from utils.message_log import MessageLog
from utils.image_utils import ImageUtils
from utils.mouse_utils import MouseUtils
from bot.combat_mode import CombatMode


class EventException(Exception):
    def __init__(self, message):
        super().__init__(message)


class Event:
    """
    Provides the navigation and any necessary utility functions to handle the Event or Event (Token Drawboxes) game mode.
    """

    @staticmethod
    def check_for_event_nightmare():
        """Checks for Event Nightmare and if it appears and the user enabled it in user settings, start it.

        Returns:
            (bool): Return True if Event Nightmare was detected and successfully completed. Otherwise, return False.
        """
        from bot.game import Game

        if Settings.enable_nightmare and ImageUtils.find_button("event_claim_loot"):
            # First check if the Event Nightmare is skippable.
            event_claim_loot_location = ImageUtils.find_button("event_claim_loot", suppress_error = True)
            if event_claim_loot_location is not None:
                MessageLog.print_message("\n[EVENT] Skippable Event Nightmare detected. Claiming it now...")
                MouseUtils.move_and_click_point(event_claim_loot_location[0], event_claim_loot_location[1], "event_claim_loot")
                Game.collect_loot_safe(is_completed = False, is_event_nightmare = True)
                return True
            else:
                MessageLog.print_message("\n[EVENT] Detected Event Nightmare. Starting it now...")

                MessageLog.print_message("\n********************************************************************************")
                MessageLog.print_message("********************************************************************************")
                MessageLog.print_message(f"[EVENT] Event Nightmare")
                MessageLog.print_message(f"[EVENT] Event Nightmare Summon Elements: {Settings.nightmare_summon_elements_list}")
                MessageLog.print_message(f"[EVENT] Event Nightmare Summons: {Settings.nightmare_summon_list}")
                MessageLog.print_message(f"[EVENT] Event Nightmare Group Number: {Settings.nightmare_group_number}")
                MessageLog.print_message(f"[EVENT] Event Nightmare Party Number: {Settings.nightmare_party_number}")
                MessageLog.print_message(f"[EVENT] Event Nightmare Combat Script: {Settings.nightmare_combat_script_name}")
                MessageLog.print_message("********************************************************************************")
                MessageLog.print_message("********************************************************************************\n")

                # Click the "Play Next" button to head to the Summon Selection screen.
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

        elif not Settings.enable_nightmare and ImageUtils.find_button("event_claim_loot"):
            # First check if the Event Nightmare is skippable.
            event_claim_loot_location = ImageUtils.find_button("event_claim_loot", suppress_error = True)
            if event_claim_loot_location is not None:
                MessageLog.print_message("\n[EVENT] Skippable Event Nightmare detected but user opted to not run it. Claiming it regardless...")
                MouseUtils.move_and_click_point(event_claim_loot_location[0], event_claim_loot_location[1], "event_claim_loot")
                Game.collect_loot_safe(is_completed = False, is_event_nightmare = True)
                return True
            else:
                MessageLog.print_message("\n[EVENT] Event Nightmare detected but user opted to not run it. Moving on...")
                Game.find_and_click_button("close")
        else:
            MessageLog.print_message("\n[EVENT] No Event Nightmare detected. Moving on...")

        return False

    @staticmethod
    def _navigate_token_drawboxes():
        """Navigates to the specified Event (Token Drawboxes) mission.

        Returns:
            None
        """
        from bot.game import Game

        MessageLog.print_message(f"[EVENT.TOKEN.DRAWBOXES] Now beginning process to navigate to the mission: {Settings.mission_name}...")

        # Go to the Home screen.
        Game.go_back_home(confirm_location_check = True)

        # Go to the Event by clicking on the "Menu" button and then click the very first banner.
        Game.find_and_click_button("home_menu")
        Game.wait(1.5)

        # Check if the Event banner is already visible in the opened Menu
        banner_locations = ImageUtils.find_all("event_banner", custom_confidence = 0.75)
        if len(banner_locations) == 0:
            banner_locations = ImageUtils.find_all("event_banner_blue", custom_confidence = 0.75)

        # If not visible yet, scroll down in the Home Menu
        scroll_count = 0
        max_scrolls = 3
        while len(banner_locations) == 0 and scroll_count < max_scrolls:
            MessageLog.print_message(f"[EVENT.TOKEN.DRAWBOXES] Scrolling to find event banner (attempt {scroll_count + 1})...")
            MouseUtils.scroll_screen_from_home_button(-200)
            Game.wait(1.5)
            banner_locations = ImageUtils.find_all("event_banner", custom_confidence = 0.75)
            if len(banner_locations) == 0:
                banner_locations = ImageUtils.find_all("event_banner_blue", custom_confidence = 0.75)
            scroll_count += 1

        if len(banner_locations) == 0:
            raise EventException("Failed to find the Event banner.")

        MessageLog.print_message(f"[EVENT.TOKEN.DRAWBOXES] Found {len(banner_locations)} event banner(s).")

        if Settings.event_enable_new_position:
            if Settings.event_new_position > len(banner_locations) - 1:
                raise EventException("Value set for New Position was found to be invalid compared to the actual number of events found in the Home Menu.")
            target_idx = Settings.event_new_position
        else:
            # For Exo Corow, the banner might be at position 0 or 1 depending on layout
            target_idx = 0
            if len(banner_locations) > 1:
                # Check if the first banner looks like it's the right size/position
                MessageLog.print_message(f"[EVENT.TOKEN.DRAWBOXES] Choosing banner at position {target_idx}")

        MouseUtils.move_and_click_point(banner_locations[target_idx][0], banner_locations[target_idx][1], "event_banner")
        MessageLog.print_message(f"[EVENT.TOKEN.DRAWBOXES] Clicked event banner.")
        Game.wait(4.0)  # Increased wait time for page load

        # Check and click away the "Daily Missions" popup.
        # For Exo Crucible, we need to check this BEFORE proceeding to mission selection
        if Settings.mission_name == "Exo Corow" and ImageUtils.confirm_location("event_daily_missions", tries = 3):
            MessageLog.print_message(f"\n[EVENT.TOKEN.DRAWBOXES] Detected \"Daily Missions\" popup. Clicking it away...")
            Game.find_and_click_button("close")

        # Remove the difficulty prefix from the mission name.
        difficulty = ""
        formatted_mission_name = ""
        if Settings.mission_name.find("VH ") == 0:
            difficulty = "Very Hard"
            formatted_mission_name = Settings.mission_name[3:]
        elif Settings.mission_name.find("EX ") == 0:
            difficulty = "Extreme"
            formatted_mission_name = Settings.mission_name[3:]
        elif Settings.mission_name.find("EX+ ") == 0:
            difficulty = "Extreme+"
            formatted_mission_name = Settings.mission_name[4:]
        elif Settings.mission_name.find("IM ") == 0:
            difficulty = "Impossible"
            formatted_mission_name = Settings.mission_name[3:]
        else:
            formatted_mission_name = Settings.mission_name

        # For Exo Crucible, no need to scroll - the event page layout is different
        # Skip the Token Drawboxes scroll for Exo Corow to avoid navigating away from event page

        if "Exo" in formatted_mission_name or formatted_mission_name == "Exo Corow":
            MessageLog.print_message("[EVENT.TOKEN.DRAWBOXES] Starting Exo Corow...")

            # Wait for the Event page to load and confirm we're there
            # Check for any of these indicators that we're on the Exo Crucible event page
            event_page_confirmed = False
            for confirm_attempt in range(10):
                # Try multiple indicators: exo_crucible button, event_solo_battle, or event_play
                if ImageUtils.find_button("exo_crucible", tries=1, suppress_error=True) or \
                   ImageUtils.find_button("event_solo_battle", tries=1, suppress_error=True) or \
                   ImageUtils.confirm_location("event_play", tries=1, suppress_error=True):
                    event_page_confirmed = True
                    break
                Game.wait(0.5)

            if not event_page_confirmed:
                MessageLog.print_message("[WARNING] Event page indicators not found, checking for popups and retrying...")
                # Dismiss any potential popups
                Game.find_and_click_button("close", tries=3, suppress_error=True)
                Game.find_and_click_button("ok", tries=3, suppress_error=True)
                Game.wait(2.0)

                # Re-check after dismissing popups
                for retry_attempt in range(5):
                    if ImageUtils.find_button("exo_crucible", tries=1, suppress_error=True) or \
                       ImageUtils.find_button("event_solo_battle", tries=1, suppress_error=True) or \
                       ImageUtils.confirm_location("event_play", tries=1, suppress_error=True):
                        event_page_confirmed = True
                        MessageLog.print_message("[EVENT.TOKEN.DRAWBOXES] Event page confirmed after dismissing popups.")
                        break
                    Game.wait(1.0)

                if not event_page_confirmed:
                    MessageLog.print_message("[WARNING] Event page still not confirmed. Trying DOM check...")
                    # Check URL hash via DOM
                    hash_check = Game.evaluate_dom_js("""(() => {
                        let hash = window.location.hash || '';
                        return hash.includes('event') || hash.includes('quest') || hash.includes('battle');
                    })()""")
                    if hash_check:
                        MessageLog.print_message("[EVENT.TOKEN.DRAWBOXES] DOM confirms we're on an event-related page.")

            # Click the Exo Crucible button (card/tile for Exo Crucible battles)
            exo_crucible_location = ImageUtils.find_button("exo_crucible", custom_confidence=0.75, tries=5, suppress_error=True)
            if exo_crucible_location is None:
                # Try alternate: event_solo_battle button
                exo_crucible_location = ImageUtils.find_button("event_solo_battle", custom_confidence=0.75, tries=5, suppress_error=True)

            if exo_crucible_location is not None:
                MouseUtils.move_and_click_point(exo_crucible_location[0], exo_crucible_location[1], "exo_crucible")
                MessageLog.print_message("[EVENT.TOKEN.DRAWBOXES] Clicked Exo Crucible button.")
            else:
                # Try DOM click for Crucible card
                dom_card = Game.evaluate_dom_js("""(() => {
                    let card = document.querySelector('.btn-quest-start, [data-quest-type=\"crucible\"], .btn-stage-detail');
                    if (card && card.offsetParent !== null) {
                        if (window.$) { try { $(card).trigger('tap'); } catch(e){} }
                        card.click();
                        return true;
                    }
                    return false;
                })()""")
                if dom_card:
                    MessageLog.print_message("[EVENT.TOKEN.DRAWBOXES] Clicked Exo Crucible card via DOM.")
                else:
                    MessageLog.print_message("[EVENT.TOKEN.DRAWBOXES] Exo Crucible button not found, checking for Play button...")

            Game.wait(2.5)

            # Click the Play button on the modal popup
            play_clicked = Game.find_and_click_button("event_play", tries=5, suppress_error=True)
            if not play_clicked:
                # Fallback: check play_round_button
                play_clicked = Game.find_and_click_button("play_round_button", custom_confidence=0.70, tries=3, suppress_error=True)

            if not play_clicked:
                # Last resort: try to start via DOM
                dom_play = Game.evaluate_dom_js("""(() => {
                    let btns = Array.from(document.querySelectorAll('.pop-usual .btn-quest-start, .btn-usual-ok, .btn-quest-start'));
                    for (let b of btns) {
                        let txt = (b.innerText || b.textContent || '').trim();
                        if (b.offsetParent !== null && (txt.includes('Play') || txt.includes('Start') || txt.includes('AP'))) {
                            if (window.$) { try { $(b).trigger('tap'); } catch(e){} }
                            b.click();
                            return true;
                        }
                    }
                    return false;
                })()""")
                if dom_play:
                    MessageLog.print_message("[EVENT.TOKEN.DRAWBOXES] Clicked Play on Crucible popup via DOM.")
                    play_clicked = True

            Game.wait(3.0)
            return None
        elif formatted_mission_name == "Event Quest":
            MessageLog.print_message(f"[EVENT.TOKEN.DRAWBOXES] Now hosting Event Quest...")
            if Game.find_and_click_button("event_quests") is False:
                raise EventException("Failed to proceed any further in Event (Token Drawboxes) navigation by missing the Event Quests button.")

            Game.wait(1)

            # Find all the round "Play" buttons.
            quest_play_locations = ImageUtils.find_all("play_round_button")

            # Only Extreme and Extreme+ difficulty is supported for farming efficiency.
            if difficulty == "Extreme":
                MouseUtils.move_and_click_point(quest_play_locations[3][0], quest_play_locations[3][1], "play_round_button")
            elif difficulty == "Extreme+":
                MouseUtils.move_and_click_point(quest_play_locations[4][0], quest_play_locations[4][1], "play_round_button")
        elif formatted_mission_name == "Event Raid":
            # Bring up the "Raid Battle" popup. Then scroll down the screen a bit for screens less than 1440p to see the entire popup.
            MessageLog.print_message(f"[EVENT.TOKEN.DRAWBOXES] Now hosting Event Raid...")
            if not Game.find_and_click_button("event_raid_battle"):
                raise EventException("Failed to detect Token Drawbox layout for this Event. Are you sure this Event has Token Drawboxes? If not, switch to \"Event\" Farming Mode.")
            MouseUtils.scroll_screen_from_home_button(-200)

            Game.wait(1)

            # Try finding and clicking the raid difficulty card via DOM directly first
            dom_card = Game.evaluate_dom_js(f"""(() => {{
                let diff = "{difficulty.lower()}";
                let btns = Array.from(document.querySelectorAll('.pop-select-raid .btn-quest-start, .btn-quest-start'));
                for (let b of btns) {{
                    let ap = b.dataset.ap || '';
                    let cname = (b.dataset.chapterName || '').toLowerCase();
                    let match = false;
                    if (diff.includes('very hard') || diff.includes('vh')) {{
                        match = (ap === '20' || cname.includes('very hard') || cname.includes('envoy'));
                    }} else if (diff.includes('impossible') || diff.includes('extreme+')) {{
                        match = (ap === '40' || cname.includes('impossible') || cname.includes('merlin'));
                    }} else if (diff.includes('extreme')) {{
                        match = (ap === '30' || cname.includes('extreme') || cname.includes('barrier') || cname.includes('master'));
                    }}
                    if (match && b.offsetParent !== null) {{
                        let r = b.getBoundingClientRect();
                        if (window.$) {{ try {{ $(b).trigger('tap'); }} catch(e){{}} }}
                        b.click();
                        return JSON.stringify({{ cx: r.x + r.width / 2, cy: r.y + r.height / 2 }});
                    }}
                }}
                return null;
            }})()""")

            if dom_card:
                MessageLog.print_message(f"[INFO] Selected {difficulty} raid card via DOM.")
                if Settings.window_left is not None and Settings.window_top is not None:
                    try:
                        import json as _json
                        pt = _json.loads(dom_card)
                        screen_x = Settings.window_left + int(pt["cx"])
                        screen_y = Settings.window_top + int(pt["cy"])
                        diff_slug = difficulty.lower().replace(" ", "_").replace("+", "")
                        MouseUtils.move_and_click_point(screen_x, screen_y, f"event_raid_{diff_slug}")
                    except Exception:
                        pass
                return None

            # If not found directly, check categories (only if raids are split into multiple tabs)
            categories = ImageUtils.find_all("event_raid_category")
            if len(categories) > 0:
                if Settings.enable_select_bottom_category is False:
                    MouseUtils.move_and_click_point(categories[0][0] - 50, categories[0][1], "event_raid_category")
                elif len(categories) > 1:
                    MouseUtils.move_and_click_point(categories[1][0] - 50, categories[1][1], "event_raid_category")
                else:
                    MessageLog.print_message("[WARNING] Only 1 category detected. Selecting the available category.")
                    MouseUtils.move_and_click_point(categories[0][0] - 50, categories[0][1], "event_raid_category")

            # Try finding the difficulty directly via its template badge
            raid_btn_name = f"event_raid_{difficulty.lower().replace(' ', '_').replace('+', '')}"
            card_location = ImageUtils.find_button(raid_btn_name, suppress_error = True)

            if card_location is not None:
                # Click the card / AP button directly (y + 45)
                MouseUtils.move_and_click_point(card_location[0], card_location[1] + 45, raid_btn_name)
                return None

            # Fallback: check for standard AP badge or AP-0 free badge
            ap_locations = ImageUtils.find_all("ap")
            if len(ap_locations) == 0:
                ap_locations = ImageUtils.find_all("ap_free")
            if len(ap_locations) > 0:
                # Always sort left-to-right by x coordinate because raid difficulty cards are arranged horizontally
                ap_locations.sort(key = lambda pt: pt[0])

            if difficulty == "Very Hard":
                if len(ap_locations) > 0:
                    target_x, target_y = ap_locations[0][0], ap_locations[0][1]
                else:
                    target_x, target_y = Settings.window_left + 175, 660
                MouseUtils.move_and_click_point(target_x, target_y, "ap")
                return None
            elif difficulty == "Extreme":
                if len(ap_locations) >= 2:
                    target_x, target_y = ap_locations[1][0], ap_locations[1][1]
                elif len(ap_locations) == 1:
                    target_x, target_y = ap_locations[0][0] + 160, ap_locations[0][1]
                else:
                    target_x, target_y = Settings.window_left + 335, 660
                MouseUtils.move_and_click_point(target_x, target_y, "ap")
                return None
            elif difficulty == "Impossible":
                if len(ap_locations) >= 3:
                    target_x, target_y = ap_locations[2][0], ap_locations[2][1]
                elif len(ap_locations) == 2:
                    target_x, target_y = ap_locations[1][0] + 160, ap_locations[1][1]
                elif len(ap_locations) == 1:
                    target_x, target_y = ap_locations[0][0] + 320, ap_locations[0][1]
                else:
                    target_x, target_y = Settings.window_left + 495, 660
                MouseUtils.move_and_click_point(target_x, target_y, "ap")
                return None

            # If the user does not have enough Treasures to host a Extreme or an Impossible Raid, host a Very Hard Raid instead.
            MessageLog.print_message(f"[EVENT.TOKEN.DRAWBOXES] Not enough materials to host {difficulty}. Hosting Very Hard instead...")
            if len(ap_locations) > 0:
                MouseUtils.move_and_click_point(ap_locations[0][0], ap_locations[0][1], "ap")
            else:
                MouseUtils.move_and_click_point(Settings.window_left + 175, 660, "ap")

        return None

    @staticmethod
    def _navigate():
        """Navigates to the specified Event mission.

        Returns:
            None
        """
        from bot.game import Game

        # Switch over to the navigation logic for Event (Token Drawboxes) if needed.
        if Settings.farming_mode == "Event (Token Drawboxes)":
            Event._navigate_token_drawboxes()
        else:
            MessageLog.print_message(f"[EVENT] Now beginning process to navigate to the mission: {Settings.mission_name}...")

            # Go to the Home screen.
            Game.go_back_home(confirm_location_check = True)

            Game.find_and_click_button("quest")

            Game.wait(3.0)

            # Check for the "You retreated from the raid battle" popup.
            if ImageUtils.confirm_location("you_retreated_from_the_raid_battle", tries = 3):
                Game.find_and_click_button("ok")

            # Go to the Special screen.
            Game.find_and_click_button("special")
            Game.wait(3.0)

            Game.find_and_click_button("special_event")

            # Remove the difficulty prefix from the mission name.
            difficulty = ""
            formatted_mission_name = ""
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
            elif Settings.mission_name.find("EX+ ") == 0:
                difficulty = "Extreme+"
                formatted_mission_name = Settings.mission_name[4:]
            else:
                formatted_mission_name = Settings.mission_name

            if ImageUtils.confirm_location("special"):
                # Check to see if the user already has a Nightmare available.
                nightmare_is_available = 0
                if ImageUtils.find_button("event_nightmare") is not None:
                    nightmare_is_available = 1

                # Find all the "Select" buttons.
                select_button_locations = ImageUtils.find_all("select")
                if Settings.enable_event_location_incrementation_by_one:
                    position = 1
                else:
                    position = 0

                # Select the Event Quest or Event Raid. Additionally, offset the locations by 1 if there is a Nightmare available.
                try:
                    if formatted_mission_name == "Event Quest":
                        MessageLog.print_message(f"[EVENT] Now hosting Event Quest...")
                        MouseUtils.move_and_click_point(select_button_locations[position + nightmare_is_available][0], select_button_locations[position + nightmare_is_available][1], "select")
                    elif formatted_mission_name == "Event Raid":
                        MessageLog.print_message(f"[EVENT] Now hosting Event Raid...")
                        MouseUtils.move_and_click_point(select_button_locations[(position + 1) + nightmare_is_available][0], select_button_locations[(position + 1) + nightmare_is_available][1],
                                                        "play_round_button")
                except IndexError as e:
                    MessageLog.print_message(f"\n[ERROR] Turn on/off the 'Enable Incrementation of Location by 1' and try again.")
                    raise IndexError(e)

                Game.wait(1)

                # Find all the round "Play" buttons.
                round_play_button_locations = ImageUtils.find_all("play_round_button")

                # If Extreme+ was selected and only 3 locations were found for the play_round_button, that means Extreme+ is not available.
                if len(round_play_button_locations) == 3 and difficulty == "Extreme+":
                    MessageLog.print_message(f"[EVENT] Extreme+ was selected but it seems it is not available. Defaulting to Extreme difficulty...")
                    difficulty = "Extreme"

                # Now select the chosen difficulty.
                if difficulty == "Very Hard":
                    MouseUtils.move_and_click_point(round_play_button_locations[0][0], round_play_button_locations[0][1], "play_round_button")
                elif difficulty == "Extreme":
                    MouseUtils.move_and_click_point(round_play_button_locations[1][0], round_play_button_locations[1][1], "play_round_button")
                elif difficulty == "Extreme+":
                    MouseUtils.move_and_click_point(round_play_button_locations[2][0], round_play_button_locations[2][1], "play_round_button")
            else:
                raise EventException("Failed to arrive at the Special Quest screen.")

        return None

    @staticmethod
    def _handle_post_battle_popups():
        """Handles all popups that appear after a raid battle concludes.

        Sequence:
          1. Wait until the browser is on the Quest Result page (#result_multi or exp_gained/loot_collected).
          2. Dismiss all OK / close / cancel popups until the Loot Collected screen is reached.
          3. Leave the bot at the Loot Collected screen so the caller can click Play Again.

        Returns:
            None
        """
        from bot.game import Game

        MessageLog.print_message("[EVENT] Waiting for Quest Result page to appear...")

        # ----------------------------------------------------------------
        # Step 0: Wait until the result page is loaded.
        # Poll the current URL and also check for exp_gained / loot_collected images.
        # ----------------------------------------------------------------
        result_wait_tries = 60          # max ~60 seconds
        on_result_page = False
        while result_wait_tries > 0 and not on_result_page:
            result_wait_tries -= 1

            # Check via DOM whether the URL contains "result"
            current_url = Game.evaluate_dom_js("window.location.href") or ""
            if "result" in str(current_url):
                on_result_page = True
                break

            # Also accept if loot images are already visible
            from utils.image_utils import ImageUtils
            if ImageUtils.confirm_location("exp_gained",   tries=1, suppress_error=True, bypass_general_adjustment=True) or \
               ImageUtils.confirm_location("loot_collected", tries=1, suppress_error=True, bypass_general_adjustment=True):
                on_result_page = True
                break

            Game.wait(1.0)

        if on_result_page:
            MessageLog.print_message("[EVENT] Quest Result page detected.")
        else:
            MessageLog.print_message("[EVENT] Quest Result page not detected after waiting. Attempting reload to reach result page...")
            Game.find_and_click_button("reload")
            Game.wait(4.0)

        # ----------------------------------------------------------------
        # Step 1: Retry-loop — dismiss all OK / close popups until we reach
        #         the Loot Collected screen.
        # ----------------------------------------------------------------
        from utils.image_utils import ImageUtils
        dismiss_tries = 30
        MessageLog.print_message("[EVENT] Dismissing post-battle popups...")
        while dismiss_tries > 0:
            dismiss_tries -= 1

            # If Loot Collected screen is already visible, we're done.
            reached_loot = Game.evaluate_dom_js("""(() => {
                let again = document.querySelector('.btn-again, .btn-retry');
                let popup = document.querySelector('.btn-usual-ok, .btn-result-next, .btn-usual-close');
                return Boolean(again && again.offsetParent !== null && (!popup || popup.offsetParent === null));
            })()""")
            if reached_loot or ImageUtils.confirm_location("loot_collected", tries=1, suppress_error=True, bypass_general_adjustment=True):
                MessageLog.print_message("[EVENT] Loot Collected screen reached.")
                break

            # Try DOM OK click (covers .btn-usual-ok and .btn-result-next).
            clicked = Game.evaluate_dom_js("""(() => {
                let sel = ['.btn-usual-ok', '.btn-result-next', '.btn-usual-close', '.btn-close'];
                for (let s of sel) {
                    let el = document.querySelector(s);
                    if (el && el.offsetParent !== null) {
                        if (window.$) { try { $(el).trigger('tap'); } catch(e){} }
                        el.click();
                        return s;
                    }
                }
                return null;
            })()""")

            if clicked:
                MessageLog.print_message(f"[EVENT] Dismissed popup via DOM ({clicked}).")
                Game.wait(1.5)
                continue

            # Check if on Quest Result screen to prevent false-positive image matching on Event Home
            is_on_result = Game.evaluate_dom_js("""(() => {
                let hash = window.location.hash || '';
                let again = document.querySelector('.btn-again, .btn-retry');
                return Boolean(hash.includes('result') || (again && again.offsetParent !== null));
            })()""")

            if not is_on_result:
                # Fallback to image-based OK / close buttons only when NOT on result page.
                if Game.find_and_click_button("ok", tries=1, suppress_error=True):
                    MessageLog.print_message("[EVENT] Clicked OK popup.")
                    Game.wait(1.5)
                    continue

                if Game.find_and_click_button("close", tries=1, suppress_error=True):
                    MessageLog.print_message("[EVENT] Clicked Close popup.")
                    Game.wait(1.5)
                    continue

            # Nothing to dismiss right now — wait a moment.
            Game.wait(1.0)

        MessageLog.print_message("[EVENT] Post-battle popup handling complete.")
        return None

    @staticmethod
    def start(first_run: bool):
        """Starts the process to complete a run for Event or Event (Token Drawboxes) Farming Mode and returns the number of items detected.

        Args:
            first_run (bool): Flag that determines whether or not to run the navigation process again. Should be False if the Farming Mode supports the "Play Again" feature for repeated runs.

        Returns:
            None
        """
        from bot.game import Game

        # Start the navigation process.
        if first_run:
            Event._navigate()
        else:
            # Handle any post-battle popups before looking for "Play Again".
            # This will wait for Quest Result page and dismiss all OK popups
            # until Loot Collected screen is reached.
            Event._handle_post_battle_popups()

            # ------------------------------------------------------------------
            # Find and click Play Again using DOM-based data-href navigation /
            # coordinate fallback.
            # ------------------------------------------------------------------
            play_again_clicked = False
            for attempt in range(5):
                if Game.find_and_click_play_again():
                    MessageLog.print_message(f"[EVENT] Clicked Play Again (attempt {attempt + 1}).")
                    play_again_clicked = True
                    break
                MessageLog.print_message(f"[EVENT] Play Again not found yet (attempt {attempt + 1}/5). Waiting...")
                Game.wait(2.0)

            if play_again_clicked:
                MessageLog.print_message("[EVENT] Clicked Play Again. Waiting for summon / party selection screen...")
                Game._wait_for_navigation_after_play_again()
            else:
                # If Play Again is still not visible, check for Pending Battles and re-navigate.
                MessageLog.print_message("[EVENT] Play Again button not found after retries. Checking for pending battles and re-navigating...")
                Game.check_for_pending()
                Event._navigate()

        # Check for AP.
        Game.check_for_ap()

        # Check if the bot is at the Summon Selection screen.
        at_summon_screen = Game.evaluate_dom_js("""(() => {
            let hash = window.location.hash || '';
            return hash.includes('supporter') || Boolean(document.querySelector('.prt-supporter-detail, .btn-supporter'));
        })()""")
        if at_summon_screen or ImageUtils.confirm_location("select_a_summon", tries = 30):
            summon_check = Game.select_summon(Settings.summon_list, Settings.summon_element_list)

            if summon_check:
                # Select the Party.
                Game.find_party_and_start_mission(Settings.group_number, Settings.party_number)

                # Now start Combat Mode and detect any item drops.
                if CombatMode.start_combat_mode():
                    Game.collect_loot_safe(is_completed = True)
        else:
            raise EventException("Failed to arrive at the Summon Selection screen.")

        return None