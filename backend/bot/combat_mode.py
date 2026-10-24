import copy
import os
from typing import List
import time

from utils.settings import Settings
from utils.message_log import MessageLog
from utils.image_utils import ImageUtils
from utils.mouse_utils import MouseUtils


class CombatModeException(Exception):
    def __init__(self, message):
        super().__init__(message)


class CombatMode:
    """
    Provides the utility functions needed for Combat Mode.
    """

    # Save a reference to the original current working directory.
    _owd = os.getcwd()

    _healing_item_commands = ["usegreenpotion.target(1)", "usegreenpotion.target(2)", "usegreenpotion.target(3)", "usegreenpotion.target(4)", "usebluepotion", "usefullelixir",
                              "usesupportpotion", "useclarityherb.target(1)", "useclarityherb.target(2)", "useclarityherb.target(3)", "useclarityherb.target(4)", "userevivalpotion"]

    # Save some variables for use throughout the class.
    _semi_auto = False
    _full_auto = False
    _attack_button_location = None
    _retreat_check = False
    _start_time: float = None
    _list_of_exit_events_for_false = ["Time Exceeded", "No Loot"]
    _list_of_exit_events_for_true = ["Battle Concluded", "Exp Gained", "Loot Collected"]
    _command_turn_number = 1
    _turn_number = 1  # Current turn for the script execution.
    _wipe_check_counter: int = 0
    _FULL_AUTO_CONTROL_WAIT_ATTEMPTS = 45
    _FULL_AUTO_ACTIVATION_VERIFY_ATTEMPTS = 6

    @staticmethod
    def _combat_safety_timeout_seconds():
        """Return the bounded monitor timeout, or ``None`` when explicitly disabled."""
        if getattr(Settings, "enable_no_timeout", False):
            return None

        configured = float(getattr(Settings, "time_allowed_until_auto_exit_raid", 600))
        return max(60.0, configured)

    @staticmethod
    def _check_monitor_safety_timeout(start_time: float, workflow_name: str) -> None:
        """Stop a passive monitor that can no longer prove forward progress."""
        timeout = CombatMode._combat_safety_timeout_seconds()
        now = time.time()
        if timeout is None or now - start_time < timeout:
            return

        elapsed = int(now - start_time)
        MessageLog.print_message(
            f"[ERROR] {workflow_name} exceeded its {int(timeout)}s safety limit "
            f"({elapsed}s elapsed). Starting bounded Home recovery."
        )
        raise CombatModeException("Time Exceeded")

    ######################################################################
    ######################################################################
    # Checks
    ######################################################################
    ######################################################################

    @staticmethod
    def _click_raid_elixir_prompt() -> bool:
        """Click only an elixir/revive control that belongs to the visible wipe prompt."""
        from bot.game import Game

        try:
            result = Game.evaluate_dom_js(r"""(() => {
                function visible(el) {
                    if (!el || el.offsetParent === null) return false;
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && style.visibility !== 'hidden';
                }
                function activate(el) {
                    let activated = false;
                    if (window.$ && typeof window.$(el).trigger === 'function') {
                        try { window.$(el).trigger('tap'); activated = true; } catch (_) {}
                    }
                    if (!activated) el.click();
                }

                // Prefer controls whose purpose is unambiguous, even when the game renders
                // them outside the generic popup container.
                const direct = Array.from(document.querySelectorAll('.btn-use-elixir, .btn-revive'))
                    .find(visible);
                if (direct) {
                    activate(direct);
                    return true;
                }

                // A wiped party normally gets a generic OK/Cancel popup.  Only accept its
                // generic OK when the popup text proves that it is the elixir prompt.
                const popups = document.querySelectorAll(
                    '.pop-usual, .prt-popup, .prt-popup-body, [class*="pop-continue"]'
                );
                for (const popup of popups) {
                    if (!visible(popup)) continue;
                    const text = (popup.innerText || popup.textContent || '').toLowerCase();
                    const isElixirPrompt = text.includes('elixir') || text.includes('revive') ||
                        text.includes('come back') || text.includes('\u5168\u6ec5');
                    if (!isElixirPrompt) continue;
                    const confirm = Array.from(popup.querySelectorAll(
                        '.btn-use-elixir, .btn-revive, .btn-usual-ok, .btn-ok'
                    )).find(visible);
                    if (confirm) {
                        activate(confirm);
                        return true;
                    }
                }
                return false;
            })()""")
            return bool(result)
        except Exception:
            return False

    @staticmethod
    def _raid_party_revive_state():
        """Return True when revived, False while still wiped, or None if CDP cannot tell."""
        from bot.game import Game

        try:
            result = Game.evaluate_dom_js(r"""(() => {
                function visible(el) {
                    if (!el || el.offsetParent === null) return false;
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && style.visibility !== 'hidden';
                }

                const wipeControl = Array.from(document.querySelectorAll(
                    '.btn-use-elixir, .btn-revive'
                )).some(visible);
                if (wipeControl) return false;

                const popups = document.querySelectorAll('.pop-usual, .prt-popup, .prt-popup-body');
                for (const popup of popups) {
                    if (!visible(popup)) continue;
                    const text = (popup.innerText || popup.textContent || '').toLowerCase();
                    if (text.includes('elixir') || text.includes('revive') ||
                            text.includes('come back') || text.includes('\u5168\u6ec5')) return false;
                }

                const player = window.stage && window.stage.gGameStatus &&
                    window.stage.gGameStatus.player;
                if (player && Array.isArray(player.param) && player.param.length) {
                    return player.param.some(member =>
                        member && Number(member.hp) > 0 && member.alive !== 0
                    );
                }

                const hash = window.location.hash || '';
                const battleControl = Array.from(document.querySelectorAll(
                    '.btn-attack-start, .btn-auto, .btn-raid-menu'
                )).some(visible);
                if ((hash.includes('raid') || hash.includes('stage')) && battleControl) return true;
                return null;
            })()""")
            return result if isinstance(result, bool) else None
        except Exception:
            return None

    @staticmethod
    def _revive_raid_party_with_elixir(party_wipe_indicator = None) -> bool:
        """Use a Full Elixir after a Raid wipe and verify that combat is resumable."""
        from bot.game import Game

        MessageLog.print_message(
            "[RAID] Party wipe detected. Attempting to use a Full Elixir and resume this raid..."
        )

        prompt_activated = CombatMode._click_raid_elixir_prompt()
        for attempt in range(10):
            if not prompt_activated:
                indicator = party_wipe_indicator
                if indicator is None:
                    indicator = ImageUtils.find_button(
                        "party_wipe_indicator", tries = 1, suppress_error = True
                    )
                if indicator is not None:
                    MouseUtils.move_and_click_point(
                        indicator[0], indicator[1], "party_wipe_indicator"
                    )
                    party_wipe_indicator = None
                    prompt_activated = True
                    Game.wait(0.5)

            # The first click may open a second confirmation prompt.
            if CombatMode._click_raid_elixir_prompt():
                prompt_activated = True

            # Image fallback is deliberately gated by the Continue header so a generic OK
            # elsewhere can never spend or confirm an unrelated action.
            if ImageUtils.confirm_location("continue", tries = 1, suppress_error = True):
                if Game.find_and_click_button("ok", tries = 1, suppress_error = True):
                    prompt_activated = True

            Game.wait(1.0)
            revive_state = CombatMode._raid_party_revive_state()
            if revive_state is True:
                MessageLog.print_message(
                    "[SUCCESS] Full Elixir used successfully. Resuming the current raid."
                )
                return True

            # CDP-less fallback: an Attack control with no wipe/Continue indicator is enough
            # evidence that the party returned to active combat.
            if revive_state is None and prompt_activated:
                wipe_still_visible = ImageUtils.find_button(
                    "party_wipe_indicator", tries = 1, suppress_error = True
                ) is not None
                continue_visible = ImageUtils.confirm_location(
                    "continue", tries = 1, suppress_error = True
                )
                attack_visible = ImageUtils.find_button(
                    "attack", tries = 1, suppress_error = True
                ) is not None
                if attack_visible and not wipe_still_visible and not continue_visible:
                    MessageLog.print_message(
                        "[SUCCESS] Full Elixir use verified from the restored battle controls."
                    )
                    return True

            if attempt < 9:
                Game.wait(0.5)

        MessageLog.print_message(
            "[WARNING] Could not confirm Full Elixir use (it may be unavailable). "
            "Falling back to Home recovery."
        )
        return False

    @staticmethod
    def _check_for_wipe():
        """Check to see if the Party has wiped during Combat Mode. Update the retreat check flag if so.

        Returns:
            None
        """
        from bot.game import Game

        # Check to see if Party has wiped.
        if Settings.debug_mode:
            MessageLog.print_message(f"\n[DEBUG] Checking to see if the Party wiped...")

        party_wipe_indicator = None
        wipe_detected = False

        # Fast DOM check first if DOM clicking is enabled
        if getattr(Settings, "enable_dom_clicking", False):
            try:
                from bot.dom_clicker import DomClicker
                if DomClicker.element_exists("party_wipe_indicator") or DomClicker.element_exists("salute_participants"):
                    wipe_detected = True
            except Exception:
                pass

        # Fallback to image-matching only if DOM check did not detect wipe AND
        # either DOM clicking is disabled or throttled every 4 iterations to save CPU/disk time.
        if not wipe_detected:
            CombatMode._wipe_check_counter += 1
            need_image_check = not getattr(Settings, "enable_dom_clicking", False) or (CombatMode._wipe_check_counter % 4 == 0)
            if need_image_check:
                party_wipe_indicator = ImageUtils.find_button("party_wipe_indicator", tries = 1, suppress_error = True)
                if party_wipe_indicator is not None or ImageUtils.confirm_location("salute_participants", tries = 1, suppress_error = True):
                    wipe_detected = True

        if wipe_detected:
            CombatMode._wipe_check_counter = 0
            if Settings.farming_mode == "Raid":
                if not CombatMode._revive_raid_party_with_elixir(party_wipe_indicator):
                    Game.go_back_home(confirm_location_check = True)
                    CombatMode._retreat_check = True
            elif (Settings.farming_mode != "Dread Barrage") and ImageUtils.confirm_location("continue"):
                # Click on the blue indicator to get rid of the overlay.
                if party_wipe_indicator is not None:
                    MouseUtils.move_and_click_point(party_wipe_indicator[0], party_wipe_indicator[1], "party_wipe_indicator")
                else:
                    Game.find_and_click_button("party_wipe_indicator", suppress_error = True)

                MessageLog.print_message(f"[WARNING] Party has unfortunately wiped during Combat Mode for this non-Raid battle. Retreating now...")

                # Cancel the popup that asks you if you want to use a Full Elixir to come back. Then click the red "Retreat" button.
                Game.find_and_click_button("cancel")
                Game.find_and_click_button("retreat_confirmation")
                CombatMode._retreat_check = True
            elif Settings.farming_mode == "Dread Barrage" or Settings.farming_mode == "Guild Wars" or Settings.map_name.__contains__("Raid"):
                MessageLog.print_message(f"[WARNING] Party has unfortunately wiped during Combat Mode for this Raid battle. Backing out now without retreating...")

                # Head back to the Home screen.
                Game.go_back_home(confirm_location_check = True)
                CombatMode._retreat_check = True
            elif Settings.farming_mode == "Coop" and (ImageUtils.confirm_location("salute_participants") or (getattr(Settings, "enable_dom_clicking", False) and DomClicker.element_exists("salute_participants"))):
                # Click on the blue indicator to get rid of the overlay.
                if party_wipe_indicator is not None:
                    MouseUtils.move_and_click_point(party_wipe_indicator[0], party_wipe_indicator[1], "party_wipe_indicator")

                # Salute the participants.
                MessageLog.print_message(f"[WARNING] Party has unfortunately wiped during Combat Mode for this Coop battle. Leaving the Coop room...")
                Game.find_and_click_button("salute")
                Game.find_and_click_button("ok")

                # Then cancel the popup that asks you if you want to use a Full Elixir to come back.
                Game.find_and_click_button("cancel")

                # Then click the "Leave" button.
                Game.find_and_click_button("leave")

                CombatMode._retreat_check = True
        elif Settings.debug_mode:
            MessageLog.print_message(f"[DEBUG] Party has not wiped.")

        return None

    @staticmethod
    def _check_for_dialog():
        """Check if there are dialog popups from either Lyria or Vyrn and click them away.

        Returns:
            None
        """
        dialog_location = ImageUtils.find_button("dialog_lyria", tries = 2, suppress_error = True, bypass_general_adjustment = True)
        if dialog_location is None:
            dialog_location = ImageUtils.find_button("dialog_vyrn", tries = 2, suppress_error = True, bypass_general_adjustment = True)

        if dialog_location is not None:
            if Settings.use_first_notch is False:
                MouseUtils.move_and_click_point(dialog_location[0] + 180, dialog_location[1] - 50, "template_dialog")
            else:
                MouseUtils.move_and_click_point(dialog_location[0] + 130, dialog_location[1] - 40, "template_dialog")

        return None

    @staticmethod
    def _detect_battle_concluded_via_dom() -> bool:
        """Fallback detection for the "Battle Concluded" popup using page text instead of image template
        matching. This exists because the battle_concluded template image can silently go stale (game UI
        updates, resolution changes, etc.) and produce a consistently low confidence score that never
        crosses the match threshold, which otherwise leaves the bot stuck passively waiting forever since
        _check_for_battle_end() would keep returning "Nothing".

        Returns:
            (bool): True if the page text matches the "Battle Concluded" popup's wording. False otherwise
            (including if the DOM could not be read, e.g. CDP unavailable).
        """
        from bot.game import Game

        detected = Game.evaluate_dom_js("""(() => {
            let text = document.body ? (document.body.innerText || '') : '';
            if (text.includes('Battle Concluded') || text.includes('battle has ended') ||
                text.includes('already ended') || text.includes('foe was defeated') ||
                text.includes('The battle has ended') || text.includes('終了しました') ||
                text.includes('終了しています') || text.includes('すでに終了している')) {
                return true;
            }
            let popHeader = document.querySelector('.prt-popup-header, .pop-title, .txt-popup-title');
            if (popHeader && popHeader.offsetParent !== null) {
                let ht = (popHeader.innerText || '').trim();
                if (ht.includes('Concluded') || ht.includes('Result') || ht.includes('終了')) return true;
            }
            let popBody = document.querySelector('.prt-popup-body, .txt-popup-body, .pop-usual');
            if (popBody && popBody.offsetParent !== null) {
                let bt = (popBody.innerText || '').trim();
                if (bt.includes('Concluded') || bt.includes('already ended') || bt.includes('battle has ended') ||
                    bt.includes('終了しています') || bt.includes('終了しました') || bt.includes('すでに終了')) return true;
            }
            return false;
        })()""")
        return bool(detected)

    @staticmethod
    def _is_boss_defeated_via_dom() -> bool:
        """Check if enemy HP is 0% or victory screen is active via DOM."""
        from bot.game import Game
        res = Game.evaluate_dom_js("""(() => {
            // 1. Victory / result banner
            let win = document.querySelector('.prt-result-head, .prt-result-win, .prt-quest-win, .prt-win');
            if (win && win.offsetParent !== null) return true;

            // 2. Enemy percentage displays
            let percents = document.querySelectorAll('.prt-enemy-percent, .prt-percent-num');
            if (percents.length > 0) {
                let allZero = true;
                for (let el of percents) {
                    let txt = (el.innerText || el.textContent || '').trim();
                    if (txt !== '0%' && txt !== '0') {
                        allZero = false;
                        break;
                    }
                }
                if (allZero) return true;
            }

            // 3. Game stage status
            if (window.stage && window.stage.gGameStatus && window.stage.gGameStatus.boss) {
                let boss = window.stage.gGameStatus.boss;
                if (boss.param && boss.param.length > 0) {
                    let alive = boss.param.some(p => p.alive !== 0 && p.hp > 0);
                    if (!alive) return true;
                }
            }

            return false;
        })()""")
        return bool(res)

    @staticmethod
    def _check_for_battle_end() -> str:
        """Perform checks to see if the battle ended or not.

        Returns:
            (str): Return "Nothing" if combat is still continuing. Otherwise, raise a CombatModeException whose message is the event name that caused the battle to end.
        """
        from bot.game import Game
        from bot.dom_clicker import DomClicker

        # Fast URL hash and DOM check for Quest Result screen (only after at least 5s of battle).
        # Granblue Fantasy's router updates window.location.hash to '#result...' when battle ends.
        if time.time() - CombatMode._start_time >= 5.0:
            result_detected = Game.evaluate_dom_js("""(() => {
                let hash = window.location.hash || '';
                if (hash.includes('no_loot')) {
                    return 'no_loot';
                }
                if (hash.startsWith('#result')) {
                    return 'result_url';
                }
                let resultEl = document.querySelector('.prt-result-head, .cnt-result');
                if (resultEl && resultEl.offsetParent !== null) {
                    return 'result_dom';
                }
                return null;
            })()""")
            if result_detected == 'no_loot':
                MessageLog.print_message("\n[COMBAT] Battle ended with no loot (detected no_loot in URL).")
                MessageLog.print_message("\n######################################################################")
                MessageLog.print_message("######################################################################")
                MessageLog.print_message("[COMBAT] Combat Mode has ended with no loot.")
                MessageLog.print_message("######################################################################")
                MessageLog.print_message("######################################################################")
                raise CombatModeException("No Loot")
            elif result_detected:
                MessageLog.print_message(f"\n[COMBAT] Battle ended (detected {result_detected}).")
                MessageLog.print_message("\n######################################################################")
                MessageLog.print_message("######################################################################")
                MessageLog.print_message("[COMBAT] Ending Combat Mode.")
                MessageLog.print_message("######################################################################")
                MessageLog.print_message("######################################################################")
                raise CombatModeException("Exp Gained")

        # Check if the Battle has ended.
        if Settings.farming_mode == "Raid" and Settings.enable_auto_exit_raid and time.time() - CombatMode._start_time >= Settings.time_allowed_until_auto_exit_raid:
            MessageLog.print_message("\n######################################################################")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("[COMBAT] Combat Mode ended due to exceeding time allowed.")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("######################################################################")
            raise CombatModeException("Time Exceeded")
        elif CombatMode._retreat_check or DomClicker.element_exists("no_loot") or ImageUtils.confirm_location("no_loot", tries = 1, suppress_error = True, bypass_general_adjustment = True):
            MessageLog.print_message("\n######################################################################")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("[COMBAT] Combat Mode has ended with no loot.")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("######################################################################")
            raise CombatModeException("No Loot")
        elif CombatMode._detect_battle_concluded_via_dom() or ImageUtils.confirm_location("battle_concluded", tries = 1, suppress_error = True, bypass_general_adjustment = True):
            MessageLog.print_message("\n[COMBAT] Battle concluded suddenly (foe was defeated by other players).")
            MessageLog.print_message("\n######################################################################")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("[COMBAT] Ending Combat Mode.")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("######################################################################")
            # Dismiss the "Battle Concluded" popup by clicking the OK button.
            # Previously this incorrectly called find_and_click_button("reload") which
            # does not match the popup's OK button, leaving the bot stuck at the popup.
            if Game.find_and_click_button("ok", tries = 5, suppress_error = True):
                MessageLog.print_message("[COMBAT] Dismissed 'Battle Concluded' popup (clicked OK).")
                # Wait for the game to navigate to the Quest Results / no-loot screen.
                Game.wait(3.0)
            else:
                MessageLog.print_message("[COMBAT] Could not find OK button on 'Battle Concluded' popup. Attempting reload as fallback.")
                Game.find_and_click_button("reload")
                Game.wait(3.0)
            raise CombatModeException("Battle Concluded")
        elif DomClicker.element_exists("exp_gained") or ImageUtils.confirm_location("exp_gained", tries = 1, suppress_error = True, bypass_general_adjustment = True):
            MessageLog.print_message("\n######################################################################")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("[COMBAT] Ending Combat Mode.")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("######################################################################")
            raise CombatModeException("Exp Gained")
        elif DomClicker.element_exists("loot_collected") or ImageUtils.confirm_location("loot_collected", tries = 1, suppress_error = True, bypass_general_adjustment = True):
            MessageLog.print_message("\n######################################################################")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("[COMBAT] Ending Combat Mode.")
            MessageLog.print_message("######################################################################")
            MessageLog.print_message("######################################################################")
            raise CombatModeException("Loot Collected")
        else:
            return "Nothing"

    @staticmethod
    def _check_raid() -> bool:
        """Check if the current battle is a raid-like battle.

        Returns:
            (bool): True if the current battle is a raid-like battle.
        """
        event_raids = ["VH Event Raid", "EX Event Raid", "IM Event Raid"]
        rotb_raids = ["EX Zhuque", "EX Xuanwu", "EX Baihu", "EX Qinglong", "Lvl 100 Shenxian", "Lvl 150 Shenxian"]
        dread_barrage_raids = ["1 Star", "2 Star", "3 Star", "4 Star", "5 Star"]
        proving_grounds_raids = ["Extreme", "Extreme+"]
        guild_wars_raids = ["Very Hard", "Extreme", "Extreme+", "NM90", "NM95", "NM100", "NM150"]

        if Settings.farming_mode == "Raid" or \
                event_raids.__contains__(Settings.mission_name) or \
                rotb_raids.__contains__(Settings.mission_name) or \
                dread_barrage_raids.__contains__(Settings.mission_name) or \
                (Settings.farming_mode == "Proving Grounds" and proving_grounds_raids.__contains__(Settings.mission_name)) or \
                (Settings.farming_mode == "Guild Wars" and guild_wars_raids.__contains__(Settings.mission_name)) or \
                Settings.farming_mode == "Arcarum" or Settings.farming_mode == "Arcarum Sandbox":
            return True
        else:
            return False

    ######################################################################
    ######################################################################
    # Helper Methods
    ######################################################################
    ######################################################################

    @staticmethod
    def _select_character(character_number: int):
        """Selects the portrait of the character specified on the Combat screen.

        Args:
            character_number (int): The character that needs to be selected on the Combat screen (1-4).

        Returns:
            None
        """
        from bot.game import Game

        if character_number < 1 or character_number > 4:
            MessageLog.print_message(f"[WARNING] Invalid command received for selecting a Character #{character_number}.")
            return None

        # 1. Attempt DOM click on character portrait (.lis-character0..3)
        dom_selected = Game.evaluate_dom_js(f"""(() => {{
            let c = document.querySelector('.lis-character{character_number - 1}');
            if (c && c.offsetParent !== null) {{
                ['touchstart', 'touchend', 'mousedown', 'mouseup', 'click'].forEach(evt => {{
                    try {{
                        let e = new MouseEvent(evt, {{bubbles: true, cancelable: true, view: window}});
                        c.dispatchEvent(e);
                    }} catch(e) {{}}
                }});
                if (window.$) {{ try {{ $(c).trigger('tap'); }} catch(e) {{}} }}
                try {{ c.click(); }} catch(e) {{}}
                return true;
            }}
            return false;
        }})()""")

        # 2. Coordinate calculation for physical click
        if Settings.use_first_notch is False:
            # Notch 2: Character 1 is 409px left of Attack center, spaced by 75px
            x_offset = 409
            x_inc = 75
            y_offset = 111
        else:
            x_offset = 275
            x_inc = 50
            y_offset = 75

        x = CombatMode._attack_button_location[0] - x_offset + (x_inc * (character_number - 1))
        y = CombatMode._attack_button_location[1] + y_offset

        # Double-click the character portrait
        MouseUtils.move_and_click_point(x, y, "template_character", mouse_clicks = 2)

        return None

    @staticmethod
    def _reload_for_attack(override: bool = False) -> bool:
        """Determine whether or not to reload after an Attack.

        Args:
            override (bool): Override the set checks and reload anyways. Defaults to false.

        Returns:
            (bool): True if the bot reloaded the page. False otherwise.
        """
        # If the "Cancel" button vanishes, that means the attack is in-progress. Now reload the page and wait for either the attack to finish or Battle ended.
        if Settings.enable_refresh_during_combat and (CombatMode._check_raid() or override or (Settings.farming_mode == "Generic" and Settings.enable_force_reload)):
            from bot.game import Game

            if CombatMode._check_for_battle_end() == "Nothing":
                MessageLog.print_message("[COMBAT] Reloading now.")
                Game.find_and_click_button("reload")

                if Settings.enable_combat_mode_adjustment:
                    Game.wait(Settings.adjust_waiting_for_reload)
                else:
                    Game.wait(3.0)

                return True

        return False

    @staticmethod
    def _process_incorrect_turn():
        """Processes the current turn manually in order to get the bot to the expected turn number.

        Returns:
            None
        """
        from bot.game import Game

        # Clear any detected dialog popups that might obstruct the "Attack" button.
        CombatMode._check_for_dialog()

        # Wait for the Attack to process.
        MessageLog.print_message(f"[COMBAT] Ending Turn {CombatMode._turn_number}...")
        if CombatMode._full_auto is False and CombatMode._semi_auto is False:
            Game.find_and_click_button("attack", tries = 30)
            while ImageUtils.find_button("cancel", suppress_error = True) is not None:
                if Settings.debug_mode:
                    MessageLog.print_message("[DEBUG] While waiting for the incorrect turn to process, the \"Cancel\" button has not vanished from the screen yet.")
                Game.wait(1.0)
        else:
            while ImageUtils.find_button("attack", suppress_error = True) is not None:
                if Settings.debug_mode:
                    MessageLog.print_message("[DEBUG] While waiting for the incorrect turn to process, the \"Attack\" button has not vanished from the screen yet.")
                Game.wait(1.0)

        reload_check = False

        # If the next Turn is the current Turn block, turn off auto.
        if CombatMode._turn_number + 1 == CombatMode._command_turn_number:
            reload_check = CombatMode._reload_for_attack()
            if reload_check is False:
                if CombatMode._full_auto:
                    MouseUtils.scroll_screen_from_home_button(0)  # Move the cursor if it is hovering over the Full/Semi Auto button.
                    Game.find_and_click_button("full_auto_enabled", tries = 10)
                elif CombatMode._semi_auto:
                    MouseUtils.scroll_screen_from_home_button(0)  # Move the cursor if it is hovering over the Full/Semi Auto button.
                    Game.find_and_click_button("semi_auto_enabled", tries = 10)

            CombatMode._full_auto = False
            CombatMode._semi_auto = False

        Game.wait(1.0)

        # If the bot reloaded the page, determine if bot needs to enable Full/Semi Auto again.
        if reload_check is False:
            reload_check = CombatMode._reload_for_attack()
            if reload_check and CombatMode._full_auto:
                CombatMode._enable_full_auto()
            elif reload_check and CombatMode._semi_auto:
                CombatMode._enable_semi_auto()

        CombatMode._wait_for_attack()

        MessageLog.print_message(f"[COMBAT] Turn {CombatMode._turn_number} has ended.")

        if Game.find_and_click_button("next", tries = 3, suppress_error = True):
            Game.wait(3)

        CombatMode._turn_number += 1

        MessageLog.print_message(f"\n[COMBAT] Starting Turn {CombatMode._turn_number}.")

        return None

    @staticmethod
    def _wait_for_attack() -> bool:
        """Wait for several tries until the bot sees either the Attack or the Next button before starting a new turn.

        Returns:
            (bool): True if Attack ended into the next Turn. False if Attack ended but combat also ended as well.
        """
        from bot.game import Game

        MessageLog.print_message("[COMBAT] Now waiting for attack to end...")
        if Settings.enable_combat_mode_adjustment:
            tries = Settings.adjust_waiting_for_attack
        else:
            tries = 100

        while tries > 0 and not CombatMode._retreat_check and ImageUtils.find_button("attack", tries = 1, suppress_error = True) is None and \
                ImageUtils.find_button("next", tries = 1, suppress_error = True) is None:
            CombatMode._check_for_dialog()

            # Check if the Party wiped after attacking.
            CombatMode._check_for_wipe()

            CombatMode._check_for_battle_end()

            tries -= 1
            if tries > 0:
                Game.wait(0.2)

        MessageLog.print_message("[COMBAT] Attack ended.")

        return True

    @staticmethod
    def _enable_auto() -> bool:
        """Enable Full/Semi auto for this battle.

        Returns:
            (bool): True if Full/Semi auto is enabled.
        """
        from bot.game import Game

        if Settings.enable_refresh_during_combat and Settings.enable_auto_quick_summon:
            MessageLog.print_message(f"[COMBAT] Automatically attempting to use Quick Summon...")
            CombatMode._quick_summon()

        enable_auto = Game.find_and_click_button("full_auto") or ImageUtils.find_button("full_auto_enabled")

        # If the bot failed to find and click the "Full Auto" button, fallback to the "Semi Auto" button.
        if enable_auto is False:
            MessageLog.print_message(f"[COMBAT] Failed to find the \"Full Auto\" button. Falling back to Semi Auto.")
            MessageLog.print_message(f"[COMBAT] Double checking to see if Semi Auto is enabled.")

            enabled_semi_auto_button_location = ImageUtils.find_button("semi_button_enabled")
            if enabled_semi_auto_button_location is None:
                # Have the Party attack and then attempt to see if the "Semi Auto" button becomes visible.
                Game.find_and_click_button("attack")

                Game.wait(2.0)

                enable_auto = Game.find_and_click_button("semi_auto", tries = 10)
                if enable_auto:
                    MessageLog.print_message("[COMBAT] Semi Auto is now enabled.")
        else:
            MessageLog.print_message(f"[COMBAT] Enabled Full Auto.")

        return enable_auto

    ######################################################################
    ######################################################################
    # Commands
    ######################################################################
    ######################################################################

    @staticmethod
    def _start_turn(command: str):
        """Start the Turn based on the read command and move the internal Turn count forward to match the command.

        Args:
            command (str): The command to execute.

        Returns:
            None
        """
        # Clear any detected dialog popups that might obstruct the "Attack" button.
        CombatMode._check_for_dialog()

        # Parse the Turn's number.
        CombatMode._command_turn_number = int(command.split(":")[0].split(" ")[1])

        # If the command is a "Turn #:" and it is currently not the correct Turn, attack until the Turn numbers match.
        if CombatMode._retreat_check is False and CombatMode._turn_number != CombatMode._command_turn_number:
            MessageLog.print_message(f"[COMBAT] Attacking until the bot reaches Turn {CombatMode._command_turn_number}.")
            while CombatMode._turn_number != CombatMode._command_turn_number:
                CombatMode._process_incorrect_turn()
        else:
            MessageLog.print_message(f"\n[COMBAT] Starting Turn {CombatMode._turn_number}.")

        return None

    @staticmethod
    def _end_turn():
        """Ends the Turn by clicking the Attack button.

        Returns:
            None
        """
        from bot.game import Game

        # Click the "Attack" button once every command inside the Turn Block has been processed.
        MessageLog.print_message(f"[COMBAT] Ending Turn {CombatMode._turn_number}...")

        if CombatMode._full_auto or CombatMode._semi_auto:
            while ImageUtils.find_button("attack") is not None:
                Game.wait(1.0)
        else:
            Game.find_and_click_button("attack", tries = 10)

            # Wait until the "Cancel" button vanishes from the screen.
            if ImageUtils.find_button("combat_cancel", tries = 10) is not None:
                while ImageUtils.wait_vanish("combat_cancel", timeout = 5, suppress_error = True) is False:
                    if Settings.debug_mode:
                        MessageLog.print_message("[DEBUG] The \"Cancel\" button has not vanished from the screen yet.")
                    Game.wait(1.0)

        # Check for exit conditions.
        CombatMode._check_for_battle_end()

        if Game.find_and_click_button("next", tries = 3, suppress_error = True):
            Game.wait(3)

        return None

    @staticmethod
    def _wait_execute(command_list: List[str], fallback_delay: float = 1.0):
        """Execute a wait command.

        Args:
            command_list (List[str]): A split list of the command by its "." delimiter with the "wait" command being the first element.
            fallback_delay (float): A default delay if the wait command was invalid. Defaults to 1.0 second.

        Returns:
            None
        """
        from bot.game import Game

        # Isolate the seconds inside the command.
        if command_list[0].__contains__(")"):
            wait_command: str = command_list[0].split("(")[1].replace(")", "")
        else:
            wait_command: str = command_list[0].split("(")[1] + "." + command_list[1].replace(")", "")

        try:
            wait_seconds: float = float(wait_command)
            MessageLog.print_message(f"[COMBAT] Now waiting {wait_seconds} second(s).")
            Game.wait(wait_seconds)
        except ValueError:
            MessageLog.print_message(f"[COMBAT] Could not parse out the seconds in the wait command. Waiting {fallback_delay} second(s) as fallback.")
            Game.wait(fallback_delay)

    @staticmethod
    def _use_combat_healing_item(command: str):
        """Uses the specified healing item during Combat mode with an optional target if the item needs it.

        Args:
            command (str): The command for the healing item to use.

        Returns:
            None
        """
        from bot.game import Game

        if Settings.debug_mode:
            MessageLog.print_message(f"\n[DEBUG] Using item: {command}.")

        target = 0

        # Grab the healing command.
        healing_item_command_list = command.split(".")
        healing_item_command = healing_item_command_list.pop(0)

        # Parse the target if the user is using a Green Potion or a Clarity Herb.
        if (healing_item_command == "usegreenpotion" or healing_item_command == "useclarityherb") and healing_item_command_list[0].__contains__("target"):
            if healing_item_command_list[0] == "target(1)":
                target = 1
            elif healing_item_command_list[0] == "target(2)":
                target = 2
            elif healing_item_command_list[0] == "target(3)":
                target = 3
            elif healing_item_command_list[0] == "target(4)":
                target = 4

        # Click on the green "Heal" button.
        Game.find_and_click_button("heal")

        # Format the item name from the command.
        formatted_command = command.replace(" ", "_")

        # Click the specified item.
        if formatted_command == "usebluepotion" or formatted_command == "usesupportpotion":
            # Blue and Support Potions share the same image but are at different positions on the screen.
            potion_locations = ImageUtils.find_all(formatted_command)

            if command == "usebluepotion":
                MouseUtils.move_and_click_point(potion_locations[0][0], potion_locations[0][1], "usebluepotion")
            elif command == "usesupportpotion":
                MouseUtils.move_and_click_point(potion_locations[1][0], potion_locations[1][1], "usesupportpotion")
        else:
            Game.find_and_click_button(formatted_command)

        # After the initial popup vanishes to reveal a new popup, either select a Character target or confirm the item usage.
        if ImageUtils.wait_vanish("tap_the_item_to_use", timeout = 5):
            if command == "usegreenpotion":
                MessageLog.print_message(f"\n[COMBAT] Using Green Potion on Character {target}...")
                CombatMode._select_character(target)
            elif command == "usebluepotion":
                MessageLog.print_message(f"\n[COMBAT] Using Blue Potion on the whole Party...")
                Game.find_and_click_button("use")
            elif command == "usefullelixir":
                MessageLog.print_message(f"\n[COMBAT] Using Full Elixir to revive and gain Full Charge...")
                Game.find_and_click_button("ok")
            elif command == "usesupportpotion":
                MessageLog.print_message(f"\n[COMBAT] Using Support Potion on the whole Party...")
                Game.find_and_click_button("ok")
            elif command == "useclarityherb":
                MessageLog.print_message(f"\n[COMBAT] Using Clarity Herb on Character {target}...")
                CombatMode._select_character(target)
            elif command == "userevivalpotion":
                MessageLog.print_message(f"\n[COMBAT] Using Revival Potion to revive the whole Party...")
                Game.find_and_click_button("ok")

            # Wait for the healing animation to finish.
            Game.wait(1)

            if not ImageUtils.confirm_location("use_item", tries = 5):
                MessageLog.print_message(f"[SUCCESS] Using healing item was successful.")
            else:
                MessageLog.print_message(f"[WARNING] Using healing item was not successful. Canceling it now...")
                Game.find_and_click_button("cancel")
        else:
            MessageLog.print_message(f"[WARNING] Failed to click on the item. Either it does not exist for this particular mission or you ran out. Canceling it now...")
            Game.find_and_click_button("cancel")

        return None

    @staticmethod
    def _request_backup():
        """Request backup during a Raid.

        Returns:
            None
        """
        from bot.game import Game

        MessageLog.print_message(f"\n[COMBAT] Now requesting Backup for this Raid.")

        # Scroll down the screen a little bit to have the "Request Backup" button visible on all screen sizes and then click it.
        tries = 5
        while Game.find_and_click_button("request_backup") is False:
            MouseUtils.scroll_screen_from_home_button(-200)
            tries -= 1
            if tries <= 0:
                MessageLog.print_message(f"\n[COMBAT] Failed to request backup.")
                MouseUtils.scroll_screen_from_home_button(400)
                return None

        Game.wait(1)

        # Find the location of the "Cancel" button and then click the button right next to it. This is to ensure that no matter what the blue "Request Backup" button's appearance, it is ensured to be pressed.
        cancel_button_location = ImageUtils.find_button("cancel")
        if cancel_button_location is not None:
            MouseUtils.move_and_click_point(cancel_button_location[0] + 200, cancel_button_location[1], "cancel")

        Game.wait(1)

        # If requesting backup was successful, click "OK" to close the popup.
        if ImageUtils.confirm_location("request_backup_success", tries = 5):
            MessageLog.print_message(f"[COMBAT] Successfully requested Backup.")
            Game.find_and_click_button("ok")
        else:
            MessageLog.print_message(f"[COMBAT] Unable to request Backup. Possibly because it is still on cooldown.")
            Game.find_and_click_button("cancel")

        # Move the view back up to the top of the page to ensure all elements are visible.
        MouseUtils.scroll_screen_from_home_button(400)

        return None

    @staticmethod
    def _tweet_backup():
        """Request backup during a Raid using Twitter.

        Returns:
            None
        """
        # TODO: Remove this as Twitter functionality is now removed.
        # TODO: Update the Wiki by removing this command as well.

        from bot.game import Game

        MessageLog.print_message(f"\n[COMBAT] Now requesting Backup for this Raid via Twitter.")

        # Scroll down the screen a little bit to have the "Request Backup" button visible on all screen sizes and then click it.
        MouseUtils.scroll_screen_from_home_button(-400)
        Game.find_and_click_button("request_backup")

        Game.wait(1)

        # Then click the "Tweet" button.
        Game.find_and_click_button("request_backup_tweet")
        Game.find_and_click_button("ok")

        Game.wait(1)

        # If requesting backup via Twitter was successful, click "OK" to close the popup. Otherwise, click "Cancel".
        if ImageUtils.confirm_location("request_backup_tweet_success", tries = 5):
            MessageLog.print_message(f"[COMBAT] Successfully requested Backup via Twitter.")
            Game.find_and_click_button("ok")
        else:
            MessageLog.print_message(f"[COMBAT] Failed requesting Backup via Twitter as there is still a cooldown from the last tweet.")
            Game.find_and_click_button("cancel")

        # Move the view back up to the top of the page to ensure all elements are visible.
        MouseUtils.scroll_screen_from_home_button(400)

        return None

    @staticmethod
    def _select_enemy_target(command: str):
        """Selects the targeted enemy.

        Args:
            command (str): The command to be executed.

        Returns:
            None
        """
        for target in range(1, 3):
            if command == f"targetenemy({target})":
                from bot.game import Game

                if Settings.use_first_notch is False:
                    x_offset = 270
                    x_inc = 160
                    y_offset = 285
                else:
                    x_offset = 175
                    x_inc = 100
                    y_offset = 190

                if target == 1:
                    x = CombatMode._attack_button_location[0] - x_offset + (x_inc * 0)
                elif target == 2:
                    x = CombatMode._attack_button_location[0] - x_offset + (x_inc * 1)
                else:
                    x = CombatMode._attack_button_location[0] - x_offset + (x_inc * 2)

                y = CombatMode._attack_button_location[1] - y_offset

                MouseUtils.move_and_click_point(x, y, "template_enemy_target")
                Game.find_and_click_button("set_target")
                MessageLog.print_message(f"[COMBAT] Targeted Enemy #{target}.")

        return None

    @staticmethod
    def _use_character_skill(character_selected: int, skill_command_list: List[str]):
        """Activate the specified skill(s) for the already selected character.

        Args:
            character_selected (int): The selected character whose skill(s) needs to be used.
            skill_command_list (List[str]): The commands to be executed.

        Returns:
            (bool): Return True if the Turn will end due to a chained "attack" command. False otherwise.
        """
        from bot.game import Game

        # Execute every skill command in the list.
        while len(skill_command_list) > 0:
            # Stop if the Next button is present.
            if ImageUtils.find_button("next", tries = 1, suppress_error = True):
                return False

            if skill_command_list[0].__contains__("wait"):
                CombatMode._wait_execute(skill_command_list)
                skill_command_list.pop(0)
            elif skill_command_list[0].__contains__("attack"):
                CombatMode._end()
                return True
            else:
                skill = skill_command_list.pop(0)

                if Settings.use_first_notch is False:
                    # Notch 2: measured from DOM — Skill 1 is 286px left of Attack center, spaced by 106px
                    x_offset = 286
                    x_inc = 106
                    y_offset = 201
                else:
                    x_offset = 250
                    x_inc = 55
                    y_offset = 115

                if skill == "useskill(1)":
                    MessageLog.print_message(f"[COMBAT] Character {character_selected} uses Skill 1.")
                    x = CombatMode._attack_button_location[0] - x_offset + (x_inc * 0)
                elif skill == "useskill(2)":
                    MessageLog.print_message(f"[COMBAT] Character {character_selected} uses Skill 2.")
                    x = CombatMode._attack_button_location[0] - x_offset + (x_inc * 1)
                elif skill == "useskill(3)":
                    MessageLog.print_message(f"[COMBAT] Character {character_selected} uses Skill 3.")
                    x = CombatMode._attack_button_location[0] - x_offset + (x_inc * 2)
                elif skill == "useskill(4)":
                    MessageLog.print_message(f"[COMBAT] Character {character_selected} uses Skill 4.")
                    x = CombatMode._attack_button_location[0] - x_offset + (x_inc * 3)
                else:
                    MessageLog.print_message(f"[WARNING] Invalid command received for using the Character's Skill. User wanted: {skill}.")
                    Game.find_and_click_button("back")
                    return False

                y = CombatMode._attack_button_location[1] + y_offset

                MouseUtils.move_and_click_point(x, y, "template_skill")

                # Check if the skill requires a target.
                if len(skill_command_list) > 0 and ImageUtils.confirm_location("use_skill", bypass_general_adjustment = True):
                    MessageLog.print_message(f"[COMBAT] Skill is awaiting a target...")
                    target = skill_command_list.pop(0)

                    if Settings.use_first_notch is False:
                        x_offset = 225
                        x_inc = 95
                        y_offset = 55
                        y_inc = 70
                    else:
                        x_offset = 150
                        x_inc = 60
                        y_offset = 35
                        y_inc = 110

                    if target == 1:
                        x = CombatMode._attack_button_location[0] - x_offset + (x_inc * 0)
                    elif target == 2:
                        x = CombatMode._attack_button_location[0] - x_offset + (x_inc * 1)
                    else:
                        x = CombatMode._attack_button_location[0] - x_offset + (x_inc * 2)

                    if target == 1 or target == 2 or target == 3:
                        y = CombatMode._attack_button_location[1] - y_offset + (y_inc * 0)
                    else:
                        y = CombatMode._attack_button_location[1] - y_offset + (y_inc * 1)

                    if target == "target(1)":
                        MessageLog.print_message("[COMBAT] Targeting Character 1 for Skill.")
                        MouseUtils.move_and_click_point(x, y, "template_target")
                    elif "target(2)" in target:
                        MessageLog.print_message("[COMBAT] Targeting Character 2 for Skill.")
                        MouseUtils.move_and_click_point(x, y, "template_target")
                    elif "target(3)" in target:
                        MessageLog.print_message("[COMBAT] Targeting Character 3 for Skill.")
                        MouseUtils.move_and_click_point(x, y, "template_target")
                    elif "target(4)" in target:
                        MessageLog.print_message("[COMBAT] Targeting Character 4 for Skill.")
                        MouseUtils.move_and_click_point(x, y, "template_target")
                    elif "target(5)" in target:
                        MessageLog.print_message("[COMBAT] Targeting Character 5 for Skill.")
                        MouseUtils.move_and_click_point(x, y, "template_target")
                    elif "target(6)" in target:
                        MessageLog.print_message("[COMBAT] Targeting Character 6 for Skill.")
                        MouseUtils.move_and_click_point(x, y, "template_target")
                    elif "wait" in target:
                        CombatMode._wait_execute(list(target))
                    else:
                        MessageLog.print_message("[WARNING] Invalid command received for Skill targeting.")
                        Game.find_and_click_button("cancel")

                # Else, check if the character is skill-sealed.
                elif ImageUtils.confirm_location("skill_unusable", bypass_general_adjustment = True):
                    MessageLog.print_message("[COMBAT] Character is currently skill-sealed. Unable to execute command.")
                    Game.find_and_click_button("cancel")

        # Once all the commands for the selected Character have been processed, click the "Back" button to return.
        Game.find_and_click_button("back")

        return False

    @staticmethod
    def _use_summon(command: str):
        """Activate the specified Summon.

        Args:
            command (str): The command to be executed.

        Returns:
            (bool): Return True if the Turn will end due to a chained "attack" command. False otherwise.
        """
        for summon_index in range(1, 7):
            if f"summon({summon_index})" in command:
                from bot.game import Game

                # Click the "Summon" button to bring up the available Summons.
                MessageLog.print_message(f"[COMBAT] Invoking Summon #{summon_index}.")
                Game.find_and_click_button("summon")

                if Settings.use_first_notch is False:
                    x_offset = 320
                    x_inc = 75
                    y_offset = 140
                else:
                    x_offset = 215
                    x_inc = 50
                    y_offset = 90

                # Click on the specified Summon.
                tries = 3
                while ImageUtils.confirm_location("summon_details") is False:
                    if summon_index == 1:
                        MouseUtils.move_and_click_point(CombatMode._attack_button_location[0] - x_offset + (x_inc * 0), CombatMode._attack_button_location[1] + y_offset, "template_summon")
                    elif summon_index == 2:
                        MouseUtils.move_and_click_point(CombatMode._attack_button_location[0] - x_offset + (x_inc * 1), CombatMode._attack_button_location[1] + y_offset, "template_summon")
                    elif summon_index == 3:
                        MouseUtils.move_and_click_point(CombatMode._attack_button_location[0] - x_offset + (x_inc * 2), CombatMode._attack_button_location[1] + y_offset, "template_summon")
                    elif summon_index == 4:
                        MouseUtils.move_and_click_point(CombatMode._attack_button_location[0] - x_offset + (x_inc * 3), CombatMode._attack_button_location[1] + y_offset, "template_summon")
                    elif summon_index == 5:
                        MouseUtils.move_and_click_point(CombatMode._attack_button_location[0] - x_offset + (x_inc * 4), CombatMode._attack_button_location[1] + y_offset, "template_summon")
                    else:
                        MouseUtils.move_and_click_point(CombatMode._attack_button_location[0] - x_offset + (x_inc * 5), CombatMode._attack_button_location[1] + y_offset, "template_summon")

                    tries -= 1

                # Check if it is able to be summoned.
                if ImageUtils.confirm_location("summon_details", bypass_general_adjustment = True):
                    if Game.find_and_click_button("ok") is False:
                        MessageLog.print_message(f"[COMBAT] Summon #{summon_index} cannot be invoked due to current restrictions.")
                        Game.find_and_click_button("cancel")

                # Click the "Back" button to return.
                Game.find_and_click_button("back")

        if "wait" in command:
            split_command = command.split(".")
            split_command.pop(0)
            CombatMode._wait_execute(split_command)

        if "attack" in command:
            CombatMode._end()
            return True

        return False

    @staticmethod
    def _quick_summon(command: str = ""):
        """Activate a Quick Summon.

        Args:
            command (str, optional): The command to be executed. Defaults to the regular quick summon command.

        Returns:
            (bool): Return True if the Turn will end due to a chained "attack" command. False otherwise.
        """
        from bot.game import Game

        MessageLog.print_message("[COMBAT] Quick Summoning now...")
        if ImageUtils.find_button("quick_summon_not_ready", bypass_general_adjustment = True) is None and \
                (Game.find_and_click_button("quick_summon1", bypass_general_adjustment = True) or Game.find_and_click_button("quick_summon2", bypass_general_adjustment = True)):
            MessageLog.print_message("[COMBAT] Successfully quick summoned!")

            if "attack" in command:
                CombatMode._end()
                return True
        else:
            MessageLog.print_message("[COMBAT] Was not able to quick summon this Turn.")

        return False

    @staticmethod
    def _enable_semi_auto():
        """Enable Semi Auto and if it fails, try coordinates or Full Auto.

        Returns:
            None
        """
        from bot.game import Game

        MessageLog.print_message("[COMBAT] Bot will now attempt to enable Semi Auto...")
        CombatMode._semi_auto = ImageUtils.find_button("semi_auto_enabled")
        if not CombatMode._semi_auto:
            # First try direct template/DOM match for semi_auto button
            if Game.find_and_click_button("semi_auto", tries = 2, suppress_error = True):
                CombatMode._semi_auto = True
                MessageLog.print_message("[COMBAT] Semi Auto button clicked.")
                return None

            # Next try clicking the Auto button via screen coordinates relative to Attack button
            if CombatMode._attack_button_location is None:
                CombatMode._attack_button_location = ImageUtils.find_button("attack", tries = 10, suppress_error = True, bypass_general_adjustment = True)

            if CombatMode._attack_button_location is not None:
                if Settings.use_first_notch:
                    auto_x = CombatMode._attack_button_location[0] - 212
                    auto_y = CombatMode._attack_button_location[1] + 12
                else:
                    auto_x = CombatMode._attack_button_location[0] - 322
                    auto_y = CombatMode._attack_button_location[1] + 18
                MouseUtils.move_and_click_point(auto_x, auto_y, "semi_auto_coords")
                CombatMode._semi_auto = True
                MessageLog.print_message(f"[COMBAT] Semi Auto clicked via coordinates ({auto_x}, {auto_y}).")
                return None

            # Fallback: Attack first, then attempt Semi Auto
            Game.find_and_click_button("attack")
            CombatMode._semi_auto = Game.find_and_click_button("semi_auto")
            if not CombatMode._semi_auto:
                MessageLog.print_message("[COMBAT] Failed to enable Semi Auto. Falling back to Full Auto...")
                CombatMode._full_auto = Game.find_and_click_button("full_auto")
            else:
                MessageLog.print_message("[COMBAT] Semi Auto is now enabled.")

        return None

    @staticmethod
    def _is_full_auto_active() -> bool:
        """Check if Full Auto or active attack turn is currently running in the battle."""
        from bot.game import Game
        try:
            res = Game.evaluate_dom_js("""(() => {
                let hash = window.location.hash || '';
                if (!hash.includes('raid') && !hash.includes('stage')) return false;

                // 1. If Attack button is visible with 'display-on', the battle is IDLE waiting for player action!
                let att = document.querySelector('.btn-attack-start');
                let attIdle = Boolean(
                    att &&
                    att.classList.contains('display-on') &&
                    att.offsetParent !== null &&
                    window.getComputedStyle(att).display !== 'none'
                );

                // 2. Check Auto button class/state
                let auto = document.querySelector('.btn-auto');
                let autoActive = false;
                let autoVisible = Boolean(
                    auto && auto.offsetParent !== null &&
                    window.getComputedStyle(auto).display !== 'none' &&
                    window.getComputedStyle(auto).visibility !== 'hidden'
                );
                if (autoVisible) {
                    let cls = auto.className || '';
                    if (cls.includes('select') || cls.includes('state-auto') || cls.includes('is-active')) {
                        autoActive = true;
                    }
                }

                // 3. Check internal engine status
                if (window.stage && window.stage.gGameStatus) {
                    let gs = window.stage.gGameStatus;
                    if (gs.auto_attack === 1 || gs.is_auto || gs.auto) {
                        autoActive = true;
                    }
                    if (gs.attacking === 1 || gs.is_attack || gs.attack_action) {
                        return true;
                    }
                }

                // 4. Cancel button is ONLY active if it has 'display-on' (never when display-off)
                let cancel = document.querySelector('.btn-attack-cancel');
                if (cancel && cancel.classList.contains('display-on') && !cancel.classList.contains('display-off') &&
                    cancel.offsetParent !== null && window.getComputedStyle(cancel).display !== 'none') {
                    return true;
                }

                // 5. If auto is confirmed active:
                if (autoActive) {
                    return true;
                }

                // 6. If attack button is idle waiting for action, Full Auto is NOT running!
                if (attIdle) {
                    return false;
                }

                // 7. If attack button is hidden/display-off, turn is executing
                if (att && (att.classList.contains('display-off') || window.getComputedStyle(att).display === 'none')) {
                    return true;
                }

                return false;
            })()""")
            if res is not None:
                return bool(res)
        except Exception:
            pass

        # Image fallback: combat_cancel on screen = attack in progress = Full Auto running
        if ImageUtils.find_button("combat_cancel", custom_confidence = 0.70, suppress_error = True) is not None:
            return True

        # Image check fallback (search in images/buttons/ folder)
        if ImageUtils.find_button("full_auto_enabled", custom_confidence = 0.70, suppress_error = True) is not None:
            return True

        return False

    @staticmethod
    def _enable_full_auto() -> bool:
        """Enable Full Auto through CDP without moving or clicking the physical cursor.

        Exactly one DOM activation is dispatched. If CDP or the control is unavailable, callers
        may retry on their normal polling cycle; this method never falls back to screen clicks.
        """
        from bot.game import Game

        MessageLog.print_message("[COMBAT] Bot will now attempt to enable Full Auto...")

        # Use a single DOM click via CDP so Full Auto never takes control of the user's cursor.
        if getattr(Settings, "enable_dom_clicking", False):
            try:
                res = Game.evaluate_dom_js("""(() => {
                    let candidates = Array.from(document.querySelectorAll('.btn-auto:not(.semi), .btn-auto'));
                    let auto = candidates.find(el => el.offsetParent !== null &&
                        window.getComputedStyle(el).display !== 'none' &&
                        window.getComputedStyle(el).visibility !== 'hidden');
                    if (auto) {
                        let cls = auto.className || '';
                        // Do not click if already active/selected
                        if (cls.includes('select') || cls.includes('active') || cls.includes('state-auto')) {
                            return { success: true, already_active: true, cls: cls };
                        }
                        if (window.stage && window.stage.gGameStatus && (window.stage.gGameStatus.auto_attack === 1 || window.stage.gGameStatus.is_auto)) {
                            return { success: true, already_active: true, cls: cls };
                        }
                        if (window.$) {
                            try { $(auto).trigger('tap'); return { success: true, cls: auto.className }; } catch(e) {}
                        }
                        auto.click();
                        return { success: true, cls: auto.className };
                    }
                    return { success: false };
                })()""")
                if res and isinstance(res, dict) and res.get('success'):
                    if res.get('already_active'):
                        MessageLog.print_message(f"[COMBAT] Full Auto is already active ({res.get('cls')}). Skipping click.")
                    else:
                        MessageLog.print_message(f"[COMBAT] Full Auto activation dispatched via DOM ({res.get('cls')}).")
                    # The click can be accepted before the game finishes updating its combat
                    # state on a slow connection. Poll briefly instead of immediately treating
                    # that delayed state transition as an activation failure.
                    for _ in range(CombatMode._FULL_AUTO_ACTIVATION_VERIFY_ATTEMPTS):
                        Game.wait(0.5)
                        CombatMode._full_auto = CombatMode._is_full_auto_active()
                        if CombatMode._full_auto:
                            CombatMode._full_auto_last_enabled_time = time.time()
                            MessageLog.print_message("[COMBAT] Full Auto state verified active.")
                            return True
                    MessageLog.print_message("[WARNING] Full Auto activation was dispatched but active state was not verified.")
            except Exception as exc:
                if Settings.debug_mode:
                    MessageLog.print_message(f"[DEBUG] Full Auto DOM activation failed: {exc}")

        CombatMode._full_auto = False
        MessageLog.print_message(
            "[WARNING] Full Auto DOM control is not ready or CDP is unavailable. "
            "No physical cursor click was attempted."
        )
        return False

    @staticmethod
    def _wait_for_full_auto_control(max_attempts: int = None) -> bool:
        """Wait until the battle's Full Auto control is usable through CDP.

        The Attack button can render before the rest of the battle controls on a slow
        connection. Treating that partial render as a fully-loaded battle causes the bot to
        fail Full Auto immediately and navigate Home. Keep polling the control that is
        actually required, and continue dismissing READY while the battle finishes loading.
        """
        from bot.game import Game

        attempts = max_attempts or CombatMode._FULL_AUTO_CONTROL_WAIT_ATTEMPTS
        for attempt in range(attempts):
            control_ready = False
            try:
                control_ready = bool(Game.evaluate_dom_js("""(() => {
                    let candidates = Array.from(document.querySelectorAll('.btn-auto:not(.semi), .btn-auto'));
                    let status = window.stage && window.stage.gGameStatus;
                    if (status && (status.auto_attack === 1 || status.is_auto || status.auto)) {
                        return true;
                    }
                    return candidates.some(el => {
                        let cls = el.className || '';
                        let active = cls.includes('select') || cls.includes('active') || cls.includes('state-auto');
                        let visible = el.offsetParent !== null &&
                            window.getComputedStyle(el).display !== 'none' &&
                            window.getComputedStyle(el).visibility !== 'hidden';
                        return active || visible;
                    });
                })()"""))
            except Exception:
                pass

            if control_ready:
                return True

            Game.check_and_tap_ready()
            if attempt < attempts - 1:
                Game.wait(1.0)

        return False

    @staticmethod
    def _attack_back():
        """Attacks and then presses the Back button to quickly end animations.

        Returns:
            None
        """
        from bot.game import Game

        if Game.find_and_click_button("attack"):
            if ImageUtils.wait_vanish("combat_cancel", timeout = 10):
                MessageLog.print_message("[COMBAT] Attacked and pressing the Back button now...")
                CombatMode._back(increment_turn = False)

            # Advance the Turn number by 1.
            CombatMode._turn_number += 1
        else:
            MessageLog.print_message("[WARNING] Failed to execute the \"attackback\" command...")

        return None

    @staticmethod
    def _attack(command: str):
        """Attacks and if there is a wait command attached, execute that as well.

        Args:
            command (str): The command to be executed.

        Returns:
            None
        """
        from bot.game import Game

        if Game.find_and_click_button("attack", tries = 30):
            if ImageUtils.wait_vanish("combat_cancel", timeout = 10):
                MessageLog.print_message("[COMBAT] Successfully executed a manual attack.")
            else:
                MessageLog.print_message("[COMBAT] Successfully executed a manual attack that resolved instantly.")
        else:
            MessageLog.print_message("[WARNING] Failed to execute a manual attack.")

        if "wait" in command:
            split_command = command.split(".")
            split_command.pop(0)
            CombatMode._wait_execute(list(split_command))

        return None

    @staticmethod
    def _back(increment_turn: bool = True):
        """Presses the Back button. Increments the Turn number if specified otherwise.

        Args:
            increment_turn (bool, optional): Increments the Turn number. Defaults to True.

        Returns:
            None
        """
        from bot.game import Game

        if Game.find_and_click_button("home_back"):
            MessageLog.print_message("[COMBAT] Tapped the Back button.")
            CombatMode._wait_for_attack()

            if increment_turn:
                # Advance the Turn number by 1.
                CombatMode._turn_number += 1
        else:
            MessageLog.print_message("[WARNING] Failed to find and tap the Back button.")

        return None

    @staticmethod
    def _reload():
        """Reloads the page.

        Returns:
            None
        """
        from bot.game import Game

        MessageLog.print_message("[COMBAT] Bot will now attempt to manually reload...")

        # Press the "Attack" button in order to show the "Cancel" button. Once that disappears, manually reload the page.
        if Game.find_and_click_button("attack"):
            if ImageUtils.wait_vanish("combat_cancel", timeout = 10):
                Game.find_and_click_button("reload")
                Game.wait(3.0)
            else:
                # If the "Cancel" button fails to disappear after 10 tries, reload anyways.
                Game.find_and_click_button("reload")
                Game.wait(3.0)

        return None

    @staticmethod
    def _end():
        """Ends the Turn.

        Returns:
            None
        """
        CombatMode._wait_for_attack()

        MessageLog.print_message(f"[COMBAT] Turn {CombatMode._turn_number} has ended.")

        CombatMode._turn_number += 1
        return None

    @staticmethod
    def _wait_for_semi_auto_reload_end():
        """Enables Semi Auto, immediately reloads the page, then waits for the raid
        battle to conclude. A periodic safety reload is performed every 3 minutes.
        Used for raids (e.g. EX Xuanwu) where the strategy is:
          1. Enable Semi Auto (triggers one round of attacks)
          2. Reload immediately (game syncs with server result)
          3. Wait for Quest Result screen

        Returns:
            None
        """
        from bot.game import Game

        start_time = time.time()
        _reload_interval = 180  # Periodic reload every 3 minutes

        # Temporarily disable auto exit timeout during semi auto wait so it never triggers Time Exceeded
        orig_auto_exit = Settings.enable_auto_exit_raid
        Settings.enable_auto_exit_raid = False

        try:
            # Step 1: Enable Auto Attack by clicking READY screen (or using pre-tap)
            if getattr(Settings, "auto_attack_pretapped", False) or getattr(Settings, "full_auto_pretapped", False):
                MessageLog.print_message("[COMBAT] Auto attack was already enabled by tapping the READY screen before battle.")
                Game.wait(1.5)
            else:
                MessageLog.print_message("[COMBAT] Checking for READY screen to enable auto attack...")
                ready_poll_tries = 20
                while ready_poll_tries > 0:
                    if Game.check_and_tap_ready():
                        Settings.auto_attack_pretapped = True
                        Settings.full_auto_pretapped = True
                        break
                    ready_poll_tries -= 1
                    if ready_poll_tries > 0:
                        Game.wait(0.25)

                # Wait for the attack turn action to be accepted by the game server
                Game.wait(1.5)

            # Step 2: Immediately reload page
            MessageLog.print_message("[COMBAT] Auto attack enabled. Reloading page immediately...")
            Game.find_and_click_button("reload")
            Game.wait(3.0)

            timeout = CombatMode._combat_safety_timeout_seconds()
            timeout_text = "disabled by configuration" if timeout is None else f"{int(timeout)}s"
            MessageLog.print_message(
                f"[COMBAT] Waiting for raid battle to conclude after reload "
                f"(safety timeout: {timeout_text})..."
            )

            last_log_time = time.time()
            last_reload_time = time.time()

            # Step 3: Monitor for battle end
            while not CombatMode._retreat_check:
                CombatMode._check_monitor_safety_timeout(start_time, "Semi Auto result monitor")

                # 1. Check if battle has ended (detects result URL hash or result DOM element)
                CombatMode._check_for_battle_end()

                # Periodic status log every 10 seconds
                if time.time() - last_log_time >= 10.0:
                    elapsed = int(time.time() - start_time)
                    MessageLog.print_message(f"[COMBAT] Waiting for raid result ({elapsed}s elapsed)...")
                    last_log_time = time.time()

                # Periodic safety reload every 3 minutes
                if time.time() - last_reload_time >= _reload_interval:
                    elapsed = int(time.time() - start_time)
                    MessageLog.print_message(f"\n[COMBAT] Periodic safety reload at {elapsed}s elapsed. Refreshing sync with server...")
                    Game.find_and_click_button("reload")
                    Game.wait(3.0)
                    last_reload_time = time.time()

                # Click Next if visible (multi-wave or end of raid)
                if Game.find_and_click_button("next", tries=1, suppress_error=True):
                    Game.wait(2.0)
                    CombatMode._check_for_battle_end()

                # Check for party wipe
                CombatMode._check_for_wipe()

                Game.wait(1.5)
        finally:
            Settings.enable_auto_exit_raid = orig_auto_exit

        return None

    ######################################################################
    ######################################################################
    # Looping Workflows for the End
    ######################################################################
    ######################################################################

    @staticmethod
    def _wait_for_full_auto_end():
        """Passively waits for Full Auto raid battle to conclude.
        Monitors URL, DOM, boss HP, and screen images for Quest Result / battle conclusion.
        No timeout is applied — the loop runs until the battle ends or the party wipes.
        NO reload page is performed during combat as Full Auto runs naturally to completion.

        Returns:
            None
        """
        from bot.game import Game

        start_time = time.time()

        timeout = CombatMode._combat_safety_timeout_seconds()
        timeout_text = "disabled by configuration" if timeout is None else f"{int(timeout)}s"
        MessageLog.print_message(
            f"[COMBAT] Full Auto is running. Monitoring battle progress "
            f"(safety timeout: {timeout_text})..."
        )

        last_log_time = time.time()

        while not CombatMode._retreat_check:
            CombatMode._check_monitor_safety_timeout(start_time, "Full Auto monitor")

            # 1. Check if battle has ended (DOM, URL, image checks)
            CombatMode._check_for_battle_end()

            # 2. Check if boss is already defeated (0% HP or victory screen)
            if time.time() - start_time >= 5.0 and CombatMode._is_boss_defeated_via_dom():
                MessageLog.print_message("[COMBAT] Boss HP reached 0% (or victory screen detected). Waiting for battle conclusion...")
                if Game.find_and_click_button("next", tries = 1, suppress_error = True):
                    Game.wait(2.0)
                CombatMode._check_for_battle_end()
                _boss_0hp_time = getattr(CombatMode, "_boss_0hp_time", 0.0)
                if _boss_0hp_time == 0.0:
                    CombatMode._boss_0hp_time = time.time()
                elif time.time() - _boss_0hp_time >= 4.0:
                    MessageLog.print_message("[COMBAT] Boss defeated for >4s without transition. Reloading page to sync with Results...")
                    Game.find_and_click_button("reload")
                    Game.wait(3.0)
                    CombatMode._check_for_battle_end()
                    CombatMode._boss_0hp_time = time.time()
            else:
                CombatMode._boss_0hp_time = 0.0

            # 3. Periodic status message every 10 seconds
            if time.time() - last_log_time >= 10.0:
                elapsed = int(time.time() - start_time)
                MessageLog.print_message(f"[COMBAT] Full Auto in progress ({elapsed}s elapsed). Waiting for raid to conclude...")
                last_log_time = time.time()

            # 4. Only click Next if we are on a result/conclusion screen (NOT during active Full Auto combat).
            # Clicking next during an active battle risks interrupting charge attacks or Full Auto pacing.
            _on_result_screen = False
            try:
                _result_js = """(() => {
                    let hash = window.location.hash || '';
                    if (hash.startsWith('#raid') || hash.startsWith('#stage')) return false;
                    if (hash.startsWith('#result') || hash.includes('no_loot')) return true;
                    let resultEl = document.querySelector('.prt-result-head, .cnt-result, .prt-result-win');
                    if (resultEl && resultEl.offsetParent !== null) return true;
                    let waveNext = document.querySelector('.btn-command-next, .btn-settlement-next');
                    if (waveNext && waveNext.offsetParent !== null) return true;
                    return false;
                })()"""
                _on_result_screen = bool(Game.evaluate_dom_js(_result_js))
            except Exception:
                pass
            if _on_result_screen and Game.find_and_click_button("next", tries = 1, suppress_error = True):
                Game.wait(2.0)
                CombatMode._check_for_battle_end()

            # Check wipe before interacting with any generic popup. This prevents an OK fallback
            # from accepting an elixir/revive prompt before the wipe state is classified.
            CombatMode._check_for_wipe()
            if CombatMode._retreat_check:
                break

            # 4b. Dismiss dialogue balloons or safe, non-destructive in-battle notices.
            CombatMode._check_for_dialog()
            try:
                Game.evaluate_dom_js("""(() => {
                    let popOk = document.querySelector('.pop-usual .btn-usual-ok, .prt-popup-footer .btn-usual-ok, .btn-pop-ok');
                    if (popOk && popOk.offsetParent !== null && window.getComputedStyle(popOk).display !== 'none') {
                        let popup = popOk.closest('.pop-usual, .pop-show, [class*="popup"]');
                        let text = ((popup && (popup.innerText || popup.textContent)) || '').toLowerCase();
                        let destructive = popup && popup.querySelector('.btn-use-elixir, .btn-revive, .btn-retreat');
                        if (destructive || text.includes('elixir') || text.includes('revive') ||
                            text.includes('retreat') || text.includes('continue battle')) return false;
                        let activated = false;
                        if (window.$) { try { $(popOk).trigger('tap'); activated = true; } catch(e){} }
                        if (!activated) popOk.click();
                        return true;
                    }
                    let dialogBox = document.querySelector('.prt-balloon, .cnt-balloon');
                    if (dialogBox && dialogBox.offsetParent !== null) {
                        let activated = false;
                        if (window.$) { try { $(dialogBox).trigger('tap'); activated = true; } catch(e){} }
                        if (!activated) dialogBox.click();
                        return true;
                    }
                    return false;
                })()""")
            except Exception:
                pass

            # 5. Watchdog: ensure Full Auto didn't turn off mid-battle or during looping.
            # Cooldown: 6 seconds after last enable. Threshold: 2 consecutive idle checks (~3s idle).
            _watchdog_last_enabled = getattr(CombatMode, "_full_auto_last_enabled_time", 0.0)
            if time.time() - start_time >= 5.0 and time.time() - _watchdog_last_enabled >= 6.0:
                try:
                    # Only re-enable if Full Auto is confirmed INACTIVE and boss is still alive
                    if not CombatMode._is_full_auto_active() and not CombatMode._is_boss_defeated_via_dom():
                        CombatMode._full_auto_idle_count = getattr(CombatMode, "_full_auto_idle_count", 0) + 1
                        if Settings.debug_mode:
                            MessageLog.print_message(f"[DEBUG] Full Auto idle count: {CombatMode._full_auto_idle_count}/2")
                        if CombatMode._full_auto_idle_count >= 2:
                            MessageLog.print_message("[COMBAT] Full Auto stopped mid-battle. Re-enabling Full Auto now...")
                            enabled = CombatMode._enable_full_auto()
                            CombatMode._full_auto_idle_count = 0
                            if enabled:
                                CombatMode._full_auto_last_enabled_time = time.time()
                    else:
                        CombatMode._full_auto_idle_count = 0
                except Exception:
                    pass

            Game.wait(1.5)

        return None

    @staticmethod
    def _loop_auto():
        """Main workflow loop for both Semi Auto and Full Auto. The bot will progress the Quest/Raid until it ends or the Party wipes.

        Returns:
            None
        """
        from bot.game import Game

        # Wait a short moment to let Full Auto begin processing before the loop starts.
        Game.wait(3.0)

        # Track the time when Full Auto started to avoid premature reloads on turn 1.
        _loop_start_time = time.time()
        _min_seconds_before_reload = 20  # Don't reload within first 20 seconds of Full Auto starting.

        while not CombatMode._retreat_check and (CombatMode._full_auto or CombatMode._semi_auto):
            # Check for exit conditions.
            CombatMode._check_for_battle_end()

            if Game.find_and_click_button("next", tries = 1, suppress_error = True):
                Game.wait(3)

            CombatMode._check_for_wipe()

            if CombatMode._check_raid():
                # Click Next if it is available and enable automation again if combat continues.
                if Game.find_and_click_button("next", tries = 1, suppress_error = True):
                    Game.wait(3.0)

                    # Check for exit conditions and restart auto.
                    if CombatMode._check_for_battle_end() == "Nothing":
                        CombatMode._enable_auto()
                elif ImageUtils.find_button("attack", tries = 1, suppress_error = True) is None and ImageUtils.find_button("next", tries = 1, suppress_error = True) is None and \
                        CombatMode._check_for_battle_end() == "Nothing":
                    # Only reload if we've been in Full Auto for long enough (avoid reloading mid-turn-1 animation).
                    elapsed = time.time() - _loop_start_time
                    if elapsed >= _min_seconds_before_reload:
                        Game.wait(1.0)
                        CombatMode._reload_for_attack(override = True)
                        CombatMode._wait_for_attack()

                        # Check for exit conditions and restart auto.
                        if CombatMode._check_for_battle_end() == "Nothing":
                            if Settings.debug_mode:
                                MessageLog.print_message("[DEBUG] Clicked the Next button to move to the next wave. Attempting to restart Full/Semi Auto...")

                            CombatMode._enable_auto()
                    else:
                        # Too early to reload — wait a bit for attack animations to settle.
                        if Settings.debug_mode:
                            MessageLog.print_message(f"[DEBUG] Skipping reload (only {elapsed:.1f}s into Full Auto, min={_min_seconds_before_reload}s). Waiting for attack to settle...")
                        Game.wait(2.0)
            elif ImageUtils.find_button("attack", tries = 1, suppress_error = True) is None and ImageUtils.find_button("next", tries = 1, suppress_error = True) is None:
                if Settings.debug_mode:
                    MessageLog.print_message("[DEBUG] Attack and Next buttons have vanished. Determining if bot should reload...")

                if CombatMode._reload_for_attack():
                    # Enable Full/Semi Auto again if the bot reloaded.
                    if CombatMode._full_auto:
                        CombatMode._enable_full_auto()
                    elif CombatMode._semi_auto:
                        CombatMode._enable_semi_auto()

        return None

    @staticmethod
    def _loop_manual():
        """Main workflow loop for manually pressing the Attack button and reloading until combat ends.

        Returns:
            None
        """
        from bot.game import Game

        while not CombatMode._retreat_check:
            # Check for exit conditions.
            CombatMode._check_for_battle_end()

            if Game.find_and_click_button("next", tries = 1, suppress_error = True):
                Game.wait(3)

                # Check for exit conditions.
                CombatMode._check_for_battle_end()

            Game.find_and_click_button("attack", tries = 10)
            CombatMode._reload_for_attack()
            CombatMode._wait_for_attack()

        return None

    ######################################################################
    ######################################################################
    # Auto-Battle Initial Skill Sequence
    ######################################################################
    ######################################################################

    @staticmethod
    def _run_initial_skill_sequence():
        """Runs the automatic initial skill sequence.

        Sequence:
          1. Select Character 1.
          2. Use Skills 1, 2, 3, 4 (skips any that are on cooldown / unavailable).
          3. Press the Back button to return to the main battle screen.
          4. Press the Attack button (this reveals the Full Auto toggle).
          5. Press the Full Auto button (via DOM .btn-auto or coordinates).
          6. Press Attack again so Characters 2-4 also activate skills via Full Auto.

        Returns:
            None
        """
        from bot.game import Game

        MessageLog.print_message("\n[COMBAT] Running automatic initial skill sequence (Character 1 Skills -> Back -> Attack -> Full Auto -> Attack)...")

        # ----------------------------------------------------------------
        # Step 1: Select Character 1 and use Skills 1-4.
        # ----------------------------------------------------------------
        CombatMode._select_character(1)
        Game.wait(0.5)

        # Compute skill button coordinates (same offsets as _use_character_skill).
        if Settings.use_first_notch is False:
            # Notch 2: measured from DOM — Skill 1 is 286px left of Attack center, spaced by 106px
            x_offset = 286
            x_inc   = 106
            y_offset = 201
        else:
            x_offset = 250
            x_inc   = 55
            y_offset = 115

        skill_y = CombatMode._attack_button_location[1] + y_offset

        for skill_num in range(1, 5):
            skill_x = CombatMode._attack_button_location[0] - x_offset + (x_inc * (skill_num - 1))
            MessageLog.print_message(f"[COMBAT] Character 1 uses Skill {skill_num}.")

            # Try DOM skill trigger first
            dom_skill = Game.evaluate_dom_js(f"""(() => {{
                let b = document.querySelector('.prt-ability-list .lis-ability:nth-child({skill_num}) .btn-ability-available, .btn-ability-available[ability-id="{skill_num}"]');
                if (b && b.offsetParent !== null) {{
                    if (window.$) {{ try {{ $(b).trigger('tap'); }} catch(e){{}} }}
                    b.click();
                    return true;
                }}
                return false;
            }})()""")

            # Also click the skill coordinate
            MouseUtils.move_and_click_point(skill_x, skill_y, "template_skill")
            Game.wait(0.5)

            # If a target-selection overlay appears, select Character 1.
            if ImageUtils.confirm_location("use_skill", bypass_general_adjustment=True):
                MessageLog.print_message("[COMBAT] Skill requires a target. Auto-selecting Character 1.")
                if Settings.use_first_notch is False:
                    target_x = CombatMode._attack_button_location[0] - 409
                    target_y = CombatMode._attack_button_location[1] + 111
                else:
                    target_x = CombatMode._attack_button_location[0] - 275
                    target_y = CombatMode._attack_button_location[1] + 75
                MouseUtils.move_and_click_point(target_x, target_y, "template_target")
                Game.wait(0.5)

        Game.wait(0.5)

        # ----------------------------------------------------------------
        # Step 2: Press Back to return to the main battle view.
        # ----------------------------------------------------------------
        MessageLog.print_message("[COMBAT] Pressing Back after Character 1 skills.")
        if not Game.find_and_click_button("back", tries=3, suppress_error=True):
            Game.find_and_click_button("home_back", tries=3, suppress_error=True)
        Game.wait(1.0)

        # ----------------------------------------------------------------
        # Step 3: Press Attack to start the turn and reveal the Full Auto button.
        # ----------------------------------------------------------------
        MessageLog.print_message("[COMBAT] Pressing Attack to reveal Full Auto button...")
        att_clicked = Game.evaluate_dom_js("""(() => {
            let att = document.querySelector('.btn-attack-start');
            if (!att) return false;
            ['touchstart', 'touchend', 'mousedown', 'mouseup', 'click'].forEach(evt => {
                try {
                    let e = new MouseEvent(evt, {bubbles: true, cancelable: true, view: window});
                    att.dispatchEvent(e);
                } catch(e) {}
            });
            if (window.$) { try { $('.btn-attack-start').trigger('tap'); } catch(e) {} }
            try { att.click(); } catch(e) {}
            return true;
        })()""")
        if not att_clicked:
            if CombatMode._attack_button_location:
                MouseUtils.move_and_click_point(CombatMode._attack_button_location[0], CombatMode._attack_button_location[1], "attack")
            else:
                Game.find_and_click_button("attack", tries=15, suppress_error=True)
        Game.wait(1.5)

        # ----------------------------------------------------------------
        # Step 4: Press Full Auto (DOM .btn-auto or coordinates).
        # ----------------------------------------------------------------
        MessageLog.print_message("[COMBAT] Pressing Full Auto...")
        CombatMode._enable_full_auto()
        Game.wait(1.0)

        # ----------------------------------------------------------------
        # Step 5: Press Attack again so Characters 2-4 fire their skills via Full Auto.
        # ----------------------------------------------------------------
        MessageLog.print_message("[COMBAT] Pressing Attack again to trigger Full Auto for Characters 2-4...")
        att2_clicked = Game.evaluate_dom_js("""(() => {
            let att = document.querySelector('.btn-attack-start');
            if (!att) return false;
            ['touchstart', 'touchend', 'mousedown', 'mouseup', 'click'].forEach(evt => {
                try {
                    let e = new MouseEvent(evt, {bubbles: true, cancelable: true, view: window});
                    att.dispatchEvent(e);
                } catch(e) {}
            });
            if (window.$) { try { $('.btn-attack-start').trigger('tap'); } catch(e) {} }
            try { att.click(); } catch(e) {}
            return true;
        })()""")
        if not att2_clicked:
            if CombatMode._attack_button_location:
                MouseUtils.move_and_click_point(CombatMode._attack_button_location[0], CombatMode._attack_button_location[1], "attack")
            else:
                Game.find_and_click_button("attack", tries=10, suppress_error=True)
        Game.wait(1.0)

        MessageLog.print_message("[COMBAT] Initial skill sequence complete. Full Auto is now driving the battle.")
        return None

    ######################################################################
    ######################################################################
    # Entry Point
    ######################################################################
    ######################################################################

    @staticmethod
    def start_combat_mode(script_commands: List[str] = None, is_nightmare: bool = False, is_defender: bool = False):
        """Start Combat Mode with the given script file path. Start reading through the text file line by line and have the bot proceed with the commands accordingly.

        Args:
            script_commands (List[str]): List of script commands to use instead of reading from a text file. Defaults to None.
            is_nightmare (bool, optional): If Combat Mode is being used for a Nightmare, determines the method of reading the script file.
            is_defender (bool, optional): If Combat Mode is being used for a Defender, determines the method of reading the script file.

        Returns:
            (bool): Return True if Combat Mode was successful. Else, return False if the Party wiped or backed out without retreating.
        """
        from bot.game import Game

        CombatMode._start_time = time.time()

        # Reset flags and Attack button location.
        CombatMode._retreat_check = False
        CombatMode._semi_auto = False
        CombatMode._full_auto = False
        CombatMode._full_auto_idle_count = 0
        CombatMode._full_auto_last_enabled_time = 0.0
        CombatMode._boss_0hp_time = 0.0
        manual_attack_and_reload = False
        skip_end = False
        CombatMode._attack_button_location = None
        CombatMode._command_turn_number = 1
        CombatMode._turn_number = 1  # Current turn for the script execution.

        MessageLog.print_message("\n######################################################################")
        MessageLog.print_message("######################################################################")
        MessageLog.print_message(f"[COMBAT] Starting Combat Mode.")
        MessageLog.print_message("######################################################################")
        MessageLog.print_message("######################################################################\n")

        if script_commands is not None:
            command_list = script_commands
        else:
            if is_nightmare:
                MessageLog.print_message(f"Name of Nightmare combat script loaded: {Settings.nightmare_combat_script_name}")
                command_list = copy.deepcopy(Settings.nightmare_combat_script)
            elif is_defender:
                MessageLog.print_message(f"Name of Defender combat script loaded: {Settings.defender_combat_script_name}")
                command_list = copy.deepcopy(Settings.defender_combat_script)
            else:
                MessageLog.print_message(f"Name of combat script loaded: {Settings.combat_script_name}")
                command_list = copy.deepcopy(Settings.combat_script)

        MessageLog.print_message(f"[COMBAT] Size of script commands: {len(command_list)}")

        # If current Farming Mode is Arcarum, attempt to dismiss potential stage effect popup like "Can't use Charge Attacks".
        if Settings.farming_mode == "Arcarum":
            Game.find_and_click_button("arcarum_stage_effect_active", tries = 10, bypass_general_adjustment = True)

        # ------------------------------------------------------------------
        # Detect Semi Auto Then Reload mode (e.g. EX Xuanwu) early.
        # Taps the READY loading screen, reloads immediately, and waits for battle end.
        # ------------------------------------------------------------------
        effective_commands = [c for c in command_list if c.strip() and not c.strip().startswith("#") and not c.strip().startswith("/")]
        is_semi_auto_reload_mode = (
            Settings.combat_script_name.lower() == "semi_auto_then_reload.txt"
            or any(cmd in c.lower() for c in effective_commands for cmd in ("enablesemiautoandreload", "enablesemiautoreload", "enablesemiautoandrreload", "enablesemiautoandrload"))
        )

        if is_semi_auto_reload_mode:
            MessageLog.print_message("[COMBAT] Semi Auto Then Reload mode: starting workflow (Tap READY -> Reload -> Wait result)...")
            try:
                CombatMode._wait_for_semi_auto_reload_end()
            except CombatModeException as e:
                if CombatMode._list_of_exit_events_for_false.__contains__(e.__str__()):
                    MessageLog.print_message(f"[COMBAT] Combat mode ended with event '{e}'. Returning to Home...")
                    Game.go_back_home(confirm_location_check = True)
                    return False
                elif CombatMode._list_of_exit_events_for_true.__contains__(e.__str__()):
                    if Settings.enable_opt_in_api:
                        Settings.combat_elapsed_time = time.time() - CombatMode._start_time
                    return True
            if CombatMode._retreat_check:
                MessageLog.print_message("[COMBAT] Party retreated or wiped. Ending Combat Mode with False.")
                return False
            return True

        # ------------------------------------------------------------------
        # Detect Full Auto mode early so we can tap the READY loading screen.
        # ------------------------------------------------------------------
        normalized_commands = []
        for raw_command in effective_commands:
            normalized = raw_command.strip().lower()
            if "#" in normalized:
                normalized = normalized.split("#", 1)[0].strip()
            normalized_commands.append(normalized)

        full_auto_directive = any(command == "enablefullauto" for command in normalized_commands)
        full_auto_structural_only = all(
            command == "enablefullauto" or command == "end" or command.startswith("turn ")
            for command in normalized_commands
        )
        is_full_auto_mode = len(normalized_commands) == 0 or (
            full_auto_directive and full_auto_structural_only
        )

        # If Full Auto mode: wait for its control to load, then ensure Full Auto is actually active.
        # This works seamlessly for both Run 1 and repeated runs (looping) without double-toggling.
        if is_full_auto_mode:
            MessageLog.print_message("[COMBAT] Full Auto mode: waiting for battle controls to load...")
            if not CombatMode._wait_for_full_auto_control():
                MessageLog.print_message(
                    "[ERROR] Full Auto control did not become ready within 45 seconds. "
                    "Recovering instead of entering an unbounded Full Auto monitor."
                )
                Game.go_back_home(confirm_location_check = True)
                return False

            # Check if Full Auto is currently running (even during looping)
            if CombatMode._is_full_auto_active():
                MessageLog.print_message("[COMBAT] Full Auto is confirmed active and running.")
                CombatMode._full_auto = True
            else:
                MessageLog.print_message("[COMBAT] Full Auto is not active yet. Enabling Full Auto now...")
                enabled = False
                for _ in range(2):
                    if CombatMode._enable_full_auto():
                        enabled = True
                        break
                    Game.wait(1.0)
                if not enabled:
                    MessageLog.print_message(
                        "[ERROR] Full Auto could not be verified after two attempts. "
                        "Recovering to Home instead of monitoring an unknown state."
                    )
                    Game.go_back_home(confirm_location_check = True)
                    return False

            MessageLog.print_message("[COMBAT] Full Auto running. Monitoring battle progress...")
            try:
                CombatMode._wait_for_full_auto_end()
            except CombatModeException as e:
                if CombatMode._list_of_exit_events_for_false.__contains__(e.__str__()):
                    MessageLog.print_message(f"[COMBAT] Full Auto concluded with event '{e}'. Returning to Home...")
                    Game.go_back_home(confirm_location_check = True)
                    return False
                elif CombatMode._list_of_exit_events_for_true.__contains__(e.__str__()):
                    if Settings.enable_opt_in_api:
                        Settings.combat_elapsed_time = time.time() - CombatMode._start_time
                    return True
            if CombatMode._retreat_check:
                MessageLog.print_message("[COMBAT] Party retreated or wiped. Ending Combat Mode with False.")
                return False
            return True

        # Save the position of the Attack button.
        CombatMode._attack_button_location = ImageUtils.find_button("attack", tries = 50, bypass_general_adjustment = True)

        if CombatMode._attack_button_location is None:
            MessageLog.print_message(f"\n[ERROR] Cannot find Attack button. Raid must have just ended.")
            return False

        ######################################################################
        ######################################################################
        # This is where the main workflow of Combat Mode is located.
        try:
            while len(command_list) > 0 and CombatMode._retreat_check is False:
                # All the logic that follows assumes that the command string is lowercase to allow case-insensitive commands.
                command = command_list.pop(0).strip().lower()
                if command == "" or command[0] == "#" or command[0] == "/":
                    continue
                elif command.__contains__("/") or command.__contains__("#"):
                    # Remove comments in the same line.
                    command = command[0:command.find("#")][0:command.find("/")].strip()

                MessageLog.print_message(f"\n[COMBAT] Reading command: \"{command}\"")

                if command.__contains__("turn"):
                    CombatMode._start_turn(command)
                elif CombatMode._turn_number == CombatMode._command_turn_number:
                    # Process all commands here that belong inside a Turn block.

                    # Check for exit conditions.
                    CombatMode._check_for_battle_end()

                    # Determine which Character to take action.
                    if "character1." in command:
                        character_selected = 1
                    elif "character2." in command:
                        character_selected = 2
                    elif "character3." in command:
                        character_selected = 3
                    elif "character4." in command:
                        character_selected = 4
                    else:
                        character_selected = 0

                    if character_selected != 0:
                        # Select the specified Character.
                        CombatMode._select_character(character_selected)

                        # Now execute each Skill command starting from left to right.
                        skill_command_list = command.split(".")
                        skill_command_list.pop(0)  # Remove the "character" portion of the string.
                        if CombatMode._use_character_skill(character_selected, skill_command_list):
                            skip_end = True

                    # Handle any other supported command.
                    elif command == "requestbackup":
                        CombatMode._request_backup()
                    elif command == "tweetbackup":
                        CombatMode._tweet_backup()
                    elif CombatMode._healing_item_commands.__contains__(command):
                        CombatMode._use_combat_healing_item(command)
                    elif command.__contains__("summon") and command.__contains__("quicksummon") is False:
                        if CombatMode._use_summon(command):
                            skip_end = True
                    elif command.__contains__("quicksummon"):
                        if CombatMode._quick_summon(command):
                            skip_end = True
                    elif command == "enablesemiauto":
                        CombatMode._enable_semi_auto()
                    elif command in ("enablesemiautoandreload", "enablesemiautoreload", "enablesemiautoandrreload", "enablesemiautoandrload"):
                        # enableSemiAutoAndReload: klik Semi Auto → reload langsung → tunggu battle end
                        CombatMode._wait_for_semi_auto_reload_end()
                    elif command == "enablefullauto":
                        CombatMode._enable_full_auto()
                    elif "targetenemy" in command:
                        # Select enemy target.
                        CombatMode._select_enemy_target(command)
                    elif "attackback" in command:
                        CombatMode._attack_back()
                    elif "attack" in command:
                        CombatMode._attack(command)
                    elif "back" in command:
                        CombatMode._back()
                    elif "reload" in command:
                        CombatMode._reload()
                    elif command == "repeatmanualattackandreload":
                        MessageLog.print_message("[COMBAT] Enabling manually pressing the Attack button and reloading (if the mission supports it) until battle ends.")
                        manual_attack_and_reload = True
                    elif CombatMode._semi_auto is False and CombatMode._full_auto is False and command == "end" and skip_end is False:
                        CombatMode._end()
                    elif command.find("wait") == 0:
                        CombatMode._wait_execute(list(command))
                    elif command == "exit":
                        # End Combat Mode by heading back to the Home screen without retreating.
                        MessageLog.print_message("\n[COMBAT] Leaving this Raid without retreating.")
                        MessageLog.print_message("\n######################################################################")
                        MessageLog.print_message("######################################################################")
                        MessageLog.print_message("[COMBAT] Ending Combat Mode.")
                        MessageLog.print_message("######################################################################")
                        MessageLog.print_message("######################################################################")
                        Game.go_back_home(confirm_location_check = True)
                        return False

                ######################################################################
                ######################################################################
                # Handle certain commands that could be present outside a Turn block.
                if CombatMode._semi_auto is False and CombatMode._full_auto is False and command == "enablesemiauto":
                    CombatMode._enable_semi_auto()
                elif CombatMode._semi_auto is False and CombatMode._full_auto is False and command == "enablefullauto":
                    CombatMode._enable_full_auto()
                elif command in ("enablesemiautoandreload", "enablesemiautoreload", "enablesemiautoandrreload", "enablesemiautoandrload"):
                    CombatMode._wait_for_semi_auto_reload_end()
                elif command == "repeatmanualattackandreload":
                    MessageLog.print_message("[COMBAT] Enabling manually pressing the Attack button and reloading (if the mission supports it) until battle ends.")
                    manual_attack_and_reload = True
                elif command.find("wait") == 0:
                    CombatMode._wait_execute(list(command))

            # Deal with the situation where high-profile raids end right when the bot loads in and all it sees is the "Next" button.
            if Settings.farming_mode == "Raid" and Game.find_and_click_button("next", tries = 3):
                MessageLog.print_message("\n######################################################################")
                MessageLog.print_message("######################################################################")
                MessageLog.print_message("[COMBAT] Ending Combat Mode.")
                MessageLog.print_message("######################################################################")
                MessageLog.print_message("######################################################################")
                return True

            ######################################################################
            ######################################################################
            # When the bot reaches here, all the commands in the combat script has been processed.
            MessageLog.print_message("\n[COMBAT] Bot has reached end of script. Automatically attacking until battle ends or Party wipes...")

            if manual_attack_and_reload is False:
                # Attempt to activate Full Auto at the end of the combat script. If not, then attempt to activate Semi Auto.
                if CombatMode._full_auto is False and CombatMode._semi_auto is False:
                    CombatMode._enable_full_auto()

                # Counteract slower instances when the battle finished right when the bot finished executing the script.
                if Game.find_and_click_button("next", tries = 1, suppress_error = True):
                    Game.wait(3)
                    CombatMode._check_for_battle_end()

                # Main workflow loop for both Semi Auto and Full Auto. The bot will progress the Quest/Raid until it ends or the Party wipes.
                CombatMode._loop_auto()
            else:
                # Main workflow loop for manually pressing the Attack button and reloading until combat ends.
                CombatMode._loop_manual()
        except CombatModeException as e:
            if CombatMode._list_of_exit_events_for_false.__contains__(e.__str__()):
                MessageLog.print_message(f"[COMBAT] Combat mode ended with event '{e}'. Returning to Home...")
                Game.go_back_home(confirm_location_check = True)
                return False
            elif CombatMode._list_of_exit_events_for_true.__contains__(e.__str__()):
                # Calculate elapsed time for the API.
                if Settings.enable_opt_in_api:
                    Settings.combat_elapsed_time = time.time() - CombatMode._start_time

                return True

        ######################################################################
        ######################################################################

        MessageLog.print_message("\n######################################################################")
        MessageLog.print_message("######################################################################")
        MessageLog.print_message("[COMBAT] Ending Combat Mode.")
        MessageLog.print_message("######################################################################")
        MessageLog.print_message("######################################################################")

        # Calculate elapsed time for the API.
        if Settings.enable_opt_in_api:
            Settings.combat_elapsed_time = time.time() - CombatMode._start_time

        if not CombatMode._retreat_check:
            return True
        else:
            return False
