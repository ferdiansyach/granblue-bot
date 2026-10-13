import multiprocessing
import random
import time
import traceback
from typing import List, Optional

import pyautogui

# The order of the following imports matter to avoid circular import error.
from utils.settings import Settings
from utils.message_log import MessageLog
from utils import discord_utils
from utils.image_utils import ImageUtils
from utils.mouse_utils import MouseUtils
# Imports for all the supported game modes.
from bot.game_modes.arcarum import Arcarum
from bot.game_modes.arcarum_sandbox import ArcarumSandbox
from bot.game_modes.coop import Coop
from bot.game_modes.dread_barrage import DreadBarrage
from bot.game_modes.event import Event
from bot.game_modes.guild_wars import GuildWars
from bot.game_modes.proving_grounds import ProvingGrounds
from bot.game_modes.quest import Quest
from bot.game_modes.raid import Raid
from bot.game_modes.rotb import RiseOfTheBeasts
from bot.game_modes.special import Special
from bot.game_modes.generic import Generic
from bot.game_modes.generic_v2 import GenericV2
from bot.window import Window


class Game:
    """
    Main driver for bot activity and navigation for the web browser bot, Granblue Fantasy.
    """

    _discord_process = None
    _discord_queue = multiprocessing.Queue()
    _cached_ws_url = None
    _last_party_start_status = None

    def __init__(self):
        super().__init__()

    @staticmethod
    def _send_discord_message(message: str) -> bool:
        """Queue a Discord message only when a live consumer exists."""
        if not Settings.enable_discord:
            return False
        if Game._discord_process is None or not Game._discord_process.is_alive():
            return False
        Game._discord_queue.put(message)
        return True

    @staticmethod
    def _uses_run_progress() -> bool:
        return Settings.progress_mode in ("completedruns", "completed_runs", "runs")

    @staticmethod
    def _current_progress() -> int:
        if Game._uses_run_progress():
            return Settings.amount_of_runs_finished
        return Settings.item_amount_farmed

    @staticmethod
    def _target_reached() -> bool:
        return Game._current_progress() >= Settings.item_amount_to_farm

    @staticmethod
    def _calibrate_game_window(display_info_check: bool = False):
        """Recalibrate the dimensions of the bot window for fast and accurate image matching.

        Args:
            display_info_check (bool, optional): Displays the screen size and the dimensions of the bot window. Defaults to False.

        Returns:
            None
        """
        # Save the location of the "Home" button at the bottom of the bot window.
        Settings.home_button_location = ImageUtils.find_button("home", bypass_general_adjustment = True, tries = 1)

        MessageLog.print_message("\n[INFO] Recalibrating the dimensions of the window...")

        if Settings.home_button_location is None:
            raise RuntimeError("Calibration of window dimensions failed. Is the Home button on the bottom bar visible?")

        # Set the dimensions of the bot window and save it in ImageUtils so that future operations do not go out of bounds.
        home_back_button = ImageUtils.find_button("home_back")

        if home_back_button is None:
            raise RuntimeError("Calibration of window dimensions failed. Is the back button visible on the screen?")

        width, height = pyautogui.size()
        additional_calibration_required = Settings.static_window

        if Settings.static_window:
            MessageLog.print_message("[INFO] Using static window configuration...")
            if Settings.use_first_notch:
                window_left = max(0, home_back_button[0] - 80)
                window_width = (Settings.home_button_location[0] - window_left) + 50
            else:
                window_left = max(0, home_back_button[0] - 100)
                # Granblue Fantasy canvas width is ~480px plus side menu and bottom navigation bar.
                # Ensure window encompasses the full width from mobage side menu to the Home button.
                window_width = (Settings.home_button_location[0] - window_left) + 60
            window_top = 0  # The y-coordinate of the top edge.
            window_height = pyautogui.size()[1]  # The height of the region.
        else:
            MessageLog.print_message("[INFO] Using dynamic window configuration...")
            window_left: int = 0
            window_top: int = 0
            window_width: int = width
            window_height: int = height

        ImageUtils.update_window_dimensions(window_left, window_top, window_width, window_height, additional_calibration_required)

        MessageLog.print_message("[SUCCESS] Dimensions of the window has been successfully recalibrated.")

        if display_info_check:
            window_dimensions = ImageUtils.get_window_dimensions()
            MessageLog.print_message("\n**********************************************************************")
            MessageLog.print_message("**********************************************************************")
            MessageLog.print_message(f"[INFO] Screen Size: {pyautogui.size()}")
            MessageLog.print_message(f"[INFO] Game Window Dimensions: Region({window_dimensions[0]}, {window_dimensions[1]}, {window_dimensions[2]}, {window_dimensions[3]})")
            MessageLog.print_message("**********************************************************************")
            MessageLog.print_message("**********************************************************************")

        return None

    @staticmethod
    def go_back_home(confirm_location_check: bool = False, display_info_check: bool = False, test_mode: bool = False):
        """Go back to the Home screen to reset the position of the bot. Also able to recalibrate the region dimensions of the bot window if
        display_info_check is True.

        Args:
            confirm_location_check (bool, optional): Check to see if the current location is confirmed to be at the Home screen. Defaults to False.
            display_info_check (bool, optional): Recalibrate the bot window dimensions and displays the info. Defaults to False.
            test_mode (bool, optional): Flag to test and get a valid scale for device compatibility.

        Returns:
            None
        """
        if test_mode:
            MessageLog.print_message("\n[DEBUG] Now beginning test to find a valid scale for this device...")
            ImageUtils.find_button("home", test_mode = True)
            return

        if not ImageUtils.confirm_location("home", bypass_general_adjustment = True):
            MessageLog.print_message("\n[INFO] Moving back to the Home screen...")

            if Game.find_and_click_button("home", bypass_general_adjustment = True) is False:
                raise Exception(
                    "HOME button is not found. Stopping bot to prevent cascade of errors. Please readjust your confidences/scales. Maybe the Home button located on the bottom bar is not visible?")

            # Handle any misc popups on the Home screen.
            Game.find_and_click_button("close", suppress_error = True)

            if confirm_location_check:
                Game.wait(3.5)

                if ImageUtils.confirm_location("home", bypass_general_adjustment = True) is False:
                    Game.find_and_click_button("reload")
                    Game.wait(5.0)
                    if ImageUtils.confirm_location("home", bypass_general_adjustment = True) is False:
                        raise Exception("Failed to head back to the Home screen after clicking on the Home button.")
        else:
            MessageLog.print_message("[INFO] Bot is at the Home screen.")

        # Recalibrate the dimensions of the bot window.
        if display_info_check:
            Game._calibrate_game_window(display_info_check = True)

        return None

    @staticmethod
    def wait(seconds: float = 3.0):
        """Wait the specified seconds to account for ping or loading.

        Args:
            seconds (float, optional): Number of seconds for the execution to wait for. Defaults to 3.0.

        Returns:
            None
        """
        if Settings.reduce_delay_seconds > 0.0:
            if seconds - Settings.reduce_delay_seconds < 0.0:
                time.sleep(seconds)
            else:
                time.sleep(seconds - Settings.reduce_delay_seconds)
        else:
            time.sleep(seconds)
        return None

    @staticmethod
    def find_and_click_button(button_name: str, clicks: int = 1, tries: int = 0, x_offset: int = 0, y_offset: int = 0, custom_confidence: float = 0.80, suppress_error: bool = False,
                              bypass_general_adjustment: bool = True, custom_wait: Optional[float] = None):
        """Find the center point of a button image and click it.

        Args:
            button_name (str): Name of the button image file in the /images/buttons/ folder.
            clicks (int, optional): Number of mouse clicks when clicking the button image location. Defaults to 1.
            tries (int, optional): Number of tries to attempt to find the specified button image. Defaults to 0 which will use ImageUtil's default.
            x_offset (int, optional): Offset the x-coordinate of the click location. Defaults to 0.
            y_offset (int, optional): Offset the y-coordinate of the click location. Defaults to 0.
            custom_confidence (float, optional): Use a custom confidence for the template matching. Defaults to 0.80.
            suppress_error (bool, optional): Suppresses template matching error depending on boolean. Defaults to False.
            bypass_general_adjustment (bool, optional): Bypass using the general adjustment for the number of tries if ImageUtil's default is not being used. Defaults to True.
            custom_wait (float, optional): custom wait time after the click

        Returns:
            (bool): Return True if the button was found and clicked. Otherwise, return False.
        """
        if Settings.debug_mode:
            MessageLog.print_message(f"\n[DEBUG] Attempting to find and click the button: \"{button_name}\".")

        # --- Ultra-Fast DOM Click via Chrome DevTools Protocol ---
        if Settings.enable_dom_clicking and clicks == 1 and x_offset == 0 and y_offset == 0:
            from bot.dom_clicker import DomClicker
            if DomClicker.has_selector(button_name):
                attempts = max(1, tries)
                for i in range(attempts):
                    if DomClicker.click_button(button_name):
                        if custom_wait is not None:
                            time.sleep(custom_wait)
                        else:
                            delay = max(0.02, Settings.dom_click_delay)
                            time.sleep(random.uniform(delay * 0.8, delay * 1.2))
                        return True
                    if attempts > 1 and i < attempts - 1:
                        time.sleep(0.25)

        if tries == 0:
            if button_name.lower() == "quest":
                temp_location = ImageUtils.find_button("quest_blue", custom_confidence = custom_confidence)
                if temp_location is None:
                    temp_location = ImageUtils.find_button("quest_red", custom_confidence = custom_confidence)
                if temp_location is None and custom_confidence > 0.70:
                    temp_location = ImageUtils.find_button("quest_blue", custom_confidence = 0.70)
                    if temp_location is None:
                        temp_location = ImageUtils.find_button("quest_red", custom_confidence = 0.70)

                if temp_location is not None:
                    MouseUtils.move_and_click_point(temp_location[0] + x_offset, temp_location[1] + y_offset, "quest_blue", mouse_clicks = clicks)
                    return True
            elif button_name.lower() == "raid":
                temp_location = ImageUtils.find_button("raid_flat", custom_confidence = custom_confidence)
                if temp_location is None:
                    temp_location = ImageUtils.find_button("raid_bouncing", custom_confidence = custom_confidence)

                if temp_location is not None:
                    MouseUtils.move_and_click_point(temp_location[0] + x_offset, temp_location[1] + y_offset, "raid_flat", mouse_clicks = clicks)
                    return True
            elif button_name.lower() == "coop_start":
                temp_location = ImageUtils.find_button("coop_start_flat", custom_confidence = custom_confidence)
                if temp_location is None:
                    temp_location = ImageUtils.find_button("coop_start_faded", custom_confidence = custom_confidence)

                if temp_location is not None:
                    MouseUtils.move_and_click_point(temp_location[0] + x_offset, temp_location[1] + y_offset, "coop_start_flat", mouse_clicks = clicks)
                    return True
            elif button_name.lower() == "event_special_quest":
                temp_location = ImageUtils.find_button("event_special_quest", custom_confidence = custom_confidence)
                if temp_location is None:
                    temp_location = ImageUtils.find_button("event_special_quest_flat", custom_confidence = custom_confidence)
                if temp_location is None:
                    temp_location = ImageUtils.find_button("event_special_quest_bouncing", custom_confidence = custom_confidence)

                if temp_location is not None:
                    MouseUtils.move_and_click_point(temp_location[0] + x_offset, temp_location[1] + y_offset, "event_special_quest", mouse_clicks = clicks)
                    return True
            elif button_name.lower() == "play_again" and Settings.enable_defender and Settings.engaged_defender_battle and Settings.number_of_defeated_defenders >= Settings.number_of_defenders:
                    return False
            elif button_name.lower() == "play_again":
                return Game.find_and_click_play_again()
            else:
                temp_location = ImageUtils.find_button(button_name.lower(), custom_confidence = custom_confidence)
                if temp_location is not None:
                    MouseUtils.move_and_click_point(temp_location[0] + x_offset, temp_location[1] + y_offset, button_name, mouse_clicks = clicks)
                    return True
        else:
            if button_name.lower() == "quest":
                temp_location = ImageUtils.find_button("quest_blue", tries = tries, custom_confidence = custom_confidence, bypass_general_adjustment = bypass_general_adjustment)
                if temp_location is None:
                    temp_location = ImageUtils.find_button("quest_red", tries = tries, custom_confidence = custom_confidence, bypass_general_adjustment = bypass_general_adjustment)
                if temp_location is None and custom_confidence > 0.70:
                    temp_location = ImageUtils.find_button("quest_blue", tries = tries, custom_confidence = 0.70, bypass_general_adjustment = bypass_general_adjustment)
                    if temp_location is None:
                        temp_location = ImageUtils.find_button("quest_red", tries = tries, custom_confidence = 0.70, bypass_general_adjustment = bypass_general_adjustment)

                if temp_location is not None:
                    MouseUtils.move_and_click_point(temp_location[0] + x_offset, temp_location[1] + y_offset, "quest_blue", mouse_clicks = clicks)
                    return True
            elif button_name.lower() == "raid":
                temp_location = ImageUtils.find_button("raid_flat", tries = tries, custom_confidence = custom_confidence, bypass_general_adjustment = bypass_general_adjustment)
                if temp_location is None:
                    temp_location = ImageUtils.find_button("raid_bouncing", tries = tries, custom_confidence = custom_confidence, bypass_general_adjustment = bypass_general_adjustment)

                if temp_location is not None:
                    MouseUtils.move_and_click_point(temp_location[0] + x_offset, temp_location[1] + y_offset, "raid_flat", mouse_clicks = clicks)
                    return True
            elif button_name.lower() == "coop_start":
                temp_location = ImageUtils.find_button("coop_start_flat", tries = tries, custom_confidence = custom_confidence, bypass_general_adjustment = bypass_general_adjustment)
                if temp_location is None:
                    temp_location = ImageUtils.find_button("coop_start_faded", tries = tries, custom_confidence = custom_confidence, bypass_general_adjustment = bypass_general_adjustment)

                if temp_location is not None:
                    MouseUtils.move_and_click_point(temp_location[0] + x_offset, temp_location[1] + y_offset, "coop_start_flat", mouse_clicks = clicks)
                    return True
            elif button_name.lower() == "event_special_quest":
                temp_location = ImageUtils.find_button("event_special_quest", tries = tries, custom_confidence = custom_confidence, bypass_general_adjustment = bypass_general_adjustment)
                if temp_location is None:
                    temp_location = ImageUtils.find_button("event_special_quest_flat", tries = tries, custom_confidence = custom_confidence, bypass_general_adjustment = bypass_general_adjustment)
                if temp_location is None:
                    temp_location = ImageUtils.find_button("event_special_quest_bouncing", tries = tries, custom_confidence = custom_confidence, bypass_general_adjustment = bypass_general_adjustment)

                if temp_location is not None:
                    MouseUtils.move_and_click_point(temp_location[0] + x_offset, temp_location[1] + y_offset, "event_special_quest", mouse_clicks = clicks)
                    return True
            elif button_name.lower() == "play_again" and Settings.enable_defender and Settings.engaged_defender_battle and Settings.number_of_defeated_defenders >= Settings.number_of_defenders:
                    return False
            elif button_name.lower() == "play_again":
                return Game.find_and_click_play_again()
            else:
                temp_location = ImageUtils.find_button(button_name.lower(), tries = tries, suppress_error = suppress_error, custom_confidence = custom_confidence,
                                                       bypass_general_adjustment = bypass_general_adjustment)
                if temp_location is not None:
                    MouseUtils.move_and_click_point(temp_location[0] + x_offset, temp_location[1] + y_offset, button_name, mouse_clicks = clicks, custom_wait=custom_wait)
                    return True

        return False

    @staticmethod
    def find_and_click_play_again() -> bool:
        """Locate and click the 'Play Again' button on the Quest Result screen.

        Strategy:
          1. DOM trigger: invoke GBF's internal Game.view.onTapRetryQuest directly to ensure
             Backbone router navigation starts reliably.
          2. Physical mouse click at DOM getBoundingClientRect() coordinates.
          3. Fallback to fixed-ratio coordinate click if DOM lookup fails.

        Returns:
            (bool): True if the button was found and clicked, False otherwise.
        """
        MessageLog.print_message("[INFO] Attempting to find and click Play Again button...")

        # --- Step 0: Ensure we are actually on a result page before attempting Play Again ---
        is_on_result = Game.evaluate_dom_js("""
            (() => {
                let hash = window.location.hash || '';
                let again = document.querySelector('.btn-again, .btn-retry');
                let backupRequests = document.querySelector('.btn-control[data-buton-name="Backup Requests"]');
                return Boolean(hash.includes('result') || (again && again.offsetParent !== null) || (backupRequests && backupRequests.offsetParent !== null));
            })()
        """)
        if not is_on_result:
            MessageLog.print_message("[INFO] Not on Quest Results screen. Skipping Play Again.")
            return False

        # If on multi-raid results screen (#result_multi) where no standard Play Again button exists,
        # return False immediately to let the caller perform normal re-host navigation.
        is_multi_no_again = Game.evaluate_dom_js("""
            (() => {
                let hash = window.location.hash || '';
                if (hash.includes('result_multi')) {
                    let again = document.querySelector('.btn-again, .btn-retry');
                    let byData = document.querySelector('[data-buton-name="Play Again"]');
                    let hasAgain = (again && again.offsetParent !== null) || (byData && byData.offsetParent !== null);
                    return !hasAgain;
                }
                return false;
            })()
        """)
        if is_multi_no_again:
            MessageLog.print_message("[INFO] Multi-Raid results screen (#result_multi) detected with no Play Again button. Delegating to re-host navigation.")
            return False

        # --- Step 1: Direct DOM trigger if available ---
        dom_triggered = Game.evaluate_dom_js("""
            (() => {
                let el = document.querySelector('.btn-again, .btn-retry');
                if (!el || el.offsetParent === null) {
                    let byData = document.querySelector('[data-buton-name="Play Again"]');
                    if (byData && byData.offsetParent !== null) el = byData;
                }
                if (el && window.Game && window.Game.view && typeof window.Game.view.onTapRetryQuest === 'function') {
                    try {
                        window.Game.view.onTapRetryQuest({ currentTarget: el, target: el, x: 100, y: 100 });
                        return true;
                    } catch(e) {}
                }
                return false;
            })()
        """)
        if dom_triggered:
            MessageLog.print_message("[INFO] Triggered Play Again via GBF internal event handler. Waiting for screen transition...")
            if Game._wait_for_navigation_after_play_again(timeout = 6.0):
                return True
            else:
                MessageLog.print_message("[INFO] Internal event handler triggered, but navigation away from result page did not complete. Falling back to click.")

        # --- Step 2: Get button center from DOM getBoundingClientRect() and physically click ---
        rect_json = Game.evaluate_dom_js("""
            (() => {
                let el = document.querySelector('.btn-again, .btn-retry');

                if (!el || el.offsetParent === null) {
                    let byData = document.querySelector('[data-buton-name="Play Again"]');
                    if (byData && byData.offsetParent !== null) el = byData;
                }

                if (!el || el.offsetParent === null) {
                    for (let c of document.querySelectorAll('div, a, button')) {
                        let txt = (c.innerText || c.textContent || '').trim();
                        if ((txt === 'Play Again' || txt === '\\u518d\\u6311\\u6226') && c.offsetParent !== null) {
                            el = c;
                            break;
                        }
                    }
                }

                if (el && el.offsetParent !== null) {
                    let r = el.getBoundingClientRect();
                    return JSON.stringify({
                        cx: r.left + r.width / 2,
                        cy: r.top + r.height / 2
                    });
                }
                return null;
            })()
        """)

        clicked = False
        if rect_json and Settings.window_left is not None and Settings.window_top is not None:
            try:
                import json as _json
                pt = _json.loads(rect_json)
                screen_x = Settings.window_left + int(pt["cx"])
                screen_y = Settings.window_top + int(pt["cy"])
                MessageLog.print_message(f"[INFO] Play Again DOM rect found. Clicking at screen ({screen_x}, {screen_y}).")
                MouseUtils.move_and_click_point(screen_x, screen_y, "play_again")
                if Game._wait_for_navigation_after_play_again(timeout = 6.0):
                    clicked = True
            except Exception as ex:
                MessageLog.print_message(f"[WARNING] Play Again DOM rect parse failed: {ex}")

        if not clicked:
            play_again_location = ImageUtils.find_button("playagain", tries=1, suppress_error=True)
            if play_again_location is None:
                play_again_location = ImageUtils.find_button("play_again", tries=1, suppress_error=True)
            if play_again_location is not None:
                MouseUtils.move_and_click_point(play_again_location[0], play_again_location[1], "playagain")
                if Game._wait_for_navigation_after_play_again(timeout = 6.0):
                    clicked = True

        if not clicked:
            # Step 3: Ratio-based physical fallback using fixed screen coordinates only on single-quest #result
            if (Settings.window_left is not None and Settings.window_top is not None
                    and Settings.window_width is not None and Settings.window_height is not None):
                current_hash = Game.evaluate_dom_js("window.location.hash || ''") or ''
                if 'result' in current_hash and not ('result_multi' in current_hash):
                    screen_x = Settings.window_left + int(Settings.window_width * 0.5)
                    screen_y = Settings.window_top + int(Settings.window_height * 0.88)
                    MessageLog.print_message(f"[INFO] Play Again not found via DOM/image. Trying ratio-based click at ({screen_x}, {screen_y}).")
                    MouseUtils.move_and_click_point(screen_x, screen_y, "play_again_fallback")
                    if Game._wait_for_navigation_after_play_again(timeout = 5.0):
                        clicked = True
                else:
                    MessageLog.print_message("[INFO] Not currently on single-quest #result URL. Skipping blind ratio click.")

        MessageLog.print_message(f"[INFO] find_and_click_play_again result: {clicked}")
        return clicked

    @staticmethod
    def _wait_for_navigation_after_play_again(timeout: float = 15.0) -> bool:
        """Wait until the game navigates away from the result screen after clicking Play Again.

        Args:
            timeout (float): Seconds to wait before giving up. Defaults to 15.0.

        Returns:
            (bool): True if navigated away from result page, False if timed out.
        """
        import time
        start_time = time.time()
        MessageLog.print_message("[INFO] Waiting for navigation to Summon / Party screen...")

        while time.time() - start_time < timeout:
            # 1. Check if arrived at supporter, stage, or party screen
            nav_status = Game.evaluate_dom_js("""(() => {
                let hash = window.location.hash || '';
                if (hash.includes('supporter') || hash.includes('stage') || hash.includes('raid') || hash.includes('party')) {
                    return 'arrived';
                }
                if (!hash.includes('result')) {
                    return 'navigated';
                }
                return null;
            })()""")
            if nav_status:
                MessageLog.print_message(f"[INFO] Successfully navigated away from result page ({nav_status}).")
                return True

            # 2. Check for Friend Request popup (crucial when using non-friend support summon)
            dismissed_friend = Game.evaluate_dom_js("""(() => {
                let friendPop = document.querySelector('.pop-friend-request');
                if (friendPop && friendPop.offsetParent !== null) {
                    if (window.Game && window.Game.view && typeof window.Game.view.popRemoveOnly === 'function') {
                        window.Game.view.popRemoveOnly();
                        return 'popRemoveOnly';
                    }
                    let cancel = friendPop.querySelector('.btn-usual-cancel, .btn-cancel');
                    if (cancel) {
                        let activated = false;
                        if (window.$ && typeof window.$(cancel).trigger === 'function') {
                            try { window.$(cancel).trigger('tap'); activated = true; } catch(e) {}
                        }
                        if (!activated) cancel.click();
                        return 'btn-usual-cancel';
                    }
                }
                return null;
            })()""")
            if dismissed_friend:
                MessageLog.print_message(f"[INFO] Dismissed Friend Request popup via DOM ({dismissed_friend}).")
                Game.wait(1.5)
                continue

            # 3. Check for any other modal popups (Missions, Skyscope, Hell appearance, host dialog, etc.)
            dismissed_modal = Game.evaluate_dom_js("""(() => {
                let pop = document.querySelector('.pop-usual, .pop-show, [class*="pop-"]');
                if (pop && pop.offsetParent !== null) {
                    let sel = ['.btn-usual-ok', '.btn-usual-close', '.btn-close-hell', '.btn-close', '.btn-usual-cancel'];
                    for (let s of sel) {
                        let btn = pop.querySelector(s);
                        if (btn && btn.offsetParent !== null) {
                            let activated = false;
                            if (window.$ && typeof window.$(btn).trigger === 'function') {
                                try { window.$(btn).trigger('tap'); activated = true; } catch(e) {}
                            }
                            if (!activated) btn.click();
                            return s;
                        }
                    }
                }
                return null;
            })()""")
            if dismissed_modal:
                MessageLog.print_message(f"[INFO] Dismissed modal popup via DOM ({dismissed_modal}).")
                Game.wait(1.5)
                continue

            # Fallback to image-based cancel/close
            if Game.find_and_click_button("cancel", tries = 1, suppress_error = True):
                MessageLog.print_message("[INFO] Dismissed Cancel popup via image match.")
                Game.wait(1.5)
                continue

            if Game.find_and_click_button("close", tries = 1, suppress_error = True):
                MessageLog.print_message("[INFO] Dismissed Close popup via image match.")
                Game.wait(1.5)
                continue

            # 4. If Play Again is still visible after 3 seconds, re-trigger Play Again
            if time.time() - start_time > 3.0:
                retriggered = Game.evaluate_dom_js("""(() => {
                    let el = document.querySelector('.btn-retry, .btn-again');
                    if (!el) {
                        el = document.querySelector('[data-buton-name="Play Again"]');
                    }
                    if (el && el.offsetParent !== null && window.Game && window.Game.view && typeof window.Game.view.onTapRetryQuest === 'function') {
                        try {
                            window.Game.view.onTapRetryQuest({ currentTarget: el, target: el, x: 100, y: 100 });
                            return true;
                        } catch(e) {}
                    }
                    return false;
                })()""")
                if retriggered:
                    MessageLog.print_message("[INFO] Re-triggered Play Again via GBF internal handler.")

            Game.wait(1.0)

        return False

    @staticmethod
    def check_for_captcha():
        """Checks for CAPTCHA right after selecting a Summon and if detected, alert the user and then stop the bot.

        Returns:
            None
        """
        try:
            if ImageUtils.confirm_location("captcha", bypass_general_adjustment = True):
                raise RuntimeError("CAPTCHA DETECTED!")
            else:
                MessageLog.print_message("\n[CAPTCHA] CAPTCHA not detected.")

            return None
        except RuntimeError:
            Game._discord_queue.put(f"> Bot encountered exception while checking for CAPTCHA: \n{traceback.format_exc()}")
            MessageLog.print_message(f"\n[ERROR] Bot encountered exception while checking for CAPTCHA: \n{traceback.format_exc()}")
            ImageUtils.generate_alert_for_captcha()

    @staticmethod
    def _delay_between_runs():
        """Execute a delay after every run completed based on user settings.

        Returns:
            None
        """
        # Delay between runs is disabled.
        return None

    @staticmethod
    def _move_mouse_security_check():
        """Moves the mouse off the game window and stay like that for a bit to attempt circumvention of possible bot detection. This is PC specific, not possible for the Android version.

        Returns:
            None
        """
        # Mouse security check is disabled.
        return None

    @staticmethod
    def select_summon(summon_list: List[str], summon_element_list: List[str]):
        """Select a configured support summon or explicitly keep the current selection.

        Args:
            summon_list (List[str]): Unused. Kept for backwards compatibility with callers.
            summon_element_list (List[str]): Unused. Kept for backwards compatibility with callers.

        Returns:
            (bool): True when selection can proceed.
        """
        if Settings.summon_selection_mode == "current":
            MessageLog.print_message(
                "\n[INFO] Support Summon mode is 'current'; keeping the selection already active in-game."
            )
            return True

        if Settings.summon_selection_mode != "configured":
            raise ValueError(
                f"Unsupported summonSelectionMode: {Settings.summon_selection_mode}. "
                "Use 'current' or 'configured'."
            )

        if not summon_list or not summon_element_list or len(summon_list) != len(summon_element_list):
            raise ValueError("Configured summon selection requires equally sized summons and summonElements lists.")

        summon_location = ImageUtils.find_summon(summon_list, summon_element_list)
        if summon_location is None:
            MessageLog.print_message("[WARNING] None of the configured support summons could be selected.")
            return False

        MouseUtils.move_and_click_point(summon_location[0], summon_location[1], "configured_support_summon")
        Game.wait(1.0)
        return True

    @staticmethod
    def _reset_summons():
        """Reset the Summons available by starting and then retreating from a Old Lignoid Trial Battle.

        Returns:
            None
        """
        MessageLog.print_message("\n[INFO] Now refreshing Summons...")
        Game.go_back_home(confirm_location_check = True)

        # Scroll down the screen to see the "Gameplay Extra" button on smaller screen sizes.
        MouseUtils.scroll_screen_from_home_button(-600)

        if Game.find_and_click_button("gameplay_extras"):
            # If the bot cannot find the "Trial Battles" button, keep scrolling down until it does. It should not take more than 2 loops to see it for any reasonable screen size.
            while Game.find_and_click_button("trial_battles") is False:
                MouseUtils.scroll_screen_from_home_button(-300)

            if ImageUtils.confirm_location("trial_battles"):
                # Click on the "Old Lignoid" button.
                Game.find_and_click_button("trial_battles_old_lignoid")

                # Select any detected "Play" button.
                Game.find_and_click_button("play_round_button")

                # Now select the first Summon.
                choose_a_summon_location = ImageUtils.find_button("choose_a_summon")
                MouseUtils.move_and_click_point(choose_a_summon_location[0], choose_a_summon_location[1] + 187, "choose_a_summon")

                # Now start the Old Lignoid Trial Battle right away and then wait a few seconds.
                Game.find_and_click_button("party_selection_ok")
                Game.wait(3.0)

                # Retreat from this Trial Battle.
                Game.find_and_click_button("menu", tries = 30)
                Game.find_and_click_button("retreat", tries = 30)
                Game.find_and_click_button("retreat_confirmation", tries = 30)
                Game.go_back_home()

                if ImageUtils.confirm_location("home"):
                    MessageLog.print_message("[SUCCESS] Summons have now been refreshed.")
        else:
            MessageLog.print_message("[WARNING] Failed to reset Summons as the 'Gameplay Extras' button is not visible.")

        return None

    @staticmethod
    def evaluate_dom_js(js: str) -> any:
        """Execute arbitrary JavaScript inside the Granblue Fantasy tab via Chrome DevTools Protocol (CDP).

        Args:
            js (str): The JavaScript expression or IIFE to evaluate.

        Returns:
            The 'value' of the evaluated JavaScript expression, or None on failure.
        """
        try:
            import urllib.request, json, socket, struct, base64

            ws_url = Game._cached_ws_url
            if not ws_url:
                # Discover the GBF tab's WebSocket URL.
                try:
                    req = urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=1.0)
                    tabs = json.loads(req.read())
                    ws_url = next(
                        (t['webSocketDebuggerUrl'] for t in tabs
                         if t.get('type') == 'page' and t.get('url', '').startswith('https://game.granbluefantasy.jp')),
                        None
                    )
                    if not ws_url:
                        # Fallback to any tab containing 'granbluefantasy'
                        ws_url = next(
                            (t['webSocketDebuggerUrl'] for t in tabs
                             if 'granbluefantasy' in t.get('url', '')),
                            None
                        )
                    Game._cached_ws_url = ws_url
                except Exception:
                    Game._cached_ws_url = None
                    return None

            if not ws_url:
                return None

            ws_url_stripped = ws_url.replace('ws://', '')
            host_port, path = ws_url_stripped.split('/', 1)
            path = '/' + path
            host, port_str = host_port.split(':')
            port = int(port_str)

            sock = socket.create_connection((host, port), timeout=3.0)

            # WebSocket upgrade handshake
            nonce = base64.b64encode(b'GranblueBot12==').decode()
            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {nonce}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            sock.sendall(handshake.encode())

            resp = b''
            while b'\r\n\r\n' not in resp:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
            if b'101' not in resp:
                sock.close()
                Game._cached_ws_url = None
                return None

            def _ws_send(payload: str):
                data = payload.encode('utf-8')
                length = len(data)
                mask_key = bytes([0xDE, 0xAD, 0xBE, 0xEF])
                masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))
                if length <= 125:
                    header = bytes([0x81, 0x80 | length]) + mask_key
                elif length <= 65535:
                    header = bytes([0x81, 0xFE]) + struct.pack('>H', length) + mask_key
                else:
                    header = bytes([0x81, 0xFF]) + struct.pack('>Q', length) + mask_key
                sock.sendall(header + masked)

            def _ws_recv() -> str:
                def _recv_exact(size: int) -> bytes:
                    data = b''
                    while len(data) < size:
                        chunk = sock.recv(size - len(data))
                        if not chunk:
                            raise ConnectionError("Chrome DevTools websocket closed mid-frame")
                        data += chunk
                    return data

                header = _recv_exact(2)
                payload_len = header[1] & 0x7F
                if payload_len == 126:
                    ext = _recv_exact(2)
                    payload_len = struct.unpack('>H', ext)[0]
                elif payload_len == 127:
                    ext = _recv_exact(8)
                    payload_len = struct.unpack('>Q', ext)[0]
                data = _recv_exact(payload_len)
                return data.decode('utf-8', errors='replace')

            request_id = 8888
            msg = json.dumps({'id': request_id, 'method': 'Runtime.evaluate',
                              'params': {'expression': js, 'returnByValue': True}})
            _ws_send(msg)
            # DevTools may emit asynchronous events before the Runtime.evaluate response.
            # Ignore those frames and wait for our request id instead of returning a false None.
            for _ in range(50):
                result = json.loads(_ws_recv())
                if result.get('id') == request_id:
                    sock.close()
                    return result.get('result', {}).get('result', {}).get('value', None)
            sock.close()
            raise TimeoutError("Chrome DevTools did not return the Runtime.evaluate response")

        except Exception as ex:
            Game._cached_ws_url = None
            if Settings.debug_mode:
                MessageLog.print_message(f"[DEBUG] evaluate_dom_js error: {ex}")
            return None

    @staticmethod
    def _try_dom_click_ok() -> str:
        """Attempt to scroll to and click the OK/Start button on the party-selection
        screen via Chrome DevTools Protocol (CDP) using stdlib websocket.

        Returns:
            str: ``clicked``, ``ended`` when the ended-raid popup owns the visible OK,
                or ``not_found`` when no safe start button could be activated.
        """
        js = r"""(() => {
            var selectors = [
                '.btn-usual-ok.se-quest-start',
                '.btn-usual-ok',
                'input[value="OK"]',
                'button.btn-ok'
            ];
            // If any visible ended-raid popup is present, do not click its generic OK button as
            // though it were the party Start button. Preserve it for check_for_ended_raid().
            const possibleEndedPopups = document.querySelectorAll(
                '.pop-result-assist-raid, .pop-usual, .prt-popup-body, .prt-popup, [class*="popup"]'
            );
            for (const popup of possibleEndedPopups) {
                if (!popup || popup.offsetParent === null || window.getComputedStyle(popup).display === 'none') continue;
                const text = (popup.innerText || popup.textContent || '').toLowerCase();
                if (text.includes('already ended') ||
                    text.includes('raid battle has already') ||
                    text.includes('終了')) return 'ended';
            }

            var ok = null;
            for (var s of selectors) {
                ok = document.querySelector(s);
                if (ok && ok.offsetParent !== null) break;
                ok = null;
            }
            if (!ok) {
                window.scrollTo(0, document.body.scrollHeight);
                return 'not_found';
            }
            ok.scrollIntoView({block: 'center', behavior: 'instant'});
            let activated = false;
            if (window.$ && typeof window.$(ok).trigger === 'function') {
                try {
                    window.$(ok).trigger('tap');
                    activated = true;
                } catch (_) {}
            }
            if (!activated) ok.click();
            return 'clicked';
        })()"""
        result = Game.evaluate_dom_js(js)
        if result == "clicked":
            MessageLog.print_message("[INFO] Clicked OK button via DOM (Chrome DevTools).")
            return "clicked"
        if result == "ended":
            return "ended"
        return "not_found"

    @staticmethod
    def check_and_tap_ready() -> bool:
        """Checks for the READY to battle screen ("Tap the screen to enable/disable auto attack")
        and taps it through CDP without moving or clicking the physical cursor.

        Returns:
            (bool): True if READY was detected and tapped, False otherwise.
        """
        try:
            dom_res = Game.evaluate_dom_js("""(() => {
                let hash = window.location.hash || '';
                // Must be on a battle URL (raid or quest stage), not still on supporter/party selection
                if (!hash.includes('raid') && !hash.includes('stage')) {
                    return { ready: false, in_battle: false };
                }

                function isVisible(el) {
                    if (!el) return false;
                    if (el.offsetParent === null) return false;
                    let s = window.getComputedStyle(el);
                    return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
                }

                let btn = document.querySelector('.btn-ready-auto');
                let prtAuto = document.querySelector('.prt-auto-setting');
                let prtReady = document.querySelector('.prt-ready');
                let txtAuto = document.querySelector('.txt-auto-setting');
                let readyDiv = document.querySelector('#ready');

                let isReady = Boolean(
                    (readyDiv && isVisible(readyDiv)) ||
                    (btn && isVisible(btn)) ||
                    (prtAuto && isVisible(prtAuto)) ||
                    (prtReady && isVisible(prtReady)) ||
                    (txtAuto && isVisible(txtAuto))
                );

                if (isReady) {
                    let target = [btn, prtReady, readyDiv, prtAuto, txtAuto].find(isVisible) || null;
                    if (!target) {
                        let center = document.elementFromPoint(window.innerWidth / 2, window.innerHeight * 0.45);
                        if (center && isVisible(center)) target = center;
                    }
                    if (target) {
                        let activated = false;
                        if (window.$ && typeof window.$(target).trigger === 'function') {
                            try {
                                window.$(target).trigger('tap');
                                activated = true;
                            } catch(e) {}
                        }
                        if (!activated) target.click();
                        return { ready: true, in_battle: true, tapped: true };
                    }
                    return { ready: true, in_battle: true, tapped: false };
                }
                return { ready: false, in_battle: true, tapped: false };
            })()""")
            if dom_res and isinstance(dom_res, dict):
                if dom_res.get('tapped', False):
                    MessageLog.print_message("[INFO] Tapped READY screen via DOM.")
                    return True
                if dom_res.get('ready', False):
                    MessageLog.print_message(
                        "[WARNING] READY screen was detected, but no DOM target could be activated. "
                        "No physical cursor click was attempted."
                    )
        except Exception:
            pass

        return False

    @staticmethod
    def find_party_and_start_mission(group_number: int, party_number: int, tries: int = 30, bypass_first_run: bool = False):
        """Select the specified Group and Party. It will then start the mission.

        Args:
            group_number (int): The Group that the specified Party is in.
            party_number (int): The specified Party to start the mission with.
            tries (int, optional): Number of tries to select a Set before failing. Defaults to 30.
            bypass_first_run (bool, optional): Determines if the bot should reselect the party in subsequent runs. Defaults to False.

        Returns:
            (bool): Returns False if it detects the "Raid is full/Raid is already done" dialog. Otherwise, return True.
        """
        Game._last_party_start_status = "starting"

        use_current_party = (
            Settings.party_selection_mode == "current" or
            Settings.no_party_selection or
            group_number <= 0 or
            party_number <= 0
        )
        if Settings.party_selection_mode not in ("current", "configured"):
            raise ValueError(
                f"Unsupported partySelectionMode: {Settings.party_selection_mode}. "
                "Use 'current' or 'configured'."
            )

        if use_current_party:
            MessageLog.print_message("\n[INFO] Party mode is 'current'; using the party already active in-game.")
            Settings.party_selection_first_run = False
        elif Settings.party_selection_first_run or bypass_first_run:
            MessageLog.print_message(f"\n[INFO] Starting process to select Group {group_number}, Party {party_number}...")

            # Find the Group that the Party is in first. If the specified Group number is less than 8, it is in Set A. Otherwise, it is in Set B. If failed, alternate searching for Set A / Set B until
            # found or tries are depleted.
            set_location = None
            if Settings.farming_mode == "Arcarum Sandbox":
                while set_location is None:
                    set_location = ImageUtils.find_button("party_set_extra", tries = 10)
                    if set_location is None:
                        tries -= 1
                        if tries <= 0:
                            raise RuntimeError("Could not find Set Extra.")
            else:
                if Settings.farming_mode == "Raid" and ImageUtils.find_button("party_set_extra", tries = 3):
                    MessageLog.print_message(f"[INFO] Skipping Set Selection due to Raid only allowing parties from the Extra category.")
                elif group_number < 8:
                    while set_location is None:
                        set_location = ImageUtils.find_button("party_set_a", tries = 1)
                        if set_location is None:
                            tries -= 1
                            if tries <= 0:
                                # Save debug screenshot to help fix templates
                                import pyautogui, datetime
                                debug_path = f"party_selection_debug_{datetime.datetime.now().strftime('%H%M%S')}.png"
                                pyautogui.screenshot(debug_path)
                                MessageLog.print_message(f"[WARNING] Could not find Set A/B buttons after all tries. Saved debug screenshot to '{debug_path}'.")
                                MessageLog.print_message(f"[INFO] Falling back to clicking OK with current party selection...")
                                set_location = None
                                break

                            # See if the user had Set B active instead of Set A if matching failed.
                            Game.find_and_click_button("party_set_b", tries = 1, suppress_error = True)
                else:
                    while set_location is None:
                        set_location = ImageUtils.find_button("party_set_b", tries = 1)
                        if set_location is None:
                            tries -= 1
                            if tries <= 0:
                                # Save debug screenshot to help fix templates
                                import pyautogui, datetime
                                debug_path = f"party_selection_debug_{datetime.datetime.now().strftime('%H%M%S')}.png"
                                pyautogui.screenshot(debug_path)
                                MessageLog.print_message(f"[WARNING] Could not find Set A/B buttons after all tries. Saved debug screenshot to '{debug_path}'.")
                                MessageLog.print_message(f"[INFO] Falling back to clicking OK with current party selection...")
                                set_location = None
                                break

                            # See if the user had Set A active instead of Set B if matching failed.
                            Game.find_and_click_button("party_set_a", tries = 1, suppress_error = True)

            # Only perform group/party selection if we successfully found the Set button anchor.
            if set_location is not None:
                # Center the mouse on the "Set A" / "Set B" button and then click the correct Group tab.
                if Settings.debug_mode:
                    MessageLog.print_message(f"[DEBUG] Successfully selected the correct Set. Now selecting Group {group_number}...")

                # Determine coordinates for the group selection.
                # Group 1..7 (Set A) and 8..14 (Set B) are horizontally laid out at y=252.
                g_idx = (group_number - 1) % 7
                if Settings.use_first_notch:
                    x = Settings.window_left + int(53 + g_idx * 50)
                    y = set_location[1] + 40
                else:
                    x = Settings.window_left + int(80 + g_idx * 75)
                    y = set_location[1] + 55

                MouseUtils.move_and_click_point(x, y, "template_group", mouse_clicks = 2)

                # Now select the correct Party.
                if Settings.debug_mode:
                    MessageLog.print_message(f"[DEBUG] Successfully selected Group {group_number}. Now selecting Party {party_number}...")

                # Party 1..6 dots are horizontally laid out at y=529 below the deck preview.
                p_idx = (party_number - 1) % 6
                if Settings.use_first_notch:
                    x = Settings.window_left + int(57 + p_idx * 62)
                    y = set_location[1] + 280
                else:
                    x = Settings.window_left + int(86 + p_idx * 93.4)
                    y = set_location[1] + 435

                # Safety: never click within the EDIT button area (y between 395 and 465)
                if 395 <= y <= 465:
                    y = 530

                MouseUtils.move_and_click_point(x, y, "template_party", mouse_clicks = 2)

                MessageLog.print_message(f"[INFO] Successfully selected Group {group_number}, Party {party_number}. Now starting the mission.")

            Settings.party_selection_first_run = False
        else:
            MessageLog.print_message("\n[INFO] Reusing the same Party.")

        # Find and click the "OK" button to start the mission.
        # On the party selection screen, the OK/Start button is located below
        # the party deck preview and requires scrolling down to become visible.
        ok_clicked = False

        # An ended-raid popup also owns a generic OK button. Dismiss and classify it before any
        # DOM/image/coordinate start fallback can accidentally consume that signal.
        if Game.check_for_ended_raid():
            Game._last_party_start_status = "ended"
            MessageLog.print_message("\n[WARNING] Raid ended before the party Start button could be activated.")
            return False

        # 1. Try DOM click/scroll first if Chrome DevTools is connected
        dom_click_status = Game._try_dom_click_ok()
        if dom_click_status == "clicked":
            ok_clicked = True
        elif dom_click_status == "ended":
            Game.check_for_ended_raid()
            Game._last_party_start_status = "ended"
            MessageLog.print_message("\n[WARNING] Raid ended while the party Start button was being located.")
            return False
        else:
            # 2. Try visual template match with scrolling down
            for attempt in range(5):
                if Game.check_for_ended_raid():
                    Game._last_party_start_status = "ended"
                    MessageLog.print_message("\n[WARNING] Raid ended before the visual Start fallback could run.")
                    return False
                if Game.find_and_click_button("btn_ok", tries = 1, suppress_error = True, custom_confidence = 0.70):
                    ok_clicked = True
                    break
                if Game.find_and_click_button("ok", tries = 1, suppress_error = True, custom_confidence = 0.70):
                    ok_clicked = True
                    break
                if Game.find_and_click_button("party_selection_ok", tries = 1, suppress_error = True, custom_confidence = 0.70):
                    ok_clicked = True
                    break

                # Scroll down using center of game window reference
                if Settings.debug_mode:
                    MessageLog.print_message(f"[DEBUG] OK button not visible yet. Scrolling down to reveal it (attempt {attempt + 1}/5)...")
                MouseUtils.scroll_screen_from_home_button(-250)
                Game.wait(0.8)

            if not ok_clicked:
                if Game.check_for_ended_raid():
                    Game._last_party_start_status = "ended"
                    MessageLog.print_message("\n[WARNING] Raid ended before the coordinate Start fallback could run.")
                    return False
                # Absolute-coordinate last resort.
                # After all scroll attempts the OK button (right side of Cancel|OK pair)
                # is visible on the right half of the bottom action area.
                ok_x = (Settings.window_left or 0) + int((Settings.window_width or 632) * 0.67)
                ok_y = (Settings.window_top or 0) + 667
                MessageLog.print_message(f"[WARNING] All template-match attempts failed. Clicking OK at absolute coords ({ok_x}, {ok_y}) as last resort.")
                MouseUtils.move_and_click_point(ok_x, ok_y, "ok_absolute_fallback")
                ok_clicked = True

        # --- Auto Attack: tap READY screen sebelum cek "raids" yang lambat ---
        # READY screen ("Tap the screen to enable/disable auto attack") muncul
        # beberapa detik setelah OK diklik dan hanya bertahan 2-3 detik.
        # Kita poll di sini untuk men-tap layar begitu READY muncul.
        is_auto_attack_tap = (
            Settings.combat_script_name.lower() in ("full_auto.txt", "semi_auto_then_reload.txt", "semi_auto.txt")
            or any(cmd in c.lower() for c in Settings.combat_script for cmd in ("enablefullauto", "enablesemiauto", "enablesemiautoandreload", "enablesemiautoreload"))
            or Settings.farming_mode in ("Rise of the Beasts", "Raid")
        )
        # Reset from any previous run before (re-)evaluating this one.
        Settings.full_auto_pretapped = False
        Settings.auto_attack_pretapped = False
        if is_auto_attack_tap:
            MessageLog.print_message("[INFO] Polling for READY screen to tap immediately after entering raid battle...")
            ready_poll_tries = 40
            ready_tapped = False
            battle_started = False
            while ready_poll_tries > 0:
                if Game.check_for_ended_raid():
                    Game._last_party_start_status = "ended"
                    MessageLog.print_message("\n[WARNING] Raid ended during battle loading. Backing out to Home now...")
                    return False

                if Game.check_and_tap_ready():
                    ready_tapped = True
                    break

                # Check if battle has already started and READY phase has passed
                battle_started = False
                try:
                    att_check = Game.evaluate_dom_js("""(() => {
                        let att = document.querySelector('.btn-attack-start');
                        return Boolean(att && !att.classList.contains('display-off') && window.getComputedStyle(att).display !== 'none');
                    })()""")
                    if att_check:
                        battle_started = True
                except Exception:
                    pass

                if not battle_started and ready_poll_tries % 5 == 0:
                    if ImageUtils.find_button("attack", tries = 1, suppress_error = True) is not None:
                        battle_started = True

                if battle_started:
                    MessageLog.print_message("[INFO] Battle screen (Attack button) appeared; READY phase ended.")
                    break

                ready_poll_tries -= 1
                if ready_poll_tries > 0:
                    Game.wait(0.25)

            if ready_tapped:
                Settings.full_auto_pretapped = True
                Settings.auto_attack_pretapped = True
            elif battle_started:
                MessageLog.print_message("[INFO] READY screen not detected during pre-tap window. Will handle during combat mode.")
            else:
                in_battle_route = Game.evaluate_dom_js("""(() => {
                    const hash = window.location.hash || '';
                    return hash.startsWith('#raid') || hash.startsWith('#stage');
                })()""")
                if not in_battle_route:
                    Game._last_party_start_status = "not_started"
                    MessageLog.print_message(
                        "[WARNING] Party Start was clicked, but no READY screen, Attack button, "
                        "or battle route appeared. Recovering instead of starting Combat Mode on an unknown screen."
                    )
                    return False
                MessageLog.print_message("[INFO] Battle route loaded after the READY polling window.")

        # If a popup appears and says "This raid battle has already ended. The Home screen will now appear.", return False.
        if Game.check_for_ended_raid():
            Game._last_party_start_status = "ended"
            MessageLog.print_message("\n[WARNING] Raid ended before starting mission. Backing out to Home now...")
            return False
        elif Settings.farming_mode.lower() == "raid" and ImageUtils.confirm_location("raids"):
            Game._last_party_start_status = "ended"
            MessageLog.print_message("\n[WARNING] Raid unfortunately just ended. Backing out now...")
            Game.find_and_click_button("ok")
            Game.wait(3.0)
            return False

        Game.wait(3.0)
        Game._last_party_start_status = "started"
        return True

    @staticmethod
    def check_for_ap():
        """Check if the user has enabled the auto-restore option for AP.

        Returns:
            None
        """
        Game.wait(3)

        if ImageUtils.confirm_location("not_enough_ap", tries = 2):
            raise RuntimeError("AP auto-restore check failed. Please enable the auto-restore option in the in-game settings according to the GitHub instructions.")
        else:
            MessageLog.print_message("\n[INFO] AP auto-restore check passed. Continuing to Party Selection...")

        return None

    @staticmethod
    def check_for_ep():
        """Check if the user has enabled the auto-restore option for EP.

        Returns:
            None
        """
        Game.wait(3)

        if Settings.farming_mode.lower() == "raid" and ImageUtils.confirm_location("not_enough_ep", tries = 2):
            raise RuntimeError("EP auto-restore check failed. Please enable the auto-restore option in the in-game settings according to the GitHub instructions.")
        else:
            MessageLog.print_message("[INFO] EP auto-restore check passed. Continuing to Party Selection...")

        return None

    @staticmethod
    def dismiss_post_battle_progression(max_attempts: int = 3) -> bool:
        """Dismiss result overlays such as Extended Mastery without using the cursor.

        Result content can become visible before these overlays finish appearing. Callers may
        therefore invoke this both immediately after loot collection and before leaving a result
        route. DOM text/class detection is preferred; the existing image is detection-only and a
        CDP tap is dispatched at the visible overlay when its artwork contains no useful DOM text.
        """
        dismissed_any = False
        attempts = max(1, max_attempts)

        detect_and_dismiss_js = r"""(() => {
            const hash = window.location.hash || '';
            if (!hash.includes('result')) {
                return {detected: false, dismissed: false, route: hash};
            }

            function visible(el) {
                if (!el || !el.isConnected) return false;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' &&
                    Number(style.opacity) !== 0 && rect.width > 1 && rect.height > 1;
            }

            function activate(el) {
                if (!el) return false;
                if (window.$ && typeof window.$(el).trigger === 'function') {
                    try {
                        window.$(el).trigger('tap');
                        return true;
                    } catch (_) {}
                }
                try {
                    el.click();
                    return true;
                } catch (_) {
                    return false;
                }
            }

            const pattern = /extended\s+mastery|mastery\s+level|new\s+mastery|zenith\s+level/i;
            const classCandidates = [...document.querySelectorAll(
                '[class*="mastery"], [class*="zenith"], [class*="lb-level"], [class*="limit-bonus"]'
            )].filter(visible);
            const textCandidate = [...document.querySelectorAll('div,section,p,span')]
                .filter(visible)
                .find(el => pattern.test((el.innerText || el.textContent || '').replace(/\s+/g, ' ')) &&
                    el.closest('.pop-usual,.pop-show,[class*="popup"],[class*="mastery"],[class*="zenith"]'));
            let overlay = classCandidates[0] || textCandidate || null;
            if (!overlay) return {detected: false, dismissed: false, route: hash};

            overlay = overlay.closest(
                '.pop-usual,.pop-show,[class*="popup"],[class*="mastery"],[class*="zenith"]'
            ) || overlay;
            const control = [...overlay.querySelectorAll(
                '.btn-usual-ok,.btn-ok,.btn-usual-close,.btn-close,.btn-result-next,.btn-settlement-next'
            )].find(visible);
            const target = control || overlay;
            return {
                detected: true,
                dismissed: activate(target),
                via: control ? 'control' : 'overlay',
                cls: `${target.className || ''}`,
                route: hash
            };
        })()"""

        center_tap_js = r"""(() => {
            const hash = window.location.hash || '';
            if (!hash.includes('result')) return false;
            const points = [
                [window.innerWidth * 0.5, window.innerHeight * 0.45],
                [window.innerWidth * 0.5, window.innerHeight * 0.55]
            ];
            for (const [x, y] of points) {
                let target = document.elementFromPoint(x, y);
                if (!target) continue;
                target = target.closest(
                    '.pop-usual,.pop-show,[class*="popup"],[class*="mastery"],[class*="zenith"]'
                );
                if (!target) continue;
                if (window.$ && typeof window.$(target).trigger === 'function') {
                    try {
                        window.$(target).trigger('tap');
                        return true;
                    } catch (_) {}
                }
                try {
                    target.click();
                    return true;
                } catch (_) {}
            }
            return false;
        })()"""

        for _ in range(attempts):
            result = Game.evaluate_dom_js(detect_and_dismiss_js)
            if isinstance(result, dict) and result.get("detected") and result.get("dismissed"):
                dismissed_any = True
                MessageLog.print_message(
                    f"[INFO] Dismissed post-battle progression overlay via DOM "
                    f"({result.get('via', 'unknown')}: {result.get('cls', '')})."
                )
                Game.wait(1.0)
                continue

            if isinstance(result, dict) and "result" not in (result.get("route") or ""):
                break

            # Some mastery overlays render their title as artwork/canvas, leaving no searchable
            # DOM text. Use the existing template only to confirm the case, then tap through CDP.
            mastery_visible = ImageUtils.find_button(
                "new_extended_mastery_level", tries = 1, suppress_error = True
            ) is not None
            if mastery_visible and Game.evaluate_dom_js(center_tap_js):
                dismissed_any = True
                MessageLog.print_message(
                    "[INFO] Dismissed 'New Extended Mastery Level' overlay via CDP center tap."
                )
                Game.wait(1.0)
                continue

            break

        return dismissed_any

    @staticmethod
    def collect_loot(is_completed: bool, is_pending_battle: bool = False, is_event_nightmare: bool = False, skip_info: bool = False, skip_popup_check: bool = False, is_defender: bool = False, is_herald: bool = False) -> bool:
        """Collects the loot from the Results screen while clicking away any dialog popups while updating the internal item count.

        Args:
            is_completed (bool): Allows incrementing of number of runs completed. This is for Farming Modes who have multi-part sections to them to prevent unnecessary incrementing of runs when it wasn't finished with 1 yet.
            is_pending_battle (bool, optional): Skip the incrementation of runs attempted if this was a Pending Battle. Defaults to False.
            is_event_nightmare (bool, optional): Skip the incrementation of runs attempted if this was a Event Nightmare. Defaults to False.
            skip_info (bool, optional): Skip printing the information of the run. Defaults to False.
            skip_popup_check (bool, optional): Skip checking for popups to get to the Loot Collected screen. Defaults to False.
            is_defender (bool, optional): Skip the incrementation of runs attempted if this was a Defender. Defaults to False.

        Returns:
            (bool): True if loot was successfully collected and recorded, False if no loot was available or if recovery to Home screen was triggered.
        """
        # Guard: If bot is already at Home screen (#mypage), there is no loot to collect.
        if Game.evaluate_dom_js("Boolean(window.location.hash && (window.location.hash.startsWith('#mypage') || window.location.hash === ''))") or \
           ImageUtils.confirm_location("home", tries = 1, suppress_error = True):
            MessageLog.print_message("\n[INFO] Bot is already at the Home screen. Skipping loot collection.")
            return False

        temp_amount = 0

        # Close all popups until the bot reaches the Loot Collected screen.
        if skip_popup_check is False:
            loot_collection_tries = 45
            stuck_counter = 0
            while not ImageUtils.confirm_location("loot_collected", tries = 1, disable_adjustment = True):
                # If bot reached Home screen during loot check, exit immediately without wasting tries
                if Game.evaluate_dom_js("Boolean(window.location.hash && window.location.hash.startsWith('#mypage'))") or \
                   ImageUtils.confirm_location("home", tries = 1, suppress_error = True):
                    MessageLog.print_message("\n[INFO] Bot reached Home screen during loot check. Skipping loot collection.")
                    return False

                loot_collection_tries -= 1
                if loot_collection_tries <= 0:
                    MessageLog.print_message("\n[WARNING] Unable to confirm Loot Collection screen after multiple tries. Attempting recovery to Home screen...")
                    # 1. Attempt to dismiss any lingering GBF popups via DOM / internal view (if CDP is alive)
                    Game.evaluate_dom_js("""(() => {
                        if (window.Game && window.Game.view && typeof window.Game.view.popRemoveOnly === 'function') {
                            try { window.Game.view.popRemoveOnly(); } catch(e){}
                        }
                    })()""")
                    # 2. Attempt fast hash navigation to home if DOM is responsive
                    Game.evaluate_dom_js('window.location.hash = "#mypage"')
                    Game.wait(2.0)

                    # 3. Robust GUI fallback: use go_back_home() which checks/clicks the physical Home button,
                    # handles reload if needed, and verifies the Home screen location via image match.
                    recovery_success = False
                    try:
                        Game.go_back_home(confirm_location_check = True)
                        recovery_success = True
                    except Exception as e:
                        MessageLog.print_message(f"[WARNING] go_back_home check during recovery encountered: {e}. Trying reload and re-verification...")
                        Game.find_and_click_button("reload", suppress_error = True)
                        Game.wait(4.0)
                        # Re-verify if Home screen was reached after reload
                        if ImageUtils.confirm_location("home", bypass_general_adjustment = True, tries = 2):
                            recovery_success = True
                        else:
                            # Try one last physical click on Home button
                            if Game.find_and_click_button("home", bypass_general_adjustment = True, suppress_error = True):
                                Game.wait(3.0)
                                if ImageUtils.confirm_location("home", bypass_general_adjustment = True, tries = 2):
                                    recovery_success = True

                    if not recovery_success:
                        raise RuntimeError("Recovery failed: Bot was unable to navigate back to the Home screen after loot collection timeout.")

                    MessageLog.print_message("\n[WARNING] Loot collection timed out. Safely recovered to Home screen.")
                    MessageLog.print_message("[INFO] Run counter NOT incremented to keep farming statistics accurate.")
                    # Return False immediately so the caller knows loot was NOT collected and does NOT record false progress.
                    return False

                # Fast DOM check: verify if we reached the Results/Loot Collected screen
                reached_loot = Game.evaluate_dom_js("""(() => {
                    let hash = window.location.hash || '';

                    // Only block on popups that actually cover the screen (have visible offsetParent AND display != none).
                    // Exclude pop-notification-title (Trophy/Achievement) - it auto-navigates when closed.
                    // Exclude pop-global-menu which is always hidden.
                    let blockingPop = Array.from(document.querySelectorAll('.pop-usual.pop-show, .pop-show, .pop-friend-request'))
                        .find(el => {
                            if (el.classList.contains('pop-notification-title')) return false;
                            if (el.classList.contains('pop-global-menu')) return false;
                            return el.offsetParent !== null && window.getComputedStyle(el).display !== 'none';
                        });
                    if (blockingPop) return false;

                    // If a trophy/achievement popup is visible but can be safely ignored (it will auto-dismiss),
                    // treat the result as reachable.

                    let again = document.querySelector('.btn-again, .btn-retry');
                    if (again && again.offsetParent !== null) return true;

                    if (hash.includes('result')) {
                        let hasResultEl = document.querySelector('[class*="cnt-result"], .prt-result-head, .prt-reward-list, .prt-reward-multi, .prt-item-list, .prt-result-report, .prt-result-rank, .btn-control');
                        if (hasResultEl && hasResultEl.offsetParent !== null) return true;
                    }

                    return false;
                })()""")
                if reached_loot:
                    MessageLog.print_message("[INFO] Loot Collected screen reached (Results / Rewards screen visible).")
                    break

                # Dismiss popups via DOM (handles "EXP Gained" OK popup, quest clear popups, modal alerts, etc.)
                dom_clicked = Game.evaluate_dom_js("""(() => {
                    // Check for standard modal removal via GBF internal view if available
                    let popUsual = document.querySelector('.pop-usual, .pop-show, .pop-friend-request, [class*="pop-"]');
                    if (popUsual && popUsual.offsetParent !== null) {
                        // If this is a Trophy/Achievement popup, clicking Close navigates away from result screen.
                        // Instead of clicking it here, let it stay visible — reached_loot will detect quest/assist.
                        if (popUsual.classList.contains('pop-notification-title')) {
                            // Dismiss it via JS internal function if available, without triggering navigation
                            if (window.Game && window.Game.view && typeof window.Game.view.popRemoveOnly === 'function') {
                                try { window.Game.view.popRemoveOnly(); return 'popRemoveOnly-trophy'; } catch(e){}
                            }
                            // Fallback: close it (will navigate to quest/assist, which is acceptable)
                            let closeBtn = popUsual.querySelector('.btn-usual-close');
                            if (closeBtn && closeBtn.offsetParent !== null) {
                                let activated = false;
                                if (window.$ && typeof window.$(closeBtn).trigger === 'function') {
                                    try { window.$(closeBtn).trigger('tap'); activated = true; } catch(e) {}
                                }
                                if (!activated) closeBtn.click();
                                return 'trophy-close';
                            }
                            return null; // skip, wait for next iteration
                        }
                        let cancel = popUsual.querySelector('.btn-usual-cancel, .btn-usual-close, .btn-close');
                        if (cancel && cancel.offsetParent !== null) {
                            let activated = false;
                            if (window.$ && typeof window.$(cancel).trigger === 'function') {
                                try { window.$(cancel).trigger('tap'); activated = true; } catch(e) {}
                            }
                            if (!activated) cancel.click();
                            return 'modal-cancel';
                        }
                        let ok = popUsual.querySelector('.btn-usual-ok, .btn-result-next, .btn-settlement-next');
                        if (ok && ok.offsetParent !== null) {
                            let activated = false;
                            if (window.$ && typeof window.$(ok).trigger === 'function') {
                                try { window.$(ok).trigger('tap'); activated = true; } catch(e) {}
                            }
                            if (!activated) ok.click();
                            return 'modal-ok';
                        }
                        if (window.Game && window.Game.view && typeof window.Game.view.popRemoveOnly === 'function') {
                            try {
                                window.Game.view.popRemoveOnly();
                                return 'popRemoveOnly';
                            } catch(e){}
                        }
                    }

                    let sel = [
                        '.btn-usual-ok', '.btn-result-next', '.btn-settlement-next',
                        '.btn-usual-close', '.btn-close', '.btn-usual-cancel',
                        '.btn-close-hell', '.btn-link-item'
                    ];
                    for (let s of sel) {
                        let el = document.querySelector(s);
                        if (el && el.offsetParent !== null) {
                            let activated = false;
                            if (window.$ && typeof window.$(el).trigger === 'function') {
                                try { window.$(el).trigger('tap'); activated = true; } catch(e) {}
                            }
                            if (!activated) el.click();
                            return s;
                        }
                    }
                    return null;
                })()""")

                if dom_clicked:
                    MessageLog.print_message(f"[INFO] Dismissed post-battle popup via DOM ({dom_clicked}).")
                    stuck_counter = 0
                    Game.wait(1.5)
                    continue

                # Guard: On Quest Result pages (#result or #result_multi), do NOT use generic template
                # matching for "ok"/"close"/"cancel" because OpenCV mistakes "Event Home" for "ok".
                is_on_result = Game.evaluate_dom_js("""(() => {
                    let hash = window.location.hash || '';
                    let again = document.querySelector('.btn-again, .btn-retry');
                    let hasResultEl = document.querySelector('[class*="cnt-result"], .prt-result-head, .prt-reward-list, .prt-reward-multi, .btn-control');
                    return Boolean(hash.includes('result') || (again && again.offsetParent !== null) || (hasResultEl && hasResultEl.offsetParent !== null));
                })()""")

                if not is_on_result:
                    Game.find_and_click_button("ok", tries = 1, suppress_error = True)
                    Game.find_and_click_button("close", tries = 1, suppress_error = True)
                    Game.find_and_click_button("cancel", tries = 1, suppress_error = True)

                if Game.dismiss_post_battle_progression(max_attempts = 1):
                    stuck_counter = 0
                    continue

                if ImageUtils.confirm_location("no_loot", tries = 1, suppress_error = True, disable_adjustment = True):
                    return False

                # Last-resort fallback: if none of the above dismissed anything for several
                # consecutive iterations, tap the center of the screen once to try to progress
                # past whatever unrecognized popup/screen is currently blocking navigation.
                stuck_counter += 1
                if stuck_counter >= 5:
                    MessageLog.print_message("[WARNING] Stuck for several iterations. Tapping center of screen once as a fallback...")
                    if (Settings.window_left is not None and Settings.window_top is not None
                            and Settings.window_width is not None and Settings.window_height is not None):
                        tap_x = Settings.window_left + int(Settings.window_width * 0.5)
                        tap_y = Settings.window_top + int(Settings.window_height * 0.5)
                        MouseUtils.move_and_click_point(tap_x, tap_y, "stuck_fallback_dismiss")
                    stuck_counter = 0
                    Game.wait(1.5)
                    continue

                if Settings.debug_mode:
                    MessageLog.print_message("[DEBUG] Have not detected the Loot Collection screen yet...")

        # The result page can become visible just before delayed progression overlays (for example
        # Extended Mastery Level) appear. Drain them before recording loot and leaving the route.
        Game.dismiss_post_battle_progression(max_attempts = 4)

        # Record either completed runs (the stable/default behavior) or actual detected item drops.
        if is_completed and not is_pending_battle and not is_event_nightmare and not is_defender and not is_herald:
            Settings.amount_of_runs_finished += 1
            if Game._uses_run_progress():
                MessageLog.print_message("\n[INFO] Recording one completed run (progressMode=completedRuns).")
            elif Settings.progress_mode in ("detecteditems", "detected_items", "items"):
                MessageLog.print_message("\n[INFO] Detecting user-specified item drops from this run...")
                temp_amount = ImageUtils.find_farmed_items(Settings.item_name)
                Settings.item_amount_farmed += temp_amount
            else:
                raise ValueError(
                    f"Unsupported progressMode: {Settings.progress_mode}. "
                    "Use 'completedRuns' or 'detectedItems'."
                )
        elif is_pending_battle:
            MessageLog.print_message("\n[INFO] Detecting if any user-specified loot dropped from this pending battle...")
            temp_amount = 0

            Settings.item_amount_farmed += temp_amount

        # If there were item drops detected and the user opt in to sending their result to Granblue Automation Statistics, then have the frontend send the API request.
        if temp_amount != 0 and Settings.enable_opt_in_api:
            if is_pending_battle:
                Game._send_api_result(temp_amount, 0.0)
            else:
                Game._send_api_result(temp_amount, Settings.combat_elapsed_time)

        if is_completed and not is_pending_battle and not is_event_nightmare and not skip_info and not is_defender and not is_herald:
            if Game._uses_run_progress():
                MessageLog.print_message("\n**********************************************************************")
                MessageLog.print_message("**********************************************************************")
                MessageLog.print_message(f"[FARM] Farming Mode: {Settings.farming_mode}")
                MessageLog.print_message(f"[FARM] Mission: {Settings.mission_name}")
                MessageLog.print_message(f"[FARM] Amount of runs completed: {Settings.amount_of_runs_finished} / {Settings.item_amount_to_farm}")
                MessageLog.print_message("**********************************************************************")
                MessageLog.print_message("**********************************************************************\n")
                completed_marker = " :white_check_mark:" if Game._target_reached() else ""
                Game._send_discord_message(
                    f"> Runs completed for __{Settings.mission_name}__: "
                    f"**[{Settings.amount_of_runs_finished} / {Settings.item_amount_to_farm}]**{completed_marker}"
                )
            elif Settings.item_name != "EXP" and Settings.item_name != "Angel Halo Weapons" and Settings.item_name != "Repeated Runs":
                MessageLog.print_message("\n**********************************************************************")
                MessageLog.print_message("**********************************************************************")
                MessageLog.print_message(f"[FARM] Farming Mode: {Settings.farming_mode}")
                MessageLog.print_message(f"[FARM] Mission: {Settings.mission_name}")
                MessageLog.print_message(f"[FARM] Summons: {Settings.summon_list}")
                MessageLog.print_message(f"[FARM] Amount of {Settings.item_name} gained from this run: {temp_amount}")
                MessageLog.print_message(f"[FARM] Amount of {Settings.item_name} gained in total: {Settings.item_amount_farmed} / {Settings.item_amount_to_farm}")
                MessageLog.print_message(f"[FARM] Amount of runs completed: {Settings.amount_of_runs_finished}")
                MessageLog.print_message("**********************************************************************")
                MessageLog.print_message("**********************************************************************\n")

                if temp_amount != 0:
                    if Settings.item_amount_farmed >= Settings.item_amount_to_farm:
                        discord_string = f"> {temp_amount}x __{Settings.item_name}__ gained from this run: **[{Settings.item_amount_farmed - temp_amount} / {Settings.item_amount_to_farm}]** -> " \
                                         f"**[{Settings.item_amount_farmed} / {Settings.item_amount_to_farm}]** :white_check_mark:"
                    else:
                        discord_string = f"> {temp_amount}x __{Settings.item_name}__ gained from this run: **[{Settings.item_amount_farmed - temp_amount} / {Settings.item_amount_to_farm}]** -> " \
                                         f"**[{Settings.item_amount_farmed} / {Settings.item_amount_to_farm}]**"

                    Game._send_discord_message(discord_string)
            else:
                MessageLog.print_message("\n**********************************************************************")
                MessageLog.print_message("**********************************************************************")
                MessageLog.print_message(f"[FARM] Farming Mode: {Settings.farming_mode}")
                MessageLog.print_message(f"[FARM] Mission: {Settings.mission_name}")
                MessageLog.print_message(f"[FARM] Summons: {Settings.summon_list}")
                MessageLog.print_message(f"[FARM] Amount of runs completed: {Settings.amount_of_runs_finished} / {Settings.item_amount_to_farm}")
                MessageLog.print_message("**********************************************************************")
                MessageLog.print_message("**********************************************************************\n")

                if Settings.amount_of_runs_finished >= Settings.item_amount_to_farm:
                    discord_string = f"> Runs completed for __{Settings.mission_name}__: **[{Settings.amount_of_runs_finished - 1} / {Settings.item_amount_to_farm}]** -> " \
                                     f"**[{Settings.amount_of_runs_finished} / {Settings.item_amount_to_farm}]** :white_check_mark:"
                else:
                    discord_string = f"> Runs completed for __{Settings.mission_name}__: **[{Settings.amount_of_runs_finished - 1} / {Settings.item_amount_to_farm}]** -> " \
                                     f"**[{Settings.amount_of_runs_finished} / {Settings.item_amount_to_farm}]**"

                Game._send_discord_message(discord_string)
        elif is_pending_battle and temp_amount > 0 and not skip_info:
            if Settings.item_name != "EXP" and Settings.item_name != "Angel Halo Weapons" and Settings.item_name != "Repeated Runs":
                MessageLog.print_message("\n**********************************************************************")
                MessageLog.print_message("**********************************************************************")
                MessageLog.print_message(f"[FARM] Farming Mode: {Settings.farming_mode}")
                MessageLog.print_message(f"[FARM] Mission: {Settings.mission_name}")
                MessageLog.print_message(f"[FARM] Summons: {Settings.summon_list}")
                MessageLog.print_message(f"[FARM] Amount of {Settings.item_name} gained from this pending battle: {temp_amount}")
                MessageLog.print_message(f"[FARM] Amount of {Settings.item_name} gained in total: {Settings.item_amount_farmed} / {Settings.item_amount_to_farm}")
                MessageLog.print_message(f"[FARM] Amount of runs completed: {Settings.amount_of_runs_finished}")
                MessageLog.print_message("**********************************************************************")
                MessageLog.print_message("**********************************************************************\n")

                if temp_amount != 0:
                    if Settings.item_amount_farmed >= Settings.item_amount_to_farm:
                        discord_string = f"> {temp_amount}x __{Settings.item_name}__ gained from this pending battle: **[{Settings.item_amount_farmed - temp_amount} / {Settings.item_amount_to_farm}]** -> " \
                                         f"**[{Settings.item_amount_farmed} / {Settings.item_amount_to_farm}]** :white_check_mark:"
                    else:
                        discord_string = f"> {temp_amount}x __{Settings.item_name}__ gained from this pending battle: **[{Settings.item_amount_farmed - temp_amount} / {Settings.item_amount_to_farm}]** -> " \
                                         f"**[{Settings.item_amount_farmed} / {Settings.item_amount_to_farm}]**"

                    Game._send_discord_message(discord_string)
        elif is_herald:
            Settings.number_of_defeated_heralds += 1
            Settings.engaged_herald_battle = False
            if Settings.no_party_selection:
                Settings.party_selection_first_run = True
                Settings.no_party_selection = False
            MessageLog.print_message("\n**********************************************************************")
            MessageLog.print_message("**********************************************************************")
            MessageLog.print_message(f"[FARM] Farming Mode: {Settings.farming_mode}")
            MessageLog.print_message(f"[FARM] Mission: {Settings.mission_name}")
            MessageLog.print_message(f"[FARM] Summons: {Settings.summon_list}")
            MessageLog.print_message(f"[FARM] Amount of Heralds defeated: {Settings.number_of_defeated_heralds}/{Settings.number_of_heralds}")
            MessageLog.print_message("**********************************************************************")
            MessageLog.print_message("**********************************************************************\n")
        elif is_defender:
            Settings.number_of_defeated_defenders += 1
            MessageLog.print_message("\n**********************************************************************")
            MessageLog.print_message("**********************************************************************")
            MessageLog.print_message(f"[FARM] Farming Mode: {Settings.farming_mode}")
            MessageLog.print_message(f"[FARM] Mission: {Settings.mission_name}")
            MessageLog.print_message(f"[FARM] Summons: {Settings.summon_list}")
            MessageLog.print_message(f"[FARM] Amount of Defenders defeated: {Settings.number_of_defeated_defenders}/{Settings.number_of_defenders}")
            MessageLog.print_message("**********************************************************************")
            MessageLog.print_message("**********************************************************************\n")

        return True

    @staticmethod
    def collect_loot_safe(is_completed: bool, is_pending_battle: bool = False, is_event_nightmare: bool = False, skip_info: bool = False, skip_popup_check: bool = False,
                           is_defender: bool = False, is_herald: bool = False) -> bool:
        """Wrapper around collect_loot() that guarantees the bot never dies from an unhandled RuntimeError.

        collect_loot() raises RuntimeError if it exhausts every recovery path (DOM dismissal, hash navigation,
        go_back_home(), reload, and physical Home button click) and still cannot confirm the bot is back at the
        Home screen. Letting that exception propagate unhandled kills the entire bot process. This wrapper is the
        single place that decides what to do when that happens, instead of duplicating the same try/except in
        every Farming Mode's start() method.

        Args:
            Same as collect_loot().

        Returns:
            (bool): True if loot was successfully collected and recorded. False if there was no loot, if a
            recovery to the Home screen was triggered, or if collect_loot() raised RuntimeError and a final
            recovery attempt here also could not be verified (in which case the exception is re-raised, since
            continuing to run with an unconfirmed screen state risks a cascade of invalid clicks).
        """
        try:
            return Game.collect_loot(is_completed = is_completed, is_pending_battle = is_pending_battle, is_event_nightmare = is_event_nightmare, skip_info = skip_info,
                                      skip_popup_check = skip_popup_check, is_defender = is_defender, is_herald = is_herald)
        except RuntimeError as e:
            MessageLog.print_message(f"\n[WARNING] collect_loot() could not recover to the Home screen on its own: {e}\n{traceback.format_exc()}\nAttempting one final recovery here...")

            try:
                Game.go_back_home(confirm_location_check = True)
                MessageLog.print_message("[INFO] Final recovery succeeded. Bot is confirmed back at the Home screen. Run counter NOT incremented for this run.")
                return False
            except Exception:
                # Every recovery path available to the bot has now been exhausted. Continuing would mean
                # clicking blindly on an unknown screen, which risks cascading errors that are harder to
                # diagnose than a clean stop here. Let this propagate so the bot halts with a clear reason.
                MessageLog.print_message("[WARNING] Final recovery attempt also failed. Bot state is unknown; stopping to avoid a cascade of invalid clicks.")
                raise

    @staticmethod
    def check_for_ended_raid() -> bool:
        """Checks if the 'This raid battle has already ended. The Home screen will now appear.'
        popup is currently displayed. If found, dismisses it with one OK activation and returns
        True after the popup disappears or navigation starts.

        Returns:
            bool: True if an ended raid popup was detected and dismissed, False otherwise.
        """
        ended_popup_js = """(() => {
            const popups = document.querySelectorAll(
                '.pop-result-assist-raid, .pop-usual, .prt-popup-body, .prt-popup, [class*="popup"]'
            );
            for (const popup of popups) {
                if (!popup || popup.offsetParent === null || window.getComputedStyle(popup).display === 'none') continue;
                const text = (popup.innerText || popup.textContent || '').toLowerCase();
                if (!text.includes('already ended') &&
                    !text.includes('raid battle has already') &&
                    !text.includes('終了')) continue;

                let okButton = popup.querySelector('.btn-usual-ok, .btn-ok, .btn-usual-close');
                if (!okButton) {
                    okButton = document.querySelector(
                        '.pop-result-assist-raid .btn-usual-ok, .pop-show .btn-usual-ok'
                    );
                }
                if (!okButton || okButton.offsetParent === null) {
                    return {detected: true, dismissed: false, route: window.location.hash || ''};
                }

                let activated = false;
                if (window.$ && typeof window.$(okButton).trigger === 'function') {
                    try {
                        window.$(okButton).trigger('tap');
                        activated = true;
                    } catch (_) {}
                }
                if (!activated) okButton.click();
                return {detected: true, dismissed: true, route: window.location.hash || ''};
            }
            return {detected: false, dismissed: false, route: window.location.hash || ''};
        })()"""

        detected = False
        try:
            for _ in range(3):
                result = Game.evaluate_dom_js(ended_popup_js)
                if not isinstance(result, dict) or not result.get("detected"):
                    return detected

                detected = True
                if result.get("dismissed"):
                    initial_route = result.get("route") or ""
                    final_route = initial_route
                    transition_confirmed = False
                    for _ in range(5):
                        Game.wait(0.5)
                        state = Game.evaluate_dom_js("""(() => {
                            const popups = document.querySelectorAll(
                                '.pop-result-assist-raid, .pop-usual, .prt-popup-body, .prt-popup, [class*="popup"]'
                            );
                            let visible = false;
                            for (const popup of popups) {
                                if (!popup || popup.offsetParent === null || window.getComputedStyle(popup).display === 'none') continue;
                                const text = (popup.innerText || popup.textContent || '').toLowerCase();
                                if (text.includes('already ended') ||
                                    text.includes('raid battle has already') ||
                                    text.includes('終了')) {
                                    visible = true;
                                    break;
                                }
                            }
                            return {visible: visible, route: window.location.hash || ''};
                        })()""")
                        if not isinstance(state, dict):
                            continue
                        final_route = state.get("route") or final_route
                        if not state.get("visible") or final_route != initial_route:
                            transition_confirmed = True
                            break

                    transition_text = "confirmed" if transition_confirmed else "not confirmed before timeout"
                    MessageLog.print_message(
                        "[WARNING] 'This raid battle has already ended' popup detected and dismissed; "
                        f"transition {transition_text}. Current route: {final_route or 'unknown'}."
                    )
                    return True
                Game.wait(0.25)

            if detected:
                MessageLog.print_message(
                    "[WARNING] Ended-raid popup was detected but its OK button was not ready. "
                    "Treating the raid as ended so navigation recovery can take over."
                )
                return True
        except Exception:
            return detected
        return detected

    @staticmethod
    def check_for_popups() -> bool:
        """Detect any popups and attempt to close them all with the final destination being the Summon Selection screen.

        Returns:
            (bool): True if there was a Nightmare mission detected or some other popup appeared that requires the navigation process to be restarted.
        """
        MessageLog.print_message(f"\n[INFO] Now beginning process to check for popups...")

        # Fast DOM check: if already at Summon Selection screen, exit immediately without delay
        if getattr(Settings, "enable_dom_clicking", False):
            is_at_summon = Game.evaluate_dom_js("""(() => {
                let hash = window.location.hash || '';
                if (hash.includes('quest/supporter') || hash.includes('stage') || hash.includes('party')) return true;
                let el = document.querySelector('.btn-supporter, .prt-supporter, .btn-autoselect-supporter');
                return Boolean(el && el.offsetParent !== null);
            })()""")
            if is_at_summon:
                MessageLog.print_message("[INFO] Already arrived at Support Summon Selection screen via DOM.")
                return False

        check_popup_tries = 30
        while ImageUtils.confirm_location("select_a_summon", tries = 1, suppress_error = True) is False:
            check_popup_tries -= 1
            if check_popup_tries <= 0:
                raise RuntimeError("Failed to progress in the Check for Popups process...")

            # Fast DOM check on each iteration to exit as soon as the screen renders
            if getattr(Settings, "enable_dom_clicking", False):
                is_at_summon = Game.evaluate_dom_js("""(() => {
                    let hash = window.location.hash || '';
                    if (hash.includes('quest/supporter') || hash.includes('stage') || hash.includes('party')) return true;
                    let el = document.querySelector('.btn-supporter, .prt-supporter, .btn-autoselect-supporter');
                    return Boolean(el && el.offsetParent !== null);
                })()""")
                if is_at_summon:
                    MessageLog.print_message("[INFO] Confirmed arrival at Support Summon Selection screen via DOM.")
                    return False

            # Check if an ended raid popup appeared
            if Game.check_for_ended_raid():
                MessageLog.print_message("[INFO] Ended raid popup detected and dismissed in check_for_popups.")
                return True

            if Settings.farming_mode == "Rise of the Beasts" and ImageUtils.confirm_location("proud_solo_quest", tries = 1):
                # Scroll down the screen a little bit because the popup itself is too long for screen sizes around 1080p.
                MouseUtils.scroll_screen_from_home_button(-400)

            # Check for certain popups for certain Farming Modes.
            if (Settings.farming_mode == "Rise of the Beasts" and RiseOfTheBeasts.check_for_rotb_extreme_plus()) or (
                    Settings.farming_mode == "Special" and Settings.mission_name == "VH Angel Halo" and Settings.item_name == "Angel Halo Weapons" and Special.check_for_dimensional_halo()) or (
                    (Settings.farming_mode == "Event" or Settings.farming_mode == "Event (Token Drawboxes)") and Event.check_for_event_nightmare()):
                return True

            # If the bot tried to repeat a Extreme/Impossible difficulty Event Raid and it lacked the treasures to host it, go back to select the Mission again.
            if (Settings.farming_mode == "Event (Token Drawboxes)" or Settings.farming_mode == "Guild Wars") and ImageUtils.confirm_location("not_enough_treasure", tries = 1):
                Game.find_and_click_button("ok")
                return True

            # Attempt to close any popup by clicking on any detected "Close" and "Cancel" buttons.
            # Use ImageUtils for cancel to avoid clicking .btn-usual-cancel on game confirmation dialogs.
            if Game.find_and_click_button("close", tries = 1, suppress_error = True) is False:
                ImageUtils.find_and_click_button("cancel", tries = 1, suppress_error = True)

            if Settings.debug_mode:
                MessageLog.print_message("[DEBUG] Have not detected the Support Summon Selection screen yet...")

        return False

    @staticmethod
    def _clear_pending_battle():
        """Process a Pending Battle using DOM-based interaction with fallback to image matching.

        Returns:
            (bool): Return True if a Pending Battle was successfully processed. Otherwise, return False.
        """
        # A pending raid is rendered as .lis-raid with a .prt-button-cover on the current
        # GBF page. Older layouts used .lis-quest / .btn-unclaimed. Poll briefly because
        # the route changes before the list has necessarily finished rendering.
        clicked = False
        wrong_route = False
        for _ in range(8):
            click_result = Game.evaluate_dom_js("""(() => {
                const hash = window.location.hash || '';
                if (!hash.includes('quest/assist/unclaimed')) {
                    return {clicked: false, wrongRoute: true};
                }

                const isVisible = (el) => {
                    if (!el || el.offsetParent === null) return false;
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') return false;
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                };

                const selectors = [
                    '.lis-raid .prt-button-cover',
                    '.lis-quest .prt-button-cover',
                    '.lis-raid .btn-result',
                    '.lis-quest .btn-result',
                    '.lis-raid [data-location-href*="result"]',
                    '.lis-quest [data-location-href*="result"]',
                    '.lis-raid',
                    '.lis-quest'
                ];

                let item = null;
                let matchedSelector = null;
                for (const selector of selectors) {
                    for (const candidate of document.querySelectorAll(selector)) {
                        if (isVisible(candidate)) {
                            item = candidate;
                            matchedSelector = selector;
                            break;
                        }
                    }
                    if (item) break;
                }
                if (!item) return {clicked: false};

                try { item.scrollIntoView({block: 'center', behavior: 'instant'}); } catch (_) {}
                let activated = false;
                if (window.$ && typeof window.$(item).trigger === 'function') {
                    try {
                        window.$(item).trigger('tap');
                        activated = true;
                    } catch (_) {}
                }
                if (!activated) {
                    try { item.click(); activated = true; } catch (_) {}
                }
                return {
                    clicked: activated,
                    selector: matchedSelector,
                    cls: `${item.className || ''}`,
                    text: (item.innerText || item.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80)
                };
            })()""")
            if isinstance(click_result, dict):
                wrong_route = bool(click_result.get("wrongRoute"))
                clicked = bool(click_result.get("clicked"))
                if clicked:
                    selector = click_result.get("selector", "DOM")
                    MessageLog.print_message(f"[INFO] Activated Pending Battle reward via {selector}.")
            else:
                # Preserve compatibility with mocked/older CDP responses that return a bool.
                clicked = bool(click_result)
            if clicked:
                break
            if wrong_route:
                MessageLog.print_message(
                    "[WARNING] Refusing to click a Pending Battle reward outside the "
                    "Pending Battles page."
                )
                break
            Game.wait(0.75)

        if clicked:
            MessageLog.print_message(f"[INFO] Clearing this Pending Battle...")

            # Wait for page to transition to #result_multi/xxx (result screen)
            # After clicking the WON banner, GBF shows: EXP Gained popup → Quest Results + Loot
            Game.wait(2.5)

            # Poll for either the EXP modal or result page. A DOM click is only considered
            # successful after this transition; stale overlays can accept a synthetic tap
            # without actually opening the reward.
            claim_transitioned = False
            for _ in range(12):
                is_ready = Game.evaluate_dom_js("""(() => {
                    let hash = window.location.hash || '';
                    if (hash.includes('result')) return true;
                    let result = document.querySelector(
                        '.pop-exp, .pop-usual.pop-show, .prt-reward-list, .prt-reward-multi, .prt-result-win, .cnt-result'
                    );
                    return Boolean(result && result.offsetParent !== null);
                })()""")
                if is_ready:
                    claim_transitioned = True
                    break
                Game.wait(1.0)

            if not claim_transitioned:
                MessageLog.print_message(
                    "[WARNING] Pending Battle reward control was activated, but the Results "
                    "screen did not open. The claim will be retried during recovery."
                )
                return False

            # STEP 1: Dismiss EXP Gained popup (the first popup that appears after clicking WON banner).
            # The popup has class 'pop-exp' or 'pop-usual pop-show' and the OK button is '.btn-usual-ok'.
            for _exp_try in range(8):
                _exp_dismissed = Game.evaluate_dom_js("""(() => {
                    // Try EXP-specific popup first
                    let expPopup = document.querySelector('.pop-exp');
                    if (expPopup && expPopup.offsetParent !== null) {
                        let ok = expPopup.querySelector('.btn-usual-ok, .btn-ok');
                        if (ok && ok.offsetParent !== null) {
                            let activated = false;
                            if (window.$ && typeof window.$(ok).trigger === 'function') {
                                try { window.$(ok).trigger('tap'); activated = true; } catch(e) {}
                            }
                            if (!activated) ok.click();
                            return 'exp-popup';
                        }
                    }
                    // Fallback: any visible popup with OK button
                    let popup = document.querySelector('.pop-usual.pop-show');
                    if (popup && popup.offsetParent !== null) {
                        let ok = popup.querySelector('.btn-usual-ok, .btn-ok');
                        if (ok && ok.offsetParent !== null) {
                            let activated = false;
                            if (window.$ && typeof window.$(ok).trigger === 'function') {
                                try { window.$(ok).trigger('tap'); activated = true; } catch(e) {}
                            }
                            if (!activated) ok.click();
                            return 'generic-popup';
                        }
                    }
                    return null;
                })()""")
                if _exp_dismissed:
                    MessageLog.print_message(f"[INFO] Dismissed EXP Gained popup ({_exp_dismissed}).")
                    Game.wait(1.5)
                    break
                # Check if already past popup (loot screen visible)
                _on_result = Game.evaluate_dom_js("""(() => {
                    let loot = document.querySelector('.prt-reward-list, .prt-reward-multi, .btn-control');
                    return Boolean(loot && loot.offsetParent !== null);
                })()""")
                if _on_result:
                    break
                Game.wait(0.8)

            # STEP 2: Check for the no-loot state through DOM only. Opening a pending
            # result is what claims the reward; no OCR/image scan is needed here.
            no_loot = Game.evaluate_dom_js("""(() => {
                const noLoot = document.querySelector('.prt-no-loot, .cnt-no-loot, .txt-no-loot');
                if (noLoot && noLoot.offsetParent !== null) return true;
                const bodyText = (document.body.innerText || '').toLowerCase();
                return bodyText.includes('no loot') || bodyText.includes('no rewards');
            })()""")
            if no_loot:
                MessageLog.print_message(f"[INFO] No loot can be collected.")
                # Navigate back to pending battles list
                _nav_back = Game.evaluate_dom_js("""(() => {
                    let btn = document.querySelector('.btn-control.btn-unclaimed, [data-location-href="quest/assist/unclaimed"]');
                    if (btn && btn.getBoundingClientRect().width > 0) {
                        let activated = false;
                        if (window.$ && typeof window.$(btn).trigger === 'function') {
                            try { window.$(btn).trigger('tap'); activated = true; } catch(e) {}
                        }
                        if (!activated) btn.click();
                        return true;
                    }
                    return false;
                })()""")
                if not _nav_back:
                    Game.evaluate_dom_js('window.location.hash = "#quest/assist/unclaimed"; true')
                return True

            # STEP 3: Confirm the result route through DOM. Merely opening this result
            # claims its pending reward; pending rewards are not added to the normal run
            # counter, so the image/OCR loot collector must not run here.
            result_confirmed = Game.evaluate_dom_js("""(() => {
                const hash = window.location.hash || '';
                const result = document.querySelector(
                    '.prt-reward-list, .prt-reward-multi, .prt-result-win, .cnt-result, .btn-control'
                );
                return hash.includes('result') || Boolean(result && result.offsetParent !== null);
            })()""")
            if not result_confirmed:
                MessageLog.print_message(
                    "[WARNING] Pending Battle Results page could not be confirmed through DOM."
                )
                return False

            MessageLog.print_message("[INFO] Pending Battle reward claimed through DOM.")
            return True
        else:
            MessageLog.print_message(f"[INFO] No claimable Pending Battle card was found through DOM.")

        return False

    @staticmethod
    def check_for_friend_request():
        """Check for the Friend Request popup.

        Returns:
            None
        """
        if ImageUtils.confirm_location("friend_request"):
            Game.find_and_click_button("cancel")
            Game.wait(2.0)
        return None

    @staticmethod
    def check_for_skyscope():
        """Check for the Skyscope popup.

        Returns:
            None
        """
        if ImageUtils.confirm_location("skyscope"):
            Game.find_and_click_button("close")
            Game.wait(2.0)
        return None

    @staticmethod
    def check_for_pending():
        """Check and collect any pending rewards and free up slots for the bot to join more raids.

        Returns:
            (bool): Return True if Pending Battles were detected. Otherwise, return False.
        """
        MessageLog.print_message(f"\n[INFO] Starting process of checking for Pending Battles...")

        if Settings.enable_pending_battles_adjustment:
            Game.wait(Settings.adjust_before_pending_battle)
        else:
            Game.wait(1)

        # 1. Check if already on the Pending Battles screen (#quest/assist/unclaimed)
        _already_on_unclaimed = Game.evaluate_dom_js("""(() => {
            let hash = window.location.hash || '';
            return hash.includes('quest/assist/unclaimed');
        })()""")

        # 2. Check for any visible popup mentioning 'pending'
        _dom_pending_popup = Game.evaluate_dom_js("""(() => {
            let popups = document.querySelectorAll(
                '.pop-usual, .pop-show, .prt-popup-body, .txt-popup-body, .prt-popup-header, [class*="pop-"]'
            );
            for (let el of popups) {
                if (el.offsetParent !== null && window.getComputedStyle(el).display !== 'none') {
                    let text = el.innerText || el.textContent || '';
                    if (text.toLowerCase().includes('pending')) {
                        return true;
                    }
                }
            }
            const controls = document.querySelectorAll(
                '.btn-unconfirmed-result, .flow-unclaimed, .btn-unclaimed, ' +
                '[data-href*="quest/assist/unclaimed"], [data-location-href*="quest/assist/unclaimed"], ' +
                'a[href*="quest/assist/unclaimed"]'
            );
            for (const control of controls) {
                if (control.offsetParent !== null && window.getComputedStyle(control).display !== 'none') {
                    return true;
                }
            }
            return false;
        })()""")

        _has_pending = (_already_on_unclaimed or _dom_pending_popup)

        if _has_pending:
            MessageLog.print_message(f"[INFO] Found Pending Battles that need collecting from.")

            # If there is a popup visible, dismiss it with OK to navigate to the Pending Battles screen
            if not _already_on_unclaimed:
                _ok_clicked = Game.evaluate_dom_js("""(() => {
                    let popups = document.querySelectorAll('.pop-usual, .pop-show, [class*="pop-"]');
                    for (let p of popups) {
                        if (p.offsetParent !== null && window.getComputedStyle(p).display !== 'none') {
                            let text = p.innerText || p.textContent || '';
                            if (text.toLowerCase().includes('pending')) {
                                let btn = p.querySelector('.btn-usual-ok, .btn-ok, [class*="ok"]');
                                if (btn && btn.offsetParent !== null) {
                                    let activated = false;
                                    if (window.$ && typeof window.$(btn).trigger === 'function') {
                                        try { window.$(btn).trigger('tap'); activated = true; } catch(e) {}
                                    }
                                    if (!activated) btn.click();
                                    return true;
                                }
                            }
                        }
                    }
                    let genericOk = document.querySelector('.pop-usual .btn-usual-ok, .btn-usual-ok, .btn-ok, [data-text="ok"]');
                    if (genericOk && genericOk.getBoundingClientRect().width > 0) {
                        let activated = false;
                        if (window.$ && typeof window.$(genericOk).trigger === 'function') {
                            try { window.$(genericOk).trigger('tap'); activated = true; } catch(e) {}
                        }
                        if (!activated) genericOk.click();
                        return true;
                    }
                    return false;
                })()""")
                if not _ok_clicked:
                    MessageLog.print_message(
                        "[INFO] Pending popup had no clickable DOM OK control; using the direct "
                        "Pending Battles route."
                    )
                Game.wait(2.0)

            # Verify that the popup actually navigated to Pending Battles. The route can
            # update before the list is rendered, so poll first. If the popup's OK handler
            # did not navigate, open the known Pending Battles route directly.
            _is_on_pending = False
            for _ in range(8):
                _is_on_pending = bool(Game.evaluate_dom_js("""(() => {
                    const hash = window.location.hash || '';
                    if (hash.includes('quest/assist/unclaimed')) return true;
                    return Boolean(document.querySelector(
                        '.cnt-unclaimed, .prt-unclaimed-list, [class*="unclaimed-list"]'
                    ));
                })()"""))
                if _is_on_pending:
                    break
                Game.wait(0.75)

            if not _is_on_pending:
                MessageLog.print_message(
                    "[INFO] Pending Battles popup did not open the reward list; navigating "
                    "directly to the Pending Battles page."
                )
                Game.evaluate_dom_js('window.location.hash = "#quest/assist/unclaimed"; true')
                Game.wait(2.0)
                for _ in range(8):
                    _is_on_pending = bool(Game.evaluate_dom_js("""(() => {
                        const hash = window.location.hash || '';
                        return hash.includes('quest/assist/unclaimed');
                    })()"""))
                    if _is_on_pending:
                        break
                    Game.wait(0.75)

            if _is_on_pending:
                # Process a bounded number of distinct Pending Battles. A stale DOM element can
                # report a successful tap without navigating; the signature prevents that state
                # from trapping this call forever.
                _seen_pending_states = set()
                _pending_clear_completed = True
                for _pending_index in range(10):
                    _pending_state = Game.evaluate_dom_js("""(() => {
                        const hash = window.location.hash || '';
                        const cards = [...document.querySelectorAll('.lis-raid, .lis-quest')]
                            .filter(el => el.offsetParent !== null)
                            .map(el => [
                                el.getAttribute('data-raid-id') || '',
                                el.getAttribute('data-battle-key') || '',
                                el.getAttribute('data-location-href') || '',
                                (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim()
                            ].join('|'));
                        return `${hash}::${cards.join(';;')}`;
                    })()""")
                    if _pending_state and _pending_state in _seen_pending_states:
                        _pending_clear_completed = False
                        MessageLog.print_message(
                            "[WARNING] Pending Battle state did not change after processing; "
                            "stopping this recovery pass to avoid an infinite loop."
                        )
                        break
                    if _pending_state:
                        _seen_pending_states.add(_pending_state)

                    if not Game._clear_pending_battle():
                        _pending_clear_completed = False
                        MessageLog.print_message(
                            "[WARNING] Pending Battles were detected, but no claimable reward item "
                            "could be activated. Leaving pending recovery unresolved."
                        )
                        break
                    Game.wait(2.0)

                    # On the Quest Results screen, click "Pending Battles" button to return to #quest/assist/unclaimed.
                    # From live DOM inspection: class is "btn-control btn-unclaimed" with data-location-href="quest/assist/unclaimed"
                    _navigated_back = Game.evaluate_dom_js("""(() => {
                        // Target the navigation button that links back to the pending battles list
                        let candidates = [
                            document.querySelector('.btn-control.btn-unclaimed'),
                            document.querySelector('[data-location-href="quest/assist/unclaimed"]'),
                            document.querySelector('a[href*="quest/assist/unclaimed"]')
                        ];
                        for (let btn of candidates) {
                            if (btn && btn.getBoundingClientRect().width > 0) {
                                let activated = false;
                                if (window.$ && typeof window.$(btn).trigger === 'function') {
                                    try { window.$(btn).trigger('tap'); activated = true; } catch(e) {}
                                }
                                if (!activated) btn.click();
                                return true;
                            }
                        }
                        return false;
                    })()""")

                    if _navigated_back:
                        MessageLog.print_message("[INFO] Navigated back to Pending Battles screen via DOM.")
                        Game.wait(2.0)
                    else:
                        MessageLog.print_message("[INFO] No more 'Pending Battles' button found on results screen; all pending battles claimed.")
                        break
                else:
                    _pending_clear_completed = False
                    MessageLog.print_message(
                        "[WARNING] Reached the safety limit of 10 Pending Battles in one pass; "
                        "continuing through normal navigation recovery."
                    )

                # Navigate away from Pending Battles / Results screen
                if Settings.farming_mode == "Raid":
                    _assist_clicked = Game.evaluate_dom_js("""(() => {
                        let btn = document.querySelector(
                            '.btn-assist, [data-href="quest/assist"], ' +
                            '[data-location-href="quest/assist"], a[href$="quest/assist"]'
                        );
                        if (btn && btn.getBoundingClientRect().width > 0) {
                            let activated = false;
                            if (window.$ && typeof window.$(btn).trigger === 'function') {
                                try { window.$(btn).trigger('tap'); activated = true; } catch(e) {}
                            }
                            if (!activated) btn.click();
                            return true;
                        }
                        return false;
                    })()""")
                    if not _assist_clicked:
                        MessageLog.print_message(
                            "[INFO] Backup Requests DOM button was unavailable; opening its route directly."
                        )
                        Game.evaluate_dom_js('window.location.hash = "#quest/assist"; true')
                else:
                    Game.evaluate_dom_js('window.location.hash = "#mypage"; true')

                Game.wait(2.0)

                if _pending_clear_completed:
                    MessageLog.print_message(f"[INFO] Pending battles have been cleared.")
                else:
                    MessageLog.print_message(
                        "[WARNING] Pending battles could not be fully cleared; "
                        "continuing through guarded navigation recovery."
                    )
            else:
                MessageLog.print_message(
                    "[WARNING] Pending Battles were detected, but the Pending Battles screen "
                    "could not be confirmed. Continuing through guarded navigation recovery."
                )
            return True

        MessageLog.print_message(f"[INFO] No Pending Battles needed to be cleared.")
        return False

    @staticmethod
    def start_discord_process():
        """Starts the Discord process.

        Returns:
            None
        """
        if Settings.enable_discord and Settings.discord_token != "" and Settings.user_id != 0:
            MessageLog.print_message("\n[DISCORD] Starting Discord process on a new Thread...")
            Game._discord_process = multiprocessing.Process(target = discord_utils.start_now, args = (Settings.discord_token, Settings.user_id, Game._discord_queue))
            Game._discord_process.start()
        else:
            MessageLog.print_message("\n[DISCORD] Unable to start Discord process. Either you opted not to turn it on or your included token/user id inside the Settings or settings.json are invalid.")

        return None

    @staticmethod
    def stop_discord_process():
        """Stops the Discord process.

        Returns:
            None
        """
        if Game._discord_process is not None and Game._discord_process.is_alive():
            MessageLog.print_message("\n[DISCORD] Now terminating Discord process...")
            drain_deadline = time.time() + 5.0
            while (Game._discord_process.is_alive() and
                   Game._discord_queue.empty() is False and
                   time.time() < drain_deadline):
                Game.wait(1.0)

            if Game._discord_process.is_alive():
                Game._discord_queue.put(f"```diff\n- Terminated connection to Discord API for Granblue Automation\n```")
            MessageLog.print_message("[DISCORD] Terminated connection to Discord API and terminating its Thread.")
            Game.wait(1.0)
            if Game._discord_process.is_alive():
                Game._discord_process.terminate()
            Game._discord_process.join(timeout = 5.0)

        return None

    @staticmethod
    def _send_api_result(amount: int, elapsed_time: float):
        """Prints a formatted message as a way to send the event back to the frontend in order to have it send the result to the database.

        Args:
            amount (int): Amount of items detected for this run.
            elapsed_time (str): Elapsed time for Combat Mode from start to finish.

        Returns:
            None
        """
        formatted_elapsed_time = elapsed_time
        if formatted_elapsed_time != 0.0:
            import datetime
            formatted_elapsed_time = str(datetime.timedelta(seconds = elapsed_time)).split('.')[0]

        MessageLog.print_message(f"\nSending API request to Granblue Automation Statistics...")
        MessageLog.print_message(f"API-RESULT|{Settings.item_name}|{amount}|{formatted_elapsed_time}")
        return None

    @staticmethod
    def start_farming_mode():
        """Start the Farming Mode using the given parameters.

        Returns:
            (bool): True if Farming Mode ended successfully.
        """
        exception_occurred = False
        try:
            Game.start_discord_process()

            if Settings.enable_test_for_home_screen:
                Game.go_back_home(confirm_location_check = True, test_mode = True)
                return True

            # Calibrate the dimensions of the bot window on bot launch.
            if Settings.farming_mode.endswith("V2"):
                Window.calibrate()
            else:
                Game._calibrate_game_window(display_info_check = True)


            if Settings.item_name != "EXP":
                MessageLog.print_message("\n######################################################################")
                MessageLog.print_message("######################################################################")
                MessageLog.print_message(f"[FARM] Starting Farming Mode for {Settings.farming_mode}.")
                MessageLog.print_message(f"[FARM] Farming {Settings.item_amount_to_farm}x {Settings.item_name} at {Settings.mission_name}.")
                MessageLog.print_message(f"[FARM] Combat Script name: {Settings.combat_script_name}")
                MessageLog.print_message(f"[FARM] Combat Script: {Settings.combat_script}")
                MessageLog.print_message(f"[FARM] Summons: {Settings.summon_list}")
                MessageLog.print_message(f"[FARM] Group #: {Settings.group_number}")
                MessageLog.print_message(f"[FARM] Party #: {Settings.party_number}")
                MessageLog.print_message("######################################################################")
                MessageLog.print_message("######################################################################\n")
            else:
                MessageLog.print_message("\n######################################################################")
                MessageLog.print_message("######################################################################")
                MessageLog.print_message(f"[FARM] Starting Farming Mode for {Settings.farming_mode}.")
                MessageLog.print_message(f"[FARM] Doing {Settings.item_amount_to_farm}x runs for {Settings.item_name} at {Settings.mission_name}.")
                MessageLog.print_message(f"[FARM] Combat Script name: {Settings.combat_script_name}")
                MessageLog.print_message(f"[FARM] Combat Script: {Settings.combat_script}")
                MessageLog.print_message(f"[FARM] Summons: {Settings.summon_list}")
                MessageLog.print_message(f"[FARM] Group #: {Settings.group_number}")
                MessageLog.print_message(f"[FARM] Party #: {Settings.party_number}")
                MessageLog.print_message("######################################################################")
                MessageLog.print_message("######################################################################\n")

            first_run = True
            while not Game._target_reached():
                if Settings.farming_mode == "Quest":
                    Quest.start(first_run)
                elif Settings.farming_mode == "Special":
                    Special.start(first_run)
                elif Settings.farming_mode == "Coop":
                    Coop.start(first_run)
                elif Settings.farming_mode == "Raid":
                    Raid.start(first_run)
                elif Settings.farming_mode == "Event" or Settings.farming_mode == "Event (Token Drawboxes)":
                    Event.start(first_run)
                elif Settings.farming_mode == "Rise of the Beasts":
                    RiseOfTheBeasts.start(first_run)
                elif Settings.farming_mode == "Guild Wars":
                    GuildWars.start(first_run)
                elif Settings.farming_mode == "Dread Barrage":
                    DreadBarrage.start(first_run)
                elif Settings.farming_mode == "Proving Grounds":
                    ProvingGrounds.start(first_run)
                elif Settings.farming_mode == "Arcarum":
                    Arcarum.start()
                elif Settings.farming_mode == "Arcarum Sandbox":
                    ArcarumSandbox.start()
                elif Settings.farming_mode == "Generic":
                    Generic.start()
                elif Settings.farming_mode == "GenericV2":
                    GenericV2.start()
                    break

                if not Game._target_reached():
                    # Generate a resting period if the user enabled it.
                    Game._delay_between_runs()
                    Game._move_mouse_security_check()
                    first_run = False

        except Exception as e:
            Game._send_discord_message(f"> Bot encountered exception in Farming Mode: \n{e}")
            exception_occurred = True
            MessageLog.print_message(f"\n[ERROR] Bot encountered exception in Farming Mode: \n{traceback.format_exc()}")
            if Settings.show_blocking_error_alert:
                try:
                    ImageUtils.generate_alert(f"Bot encountered exception in Farming Mode: \n{e}")
                except Exception as alert_error:
                    MessageLog.print_message(f"[WARNING] Could not display exception alert: {alert_error}")

        Game.stop_discord_process()

        if exception_occurred:
            MessageLog.print_message("\n######################################################################")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("[FARM] Ending Farming Mode due to encountering Exception.")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("######################################################################\n")
            Game.wait(1.0)
            return False
        else:
            MessageLog.print_message("\n######################################################################")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("[FARM] Ending Farming Mode.")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("######################################################################\n")
            Game._move_mouse_security_check()
            Game.wait(1.0)
            return True
