import json
import random
import time
from typing import Dict, List, Optional

from utils.settings import Settings
from utils.message_log import MessageLog


class DomClicker:
    """Provides ultra-fast DOM button clicking via Chrome DevTools Protocol (CDP).

    Translates common bot button names into Granblue Fantasy CSS selectors or internal
    event dispatchers. Bypasses screenshot capture, template matching, and cursor movement.
    """

    # Mapping of button names (lowercase) to list of candidate CSS selectors or special actions
    BUTTON_SELECTORS: Dict[str, List[str]] = {
        # Dialog / Confirmation
        "ok": [
            ".btn-usual-ok.se-quest-start",
            ".btn-usual-ok",
            ".btn-settle",
            ".btn-approve",
            "input[value='OK']",
            "button.btn-ok",
            ".btn-ok",
        ],
        "btn_ok": [
            ".btn-usual-ok.se-quest-start",
            ".btn-usual-ok",
            ".btn-settle",
            "input[value='OK']",
            "button.btn-ok",
            ".btn-ok",
        ],
        "party_selection_ok": [
            ".btn-usual-ok.se-quest-start",
            ".btn-usual-ok",
            "input[value='OK']",
            "button.btn-ok",
        ],
        "cancel": [
            ".pop-friend-request .btn-usual-cancel",
            ".pop-friend-request .btn-cancel",
            ".prt-popup-footer .btn-cancel",
            "button.btn-cancel",
            ".btn-cancel:not(.btn-attack-cancel):not(.btn-usual-cancel)",
        ],
        "usual_cancel": [
            ".btn-usual-cancel",
        ],
        "combat_cancel": [
            ".btn-usual-cancel",
            ".btn-cancel",
        ],
        "summon_cancel": [
            ".btn-usual-cancel",
            ".btn-cancel",
        ],
        "friend_request_cancel": [
            ".btn-usual-cancel",
            ".btn-cancel",
        ],
        "close": [
            ".btn-usual-close",
            ".btn-close",
            ".btn-popup-close",
            ".prt-popup-header .btn-close",
        ],
        "close_backup": [
            ".btn-usual-close",
            ".btn-close",
        ],
        "trial_battles_close": [
            ".btn-usual-close",
            ".btn-close",
        ],

        # Combat Buttons
        "attack": [
            ".btn-attack-start",
        ],
        "attack_backup": [
            ".btn-attack-start",
        ],
        "full_auto": [
            ".btn-auto:not(.semi)",
            ".btn-auto",
        ],
        "semi_auto": [
            ".btn-auto.semi",
            ".btn-auto",
        ],
        "heal": [
            ".btn-recovery",
        ],

        # Navigation & Headers
        "home_menu": [
            ".btn-head-pop",
            ".btn-menu",
        ],
        "menu": [
            ".btn-head-pop",
            ".btn-menu",
        ],
        "menu_home": [
            ".btn-head-mypage",
            ".btn-home",
            ".btn-treasure-footer-mypage",
            "[data-href='mypage']",
        ],
        "home": [
            ".btn-head-mypage",
            ".btn-home",
            ".btn-treasure-footer-mypage",
            "[data-href='mypage']",
        ],
        "back": [
            ".btn-back",
            ".btn-command-back",
            ".btn-head-back",
        ],
        "home_back": [
            ".btn-back",
            ".btn-command-back",
            ".btn-head-back",
        ],

        # Results & Rewards
        "play_again": [
            ".btn-again",
            ".btn-retry",
            "[data-buton-name='Play Again']",
        ],
        "tap_here_to_see_rewards": [
            ".lis-raid .prt-button-cover",
            ".lis-quest .prt-button-cover",
            ".lis-raid .btn-result",
            ".lis-quest .btn-result",
            ".lis-raid [data-location-href*='result']",
            ".lis-quest [data-location-href*='result']",
        ],
        "play_next": [
            ".btn-play-next",
            ".btn-usual-ok",
        ],

        # Raid & Assist
        "raid_tab_finder": [
            "__CUSTOM_TAB_FINDER__",
        ],
        "raid_search_refresh": [
            ".btn-search-refresh",
        ],
        "enter_id": [
            ".btn-entry-id",
        ],
        "retreat": [
            ".btn-retreat",
        ],
        "retreat_confirmation": [
            ".btn-usual-ok",
        ],
        "resume": [
            ".btn-resume",
            ".btn-usual-ok",
        ],

        # Items & AP Refills
        "use": [
            ".btn-use-item",
            ".btn-usual-use",
        ],
        "refill_half_ap": [
            ".btn-use-half",
            ".btn-use-item",
        ],
        "refill_full_ap": [
            ".btn-use-full",
            ".btn-use-item",
        ],
        "refill_soul_berry": [
            ".btn-use-berry",
            ".btn-use-item",
        ],
        "refill_soul_balm": [
            ".btn-use-balm",
            ".btn-use-item",
        ],

        # Events
        "event_claim_loot": [
            ".btn-claim-loot",
            ".btn-usual-ok",
        ],
        "event_play": [
            ".btn-event-play",
            ".btn-usual-ok",
        ],
        "rotb_shenxian_host": [
            ".btn-event-raid",
            ".btn-raid",
        ],
        "event_banner": [
            ".btn-global-banner[data-href*='teamraid']",
            ".btn-global-banner[data-href*='event']",
            ".btn-global-banner",
        ],
        "dread_barrage": [
            ".btn-global-banner[data-href='event/teamforce']",
        ],
        "guild_wars_banner": [
            ".btn-global-banner[data-href*='teamraid']",
            ".btn-global-banner[data-href*='event']",
            ".btn-global-banner",
        ],

        # Common Navigation and Dialog Buttons
        "quest": [
            ".btn-link-quest",
            "[data-href='quest/index']",
            "[data-href*='quest']",
            ".btn-footer-quest",
            ".btn-quest",
            ".btn-quest-start",
            "[data-location-href='quest']",
        ],
        "quests": [
            ".btn-link-quest",
            "[data-href='quest/index']",
            "[data-href*='quest']",
            ".btn-footer-quest",
            ".btn-quest",
            ".btn-quest-start",
            "[data-location-href='quest']",
        ],
        "raid": [
            "[data-href='quest/assist']:not(.btn-unconfirmed-result):not(.flow-unclaimed):not(.btn-unclaimed)",
            ".btn-multi-battle-blink",
            ".btn-multi-battle",
            ".btn-link-multi",
            ".btn-assist",
            ".btn-raid:not(.btn-unconfirmed-result):not(.flow-unclaimed):not(.btn-unclaimed)",
            "[data-location-href='quest/assist']",
        ],
        "raid_flat": [
            "[data-href='quest/assist']:not(.btn-unconfirmed-result):not(.flow-unclaimed):not(.btn-unclaimed)",
            ".btn-multi-battle-blink",
            ".btn-multi-battle",
            ".btn-link-multi",
            ".btn-assist",
            ".btn-raid:not(.btn-unconfirmed-result):not(.flow-unclaimed):not(.btn-unclaimed)",
            "[data-location-href='quest/assist']",
        ],
        "raid_bouncing": [
            "[data-href='quest/assist']:not(.btn-unconfirmed-result):not(.flow-unclaimed):not(.btn-unclaimed)",
            ".btn-multi-battle-blink",
            ".btn-multi-battle",
            ".btn-link-multi",
            ".btn-assist",
            ".btn-raid:not(.btn-unconfirmed-result):not(.flow-unclaimed):not(.btn-unclaimed)",
            "[data-location-href='quest/assist']",
        ],
        "coop": [
            "[data-href*='coop']",
            ".btn-coop",
            "[data-location-href='coopraid']",
        ],
        "special": [
            ".btn-extra-quest",
            "[data-href='quest/extra']",
            "[data-href*='extra']",
            ".btn-special",
            "[data-location-href='quest/extra']",
        ],
        "select": [
            ".btn-usual-select",
            ".btn-select",
        ],
        "next": [
            ".cnt-result .btn-result-next",
            ".btn-result-next",
            ".btn-settlement-next",
            ".btn-usual-next",
            ".btn-command-next",
            ".btn-control[data-buton-name='Next']",
            ".btn-next:not(.btn-next-super)",
            # NOTE: .btn-link-item removed - it matches .btn-next-super (GBF Charge Attack button)
            # during active Full Auto combat, causing the bot to click the Charge Attack mid-battle.
        ],
        "salute_participants": [
            ".btn-salute",
            ".btn-salute-participants",
            ".prt-salute",
            ".btn-usual-ok",
        ],
        "party_wipe_indicator": [
            ".btn-use-elixir",
            ".btn-revive",
            ".btn-retreat",
            ".btn-usual-cancel",
        ],
        "no_loot": [
            ".prt-no-loot",
            ".cnt-no-loot",
            ".txt-no-loot",
            ".btn-usual-ok",
        ],
        "loot_collected": [
            ".btn-again",
            ".btn-retry",
            ".btn-control[data-buton-name='Backup Requests']",
            ".prt-reward-list",
            ".prt-result-win",
        ],
        "battle_concluded": [
            ".btn-usual-ok",
            ".btn-result-next",
        ],
        "exp_gained": [
            ".btn-usual-ok",
            ".btn-result-next",
            ".btn-settlement-next",
            ".prt-exp-result",
        ],
        "go": [
            ".btn-usual-go",
            ".btn-go",
        ],
        "start": [
            ".btn-usual-start",
            ".btn-start",
        ],
        "salute": [
            ".btn-salute",
        ],
        "leave": [
            ".btn-leave",
        ],
    }

    # JS template for robust element clicking
    _CLICK_JS_TEMPLATE = r"""(() => {
        let selectors = %SELECTORS_JSON%;
        let customAction = %CUSTOM_ACTION_JSON%;
        let buttonKey = %BUTTON_KEY_JSON%;

        if (customAction === '__CUSTOM_TAB_RECENT__') {
            // Try by id first (#tab-multi is the Recent tab on Backup Requests page)
            let recentEl = document.querySelector('#tab-multi');
            if (!recentEl) {
                for (let el of document.querySelectorAll('.btn-tabs')) {
                    if ((el.innerText || '').trim().toLowerCase() === 'recent') { recentEl = el; break; }
                }
            }
            if (recentEl && recentEl.offsetParent !== null) {
                if (window.$) { try { $(recentEl).trigger('tap'); } catch(e){} }
                recentEl.click();
                return {success: true, tag: recentEl.tagName, cls: recentEl.className, text: 'Recent'};
            }
            return {success: false};
        }

        if (customAction === '__CUSTOM_TAB_FINDER__') {
            // Try by id first (#tab-search is the Finder tab on Backup Requests page)
            let finderEl = document.querySelector('#tab-search');
            if (!finderEl) {
                for (let el of document.querySelectorAll('.btn-tabs')) {
                    if ((el.innerText || '').trim().toLowerCase() === 'finder') { finderEl = el; break; }
                }
            }
            if (finderEl && finderEl.offsetParent !== null) {
                if (window.$) { try { $(finderEl).trigger('tap'); } catch(e){} }
                finderEl.click();
                return {success: true, tag: finderEl.tagName, cls: finderEl.className, text: 'Finder'};
            }
            return {success: false};
        }

        function isElementVisible(el) {
            if (!el) return false;
            if (el.classList.contains('display-off') || el.classList.contains('pop-hide') || el.classList.contains('is-hide') || el.classList.contains('hidden')) {
                return false;
            }
            if (el.closest('.display-off, .pop-hide, .is-hide, .hidden, [style*="display: none"]')) {
                return false;
            }
            if (typeof el.checkVisibility === 'function') {
                if (!el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})) return false;
            } else {
                if (el.offsetParent === null) return false;
                let s = window.getComputedStyle(el);
                if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
            }
            let r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
        }

        function isSafeTarget(el) {
            if (buttonKey !== 'raid' && buttonKey !== 'raid_flat' && buttonKey !== 'raid_bouncing') {
                return true;
            }

            const classes = `${el.className || ''}`.toLowerCase();
            const destinations = [
                el.getAttribute('href'),
                el.getAttribute('data-href'),
                el.getAttribute('data-location-href')
            ].filter(Boolean).map(value => `${value}`.toLowerCase());

            // Pending-results controls also contain "quest/assist" in their destination.
            // They must never be accepted as the Backup Requests button.
            if (classes.includes('btn-unconfirmed-result') || classes.includes('flow-unclaimed') ||
                    classes.includes('btn-unclaimed') ||
                    destinations.some(value => value.includes('assist/unclaimed'))) {
                return false;
            }

            return true;
        }

        let target = null;
        for (let sel of selectors) {
            let els = document.querySelectorAll(sel);
            for (let el of els) {
                if (isElementVisible(el) && isSafeTarget(el)) {
                    target = el;
                    break;
                }
            }
            if (target) break;
        }

        if (!target) return {success: false};

        // Scroll into view if needed
        try {
            target.scrollIntoView({block: 'center', behavior: 'instant'});
        } catch(e) {}

        let rect = target.getBoundingClientRect();
        let cx = rect.left + rect.width / 2;
        let cy = rect.top + rect.height / 2;

        // Dispatch full sequence of touch and mouse events
        ['touchstart', 'touchend', 'mousedown', 'mouseup', 'click'].forEach(evtName => {
            try {
                let ev = null;
                if (evtName.startsWith('touch')) {
                    let t = new Touch({
                        identifier: Date.now(),
                        target: target,
                        clientX: cx,
                        clientY: cy,
                        radiusX: 10,
                        radiusY: 10,
                        rotationAngle: 0,
                        force: 1
                    });
                    ev = new TouchEvent(evtName, {
                        bubbles: true,
                        cancelable: true,
                        touches: [t],
                        targetTouches: [t],
                        changedTouches: [t]
                    });
                } else {
                    ev = new MouseEvent(evtName, {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: cx,
                        clientY: cy
                    });
                }
                if (ev) target.dispatchEvent(ev);
            } catch(e) {}
        });

        // Zepto/jQuery tap trigger
        if (window.$) {
            try { $(target).trigger('tap'); } catch(e) {}
        }

        // Native click
        try { target.click(); } catch(e) {}

        return {
            success: true,
            tag: target.tagName,
            cls: target.className,
            text: (target.innerText || '').slice(0, 30).trim()
        };
    })()"""


    @staticmethod
    def element_exists(name: str) -> bool:
        """Check if an element or condition exists and is visible in the DOM without clicking it.

        Args:
            name (str): Identifier (e.g. 'party_wipe_indicator', 'salute_participants', 'no_loot',
                        'loot_collected', 'battle_concluded', 'exp_gained', or any button selector key).

        Returns:
            bool: True if element/condition exists and is visible, False otherwise.
        """
        from bot.game import Game

        key = name.lower().strip()

        # Special presence checks for combat and result states
        if key == "party_wipe_indicator":
            res = Game.evaluate_dom_js("""(() => {
                if (window.stage && window.stage.gGameStatus && window.stage.gGameStatus.player) {
                    let player = window.stage.gGameStatus.player;
                    if (player.param && player.param.length > 0) {
                        let alive = player.param.some(p => p.alive !== 0 && p.hp > 0);
                        if (!alive) return true;
                    }
                }
                let pop = document.querySelector('.pop-usual, .prt-popup-body, .txt-popup-title, .prt-popup-header');
                if (pop && pop.offsetParent !== null) {
                    let text = (document.body ? document.body.innerText || '' : '').toLowerCase();
                    if (text.includes('party was wiped out') || text.includes('all members defeated') ||
                        text.includes('全滅') || text.includes('elixir to come back') || text.includes('use an elixir')) {
                        return true;
                    }
                }
                let btn = document.querySelector('.btn-use-elixir, .btn-revive');
                return Boolean(btn && btn.offsetParent !== null);
            })()""")
            return bool(res)

        if key == "salute_participants":
            res = Game.evaluate_dom_js("""(() => {
                let el = document.querySelector('.btn-salute, .btn-salute-participants, .prt-salute, .pop-salute');
                if (el && el.offsetParent !== null) return true;
                let popHeader = document.querySelector('.prt-popup-header, .pop-title, .txt-popup-title');
                if (popHeader && popHeader.offsetParent !== null) {
                    let t = (popHeader.innerText || '').toLowerCase();
                    if (t.includes('salute') || t.includes('participants') || t.includes('挨拶')) return true;
                }
                return false;
            })()""")
            return bool(res)

        if key == "no_loot":
            res = Game.evaluate_dom_js("""(() => {
                let hash = window.location.hash || '';
                if (hash.includes('no_loot')) return true;
                let text = (document.body ? document.body.innerText || '' : '');
                if (text.includes('No loot to collect') || text.includes('no loot') || text.includes('報酬はありません')) {
                    return true;
                }
                let el = document.querySelector('.prt-no-loot, .cnt-no-loot, .txt-no-loot');
                return Boolean(el && el.offsetParent !== null);
            })()""")
            return bool(res)

        if key == "loot_collected":
            res = Game.evaluate_dom_js("""(() => {
                let hash = window.location.hash || '';
                let pop = document.querySelector('.pop-usual, .pop-show, .pop-friend-request');
                let isPopupVisible = pop && pop.offsetParent !== null && window.getComputedStyle(pop).display !== 'none';
                if (isPopupVisible) return false;

                let again = document.querySelector('.btn-again, .btn-retry');
                if (again && again.offsetParent !== null) return true;

                if (hash.includes('result')) {
                    let hasResultEl = document.querySelector('[class*="cnt-result"], .prt-result-head, .prt-reward-list, .prt-reward-multi, .prt-item-list, .prt-result-report, .prt-result-rank, .btn-control');
                    if (hasResultEl && hasResultEl.offsetParent !== null) return true;
                }
                return false;
            })()""")
            return bool(res)

        if key == "battle_concluded":
            res = Game.evaluate_dom_js("""(() => {
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
            return bool(res)

        if key == "exp_gained":
            res = Game.evaluate_dom_js("""(() => {
                let hash = window.location.hash || '';
                if (hash.includes('result')) return true;
                let el = document.querySelector('.prt-result-head, [class*="cnt-result"], .prt-exp-result');
                return Boolean(el && el.offsetParent !== null);
            })()""")
            return bool(res)

        selectors = DomClicker.BUTTON_SELECTORS.get(key)
        if not selectors:
            return False

        clean_selectors = [s for s in selectors if not s.startswith('__CUSTOM_')]
        if not clean_selectors:
            return False

        js = """(() => {
            let selectors = %SELECTORS_JSON%;
            function isElementVisible(el) {
                if (!el) return false;
                if (el.classList.contains('display-off') || el.classList.contains('pop-hide') || el.classList.contains('is-hide') || el.classList.contains('hidden')) return false;
                if (el.closest('.display-off, .pop-hide, .is-hide, .hidden, [style*="display: none"]')) return false;
                if (typeof el.checkVisibility === 'function') {
                    if (!el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})) return false;
                } else {
                    if (el.offsetParent === null) return false;
                    let s = window.getComputedStyle(el);
                    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
                }
                let r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0;
            }
            for (let sel of selectors) {
                let els = document.querySelectorAll(sel);
                for (let el of els) {
                    if (isElementVisible(el)) return true;
                }
            }
            return false;
        })()""".replace("%SELECTORS_JSON%", json.dumps(clean_selectors))

        return bool(Game.evaluate_dom_js(js))

    @staticmethod
    def has_selector(button_name: str) -> bool:
        """Check if button has a DOM selector or action mapped.

        Args:
            button_name (str): Button identifier.

        Returns:
            bool: True if mapped, False otherwise.
        """
        btn_key = button_name.lower().strip()
        if btn_key in ("reload", "reload_backup", "play_again"):
            return True
        return btn_key in DomClicker.BUTTON_SELECTORS

    @staticmethod
    def click_button(button_name: str) -> bool:
        """Attempt to find and click a button via Chrome DevTools Protocol DOM execution.

        Args:
            button_name (str): Button identifier (e.g. 'ok', 'cancel', 'close', 'attack').

        Returns:
            bool: True if button was found and clicked via DOM. False if not found or failed.
        """
        from bot.game import Game

        btn_key = button_name.lower().strip()

        # Handle special direct actions
        if btn_key in ("reload", "reload_backup"):
            res = Game.evaluate_dom_js("""(() => {
                if (window.Game && window.Game.view && typeof window.Game.view.reload === 'function') {
                    try { window.Game.view.reload(); return true; } catch(e) {}
                }
                window.location.reload();
                return true;
            })()""")
            if res:
                MessageLog.print_message(f"[DOM] Triggered reload via CDP.")
                return True
            return False

        if btn_key == "play_again":
            # Delegate to specialized play_again handler which checks internal Backbone routes
            return Game.find_and_click_play_again()

        # Look up candidate selectors
        selectors = DomClicker.BUTTON_SELECTORS.get(btn_key)
        if not selectors:
            return False

        custom_action = None
        if len(selectors) == 1 and selectors[0].startswith("__CUSTOM_"):
            custom_action = selectors[0]
            selectors_list = []
        else:
            selectors_list = selectors

        js = DomClicker._CLICK_JS_TEMPLATE.replace(
            "%SELECTORS_JSON%", json.dumps(selectors_list)
        ).replace(
            "%CUSTOM_ACTION_JSON%", json.dumps(custom_action)
        ).replace(
            "%BUTTON_KEY_JSON%", json.dumps(btn_key)
        )

        res = Game.evaluate_dom_js(js)
        if isinstance(res, dict) and res.get("success"):
            desc = res.get("cls") or res.get("text") or res.get("tag") or btn_key
            if Settings.debug_mode:
                MessageLog.print_message(f"[DOM] Clicked button '{button_name}' via DOM ({desc}).")
            return True

        return False
