import json
import random
from dataclasses import dataclass
from typing import Optional
from utils.settings import Settings
from utils.message_log import MessageLog
from utils.image_utils import ImageUtils
from utils.mouse_utils import MouseUtils
from bot.combat_mode import CombatMode


class RaidException(Exception):
    def __init__(self, message):
        super().__init__(message)


@dataclass(frozen = True)
class RaidJoinResult:
    """Outcome of selecting a raid card and validating the immediate join response."""

    status: str
    card_key: Optional[str] = None
    card_key_quality: Optional[str] = None
    detail: Optional[str] = None

    @property
    def joined(self) -> bool:
        return self.status == "joined"


@dataclass(frozen = True)
class RaidRefreshResult:
    """Result of activating Finder refresh and observing the subsequent card snapshot."""

    status: str
    detail: Optional[str] = None

    @property
    def changed(self) -> bool:
        return self.status == "changed"

    def __bool__(self) -> bool:
        # An unchanged response still proves the refresh control was activated safely. Callers
        # may select a different blacklisted-safe card from that same generation.
        return self.status in ("changed", "unchanged")


class Raid:
    """
    Provides the navigation and any necessary utility functions to handle the Raid game mode.
    """

    _raids_joined = 0
    _last_selected_raid_key = None
    _last_selected_raid_key_quality = None
    _last_selected_raid_name = None
    _finder_tab_verified_via_dom = False

    # Five failed joins are enough to trigger a recovery cycle, but a temporary burst of
    # stale Backup Requests must not terminate the whole farming session immediately.
    _MAX_JOIN_ATTEMPTS_PER_CYCLE = 5
    _MAX_STALE_RECOVERY_CYCLES = 2
    _MAX_LIST_REFRESHES_PER_JOIN = 5
    _STALE_RECOVERY_BASE_WAIT_SECONDS = 15.0

    # The mission labels exposed by this app do not always match the names rendered on
    # modern Backup Request cards. Keep the public/configuration label stable while using
    # the current in-game name for Finder's wrong-filter safety check.
    _FINDER_RAID_NAME_OVERRIDES = {
        "Lvl 100 Tiamat Omega Ayr": "Tiamat Aura Omega (Impossible)",
        "Lvl 100 Colossus Omega": "Colossus Ira Omega (Impossible)",
        "EX Zhuque": "Lvl 60 Zhuque",
        "EX Xuanwu": "Lvl 60 Xuanwu",
        "EX Baihu": "Lvl 60 Baihu",
        "EX Qinglong": "Lvl 60 Qinglong",
    }

    _GRID_SECTIONS = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12], [13, 14, 15]]

    # List of supported raids in the format of "X,Y,Z":
    # X = 1 for Standard tab or 2 for Impossible tab.
    # Y = Position in the 3xN grid reading from left to right, top to bottom.
    # Z = Position in the list reading from top to bottom.
    _list_of_raids = {
        ########## Standard Tab ##########
        # 2 stars
        "Lvl 50 Tiamat Omega": "1,2,1",
        "Lvl 70 Colossus Omega": "1,2,2",
        "Lvl 60 Leviathan Omega": "1,2,3",
        "Lvl 60 Yggdrasil Omega": "1,2,4",
        "Lvl 75 Luminiera Omega": "1,2,5",
        "Lvl 75 Celeste Omega": "1,2,6",

        # 3 stars
        "Lvl 100 Athena": "1,3,1",
        "Lvl 100 Grani": "1,3,2",
        "Lvl 100 Baal": "1,3,3",
        "Lvl 100 Garuda": "1,3,4",
        "Lvl 100 Odin": "1,3,5",
        "Lvl 100 Lich": "1,3,6",

        # 4 stars
        "Lvl 100 Grand Order": "1,4,1",
        "Lvl 100 Proto Bahamut": "1,4,2",
        "Lvl 100 Huanglong": "1,4,3",
        "Lvl 100 Qilin": "1,4,4",

        # 5 stars
        "Lvl 100 Michael": "1,5,1",
        "Lvl 100 Gabriel": "1,5,2",
        "Lvl 100 Uriel": "1,5,3",
        "Lvl 100 Raphael": "1,5,4",

        # 6 stars
        "Lvl 150 Ultimate Bahamut": "1,6,1",

        ########## Impossible Tab ##########
        # 1 stars
        "Lvl 100 Tiamat Omega Ayr": "2,1,1",
        "Lvl 100 Colossus Omega": "2,1,2",
        "Lvl 100 Leviathan Omega": "2,1,3",
        "Lvl 100 Yggdrasil Omega": "2,1,4",
        "Lvl 100 Luminiera Omega": "2,1,5",
        "Lvl 100 Celeste Omega": "2,1,6",

        # 2 stars
        "Lvl 120 Shiva": "2,2,1",
        "Lvl 120 Europa": "2,2,2",
        "Lvl 120 Godsworn Alexiel": "2,2,3",
        "Lvl 120 Grimnir": "2,2,4",
        "Lvl 120 Metatron": "2,2,5",
        "Lvl 120 Avatar": "2,2,6",
        "Lvl 110 Rose Queen": "2,2,7",
        "Lvl 120 Atum": "2,3,1",
        "Lvl 120 Tefnut": "2,3,2",
        "Lvl 120 Bennu": "2,3,3",
        "Lvl 120 Ra": "2,3,4",
        "Lvl 120 Horus": "2,3,5",
        "Lvl 120 Osiris": "2,3,6",

        # 3 stars
        "Lvl 150 Tiamat Malice": "2,4,1",
        "Lvl 150 Leviathan Malice": "2,4,2",
        "Lvl 150 Phronesis": "2,4,3",
        "Lvl 150 Luminiera Malice": "2,4,4",
        "Lvl 150 Anima-Animus Core": "2,4,5",

        # 4 stars
        "Huanglong & Qilin (Impossible)": "2,5,1",
        "Lvl 150 Lucilius": "2,5,2",
        "The Four Primarchs": "2,5,3",
        "Lvl 200 Lindwurm": "2,5,4",

        # 5 stars
        "Lvl 200 Wilnas": "2,6,1",
        "Lvl 200 Wamdus": "2,6,2",
        "Lvl 200 Galleon": "2,6,3",
        "Lvl 200 Ewiyar": "2,6,4",
        "Lvl 200 Lu Woh": "2,6,5",
        "Lvl 200 Fediel": "2,6,6",

        # 6 stars
        "Lvl 150 Proto Bahamut": "2,7,1",
        "Lvl 200 Akasha": "2,7,2",
        "Lvl 200 Grand Order": "2,7,3",
        "Lvl 200 Ultimate Bahamut": "2,7,4",

        # 7 stars
        "Lvl 250 Lucilius": "2,8,1",
        "Lvl 250 Belial": "2,8,2",
        "Lvl 250 Beelzebub": "2,8,3",

        # 8 stars
        "Lvl 275 Mugen": "2,9,1",
        "Lvl 275 Diaspora": "2,9,2",
        "Lvl 275 Siegfried": "2,9,3",
        "Lvl 275 Seofon": "2,9,4",
        "Lvl 275 Agastia": "2,9,5",
        "Lvl 300 Super Ultimate Bahamut": "2,10,1",

    }

    @staticmethod
    def _check_for_joined_raids():
        """Check and update the number of raids currently joined. (Disabled)

        Returns:
            None
        """
        return None

    @staticmethod
    def _clear_joined_raids():
        """Begin process to wait out the joined raids if there are 3 or more currently active. (Disabled)

        Returns:
            None
        """
        return None

    @staticmethod
    def _finder_raid_name(mission_name: str) -> str:
        """Return the in-game Finder name corresponding to a configured mission label."""
        return Raid._FINDER_RAID_NAME_OVERRIDES.get(mission_name, mission_name)

    @staticmethod
    def _raid_card_dom_script(excluded_keys = None, action: str = "snapshot") -> str:
        """Build the DOM scanner used for both card snapshots and a single card click.

        Raid cards have appeared as both ``.lis-raid`` wrappers and ``.btn-multi-raid``
        buttons across game versions. The scanner canonicalizes wrapper/child pairs, derives
        the strongest available per-request key, and never activates more than one DOM event.
        """
        excluded_json = json.dumps(sorted(excluded_keys or set()))
        action_json = json.dumps(action)
        expected_mission_json = json.dumps(
            Raid._finder_raid_name(Settings.mission_name or "")
        )

        template = r"""(() => {
            const excluded = new Set(%EXCLUDED_KEYS%);
            const action = %ACTION%;
            const expectedMission = %EXPECTED_MISSION%;
            const hash = window.location.hash || '';

            if (!hash.startsWith('#quest/assist') || hash.startsWith('#quest/assist/unclaimed')) {
                return {status: 'wrong_route', hash: hash, cards: []};
            }

            function rendered(el) {
                if (!el || !el.isConnected) return false;
                if (el.closest("template,[aria-hidden='true'],.display-off,.pop-hide,.is-hide,.hidden")) return false;
                try {
                    if (el.checkVisibility && !el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})) {
                        return false;
                    }
                } catch (_) {}
                for (let p = el; p; p = p.parentElement) {
                    const style = window.getComputedStyle(p);
                    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) {
                        return false;
                    }
                }
                const rect = el.getBoundingClientRect();
                return rect.width > 1 && rect.height > 1;
            }

            function cardRoots() {
                const legacy = [...document.querySelectorAll('.lis-raid')].filter(rendered);
                const modern = [...document.querySelectorAll('.btn-multi-raid')].filter(rendered);
                const roots = legacy.length ? [...legacy] : [...modern];

                for (const card of modern) {
                    if (!roots.some(root => root === card || root.contains(card) || card.contains(root))) {
                        roots.push(card);
                    }
                }

                return roots.filter((card, index, all) =>
                    !all.slice(0, index).some(root =>
                        root === card || root.contains(card) || card.contains(root)
                    )
                );
            }

            function valuesFor(root, pattern) {
                const values = [];
                const nodes = [root, ...root.querySelectorAll('*')].slice(0, 120);
                for (const node of nodes) {
                    for (const attr of node.attributes || []) {
                        const name = attr.name.toLowerCase();
                        const value = (attr.value || '').trim();
                        if (value && pattern.test(name)) values.push(`${name}=${value}`);
                    }
                }
                return [...new Set(values)].sort();
            }

            function stableLabel(root) {
                const selectors = [
                    '.txt-raid-name', '.txt-boss-name', '.txt-chapter-name',
                    '.txt-request-name', '.txt-player-name', '.txt-user-name', '.txt-owner-name'
                ].join(',');
                let text = [...root.querySelectorAll(selectors)]
                    .map(el => (el.textContent || '').trim())
                    .filter(Boolean)
                    .join('|');
                if (!text) text = root.getAttribute('data-chapter-name') || root.textContent || '';
                return text
                    .replace(/\b\d{1,2}:\d{2}(?::\d{2})?\b/g, '')
                    .replace(/\b\d+\s*%/g, '')
                    .replace(/\b\d+\s*\/\s*\d+\b/g, '')
                    .replace(/\b\d+\s*(seconds?|secs?|minutes?|mins?)\b/gi, '')
                    .replace(/\s+/g, ' ')
                    .trim();
            }

            function explicitRaidName(root) {
                const selectors = [
                    '.txt-raid-name', '.txt-boss-name', '.txt-chapter-name',
                    '.txt-request-name', '.txt-quest-name'
                ].join(',');
                const text = [...root.querySelectorAll(selectors)]
                    .map(el => (el.textContent || '').trim())
                    .find(Boolean);
                return (text || root.getAttribute('data-chapter-name') ||
                    root.getAttribute('data-raid-name') || '').replace(/\s+/g, ' ').trim();
            }

            function normalizeRaidName(value) {
                return (value || '')
                    .normalize('NFKC')
                    .toLowerCase()
                    .replace(/\b(?:lvl|level)\s*\d+\b/g, ' ')
                    .replace(/[^\p{L}\p{N}]+/gu, ' ')
                    .replace(/\s+/g, ' ')
                    .trim();
            }

            function digest(value) {
                let hashValue = 0x811c9dc5;
                for (let i = 0; i < value.length; i++) {
                    hashValue ^= value.charCodeAt(i);
                    hashValue = Math.imul(hashValue, 0x01000193);
                }
                return (hashValue >>> 0).toString(16).padStart(8, '0');
            }

            const roots = cardRoots();
            let cards = roots.map((root, index) => {
                const strong = valuesFor(
                    root,
                    /^data-(battle-key|battle-id|raid-id|raid-instance-id|assist-id|request-id)$/
                );
                const compound = valuesFor(
                    root,
                    /^data-(host-user-id|owner-user-id|user-id|quest-id|chapter-id|chapter-name|raid-name)$/
                );
                const hrefs = [...root.querySelectorAll('a[href]')]
                    .map(el => el.getAttribute('href'))
                    .filter(value => value && /(raid|assist|supporter)/i.test(value));
                const label = stableLabel(root);
                const raidName = explicitRaidName(root);
                const normalizedExpected = normalizeRaidName(expectedMission);
                const normalizedRaidName = normalizeRaidName(raidName);
                const missionMatch = !normalizedExpected || !normalizedRaidName ||
                    normalizedRaidName.includes(normalizedExpected) ||
                    normalizedExpected.includes(normalizedRaidName);
                const material = strong.length
                    ? strong.join('|')
                    : (compound.length || hrefs.length)
                        ? [...compound, ...hrefs, label].join('|')
                        : `${label}|${root.className || ''}`;
                const quality = strong.length ? 'strong' : (compound.length || hrefs.length) ? 'compound' : 'weak';
                const target = root.matches('.btn-multi-raid,.prt-button-cover')
                    ? root
                    : [...root.querySelectorAll('.btn-multi-raid,.prt-button-cover')].find(rendered) || root;
                const disabledSelector = '.disabled,.disable,.is-disable,[aria-disabled="true"]';
                const disabled = root.matches(disabledSelector) || target.matches(disabledSelector);
                return {
                    root: root,
                    target: target,
                    index: index,
                    baseKey: `${quality}:${digest(material)}`,
                    quality: quality,
                    name: (raidName || label).slice(0, 120),
                    explicitName: raidName.slice(0, 120),
                    missionMatch: missionMatch,
                    eligible: !disabled
                };
            });

            // If the same strong request ID appears twice in the DOM, it is still one server raid
            // instance. Keep one canonical card rather than downgrading it to two retryable keys.
            const preferredStrongCards = new Map();
            for (const card of cards) {
                if (card.quality !== 'strong') continue;
                const current = preferredStrongCards.get(card.baseKey);
                if (!current || (!current.eligible && card.eligible)) {
                    preferredStrongCards.set(card.baseKey, card);
                }
            }
            cards = cards.filter(card =>
                card.quality !== 'strong' || preferredStrongCards.get(card.baseKey) === card
            );

            const totals = new Map();
            for (const card of cards) totals.set(card.baseKey, (totals.get(card.baseKey) || 0) + 1);
            const occurrences = new Map();
            for (const card of cards) {
                const occurrence = occurrences.get(card.baseKey) || 0;
                occurrences.set(card.baseKey, occurrence + 1);
                if (card.quality !== 'strong' && totals.get(card.baseKey) > 1) {
                    card.key = `${card.baseKey}@${occurrence}`;
                    card.quality = 'generation';
                } else {
                    card.key = card.baseKey;
                }
            }

            const probe = window.__gbfaRaidProbe || (window.__gbfaRaidProbe = {
                epoch: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`,
                ids: new WeakMap(),
                next: 1
            });
            const domIds = cards.map(card => {
                if (!probe.ids.has(card.root)) probe.ids.set(card.root, probe.next++);
                return probe.ids.get(card.root);
            });
            const contentSig = digest(cards.map(card => `${card.key}:${card.eligible ? 1 : 0}`).join('\x1f'));
            const domSig = `${probe.epoch}:${domIds.join(',')}`;
            const publicCards = cards.map(card => ({
                key: card.key,
                quality: card.quality,
                name: card.name,
                missionMatch: card.missionMatch,
                eligible: card.eligible
            }));

            if (action === 'snapshot') {
                return {
                    status: cards.length ? 'ready' : 'no_cards',
                    contentSig: contentSig,
                    domSig: domSig,
                    cards: publicCards
                };
            }

            const namedCards = cards.filter(card => card.explicitName);
            if (normalizeRaidName(expectedMission) && namedCards.length &&
                    !namedCards.some(card => card.missionMatch)) {
                return {
                    status: 'wrong_filter',
                    expected: expectedMission,
                    visibleNames: [...new Set(namedCards.map(card => card.explicitName))].slice(0, 10),
                    contentSig: contentSig,
                    domSig: domSig,
                    cards: publicCards
                };
            }

            const chosen = cards.find(card => card.eligible && card.missionMatch && !excluded.has(card.key));
            if (!chosen) {
                return {
                    status: cards.length ? 'all_excluded' : 'no_cards',
                    contentSig: contentSig,
                    domSig: domSig,
                    cards: publicCards
                };
            }

            const target = chosen.target;
            try { target.scrollIntoView({block: 'center', behavior: 'auto'}); } catch (_) {}

            let activatedBy = 'click';
            if (window.$ && typeof window.$(target).trigger === 'function') {
                try {
                    window.$(target).trigger('tap');
                    activatedBy = 'tap';
                } catch (_) {
                    target.click();
                }
            } else {
                target.click();
            }

            return {
                status: 'clicked',
                key: chosen.key,
                quality: chosen.quality,
                name: chosen.name,
                contentSig: contentSig,
                domSig: domSig,
                activatedBy: activatedBy,
                cards: publicCards
            };
        })()"""

        return template.replace("%EXCLUDED_KEYS%", excluded_json) \
            .replace("%ACTION%", action_json) \
            .replace("%EXPECTED_MISSION%", expected_mission_json)

    @staticmethod
    def _read_visible_raid_cards() -> dict:
        """Return a read-only snapshot of visible Finder cards and their stable keys."""
        from bot.game import Game

        if not getattr(Settings, "enable_dom_clicking", False):
            return {"status": "dom_disabled", "cards": []}
        result = Game.evaluate_dom_js(Raid._raid_card_dom_script(action = "snapshot"))
        if not isinstance(result, dict):
            return {"status": "dom_error", "cards": []}
        result.setdefault("cards", [])
        return result

    @staticmethod
    def _select_raid_card(excluded_keys = None) -> dict:
        """Click one visible card that has not failed in this run."""
        from bot.game import Game

        Raid._last_selected_raid_key = None
        Raid._last_selected_raid_key_quality = None
        Raid._last_selected_raid_name = None

        if not getattr(Settings, "enable_dom_clicking", False):
            return {"status": "dom_error", "cards": []}
        result = Game.evaluate_dom_js(
            Raid._raid_card_dom_script(excluded_keys = excluded_keys, action = "click")
        )
        if not isinstance(result, dict):
            return {"status": "dom_error", "cards": []}

        if result.get("status") == "clicked":
            Raid._last_selected_raid_key = result.get("key")
            Raid._last_selected_raid_key_quality = result.get("quality")
            Raid._last_selected_raid_name = result.get("name")
        return result

    @staticmethod
    def _ensure_finder_tab(polls: int = 6, poll_interval: float = 0.5,
                           allow_image_fallback: bool = True) -> bool:
        """Ensure Backup Requests is showing Finder, never the unfiltered Recent tab."""
        from bot.game import Game

        Raid._finder_tab_verified_via_dom = False

        probe_js = r"""(() => {
            const hash = window.location.hash || '';
            if (!hash.startsWith('#quest/assist') || hash.startsWith('#quest/assist/unclaimed')) {
                return {status: 'wrong_route', hash: hash};
            }

            function rendered(el) {
                if (!el || !el.isConnected) return false;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' &&
                    Number(style.opacity) !== 0 && rect.width > 1 && rect.height > 1;
            }

            const finder = [...document.querySelectorAll('#tab-search,.btn-tabs')]
                .find(el => rendered(el) &&
                    (el.id === 'tab-search' || (el.innerText || '').trim().toLowerCase() === 'finder'));
            if (!finder) return {status: 'not_ready'};

            const classText = `${finder.className || ''} ${finder.parentElement?.className || ''}`;
            const selected = finder.getAttribute('aria-selected') === 'true' ||
                /\b(active|selected|current|on)\b/.test(classText);
            return {status: selected ? 'ready' : 'needs_click'};
        })()"""
        activate_js = r"""(() => {
            const finder = [...document.querySelectorAll('#tab-search,.btn-tabs')]
                .find(el => el.offsetParent !== null &&
                    (el.id === 'tab-search' || (el.innerText || '').trim().toLowerCase() === 'finder'));
            if (!finder) return false;
            if (window.$ && typeof window.$(finder).trigger === 'function') {
                try {
                    window.$(finder).trigger('tap');
                    return true;
                } catch (_) {}
            }
            finder.click();
            return true;
        })()"""

        if getattr(Settings, "enable_dom_clicking", False):
            activation_attempted = False
            for _ in range(max(1, polls)):
                result = Game.evaluate_dom_js(probe_js)
                if isinstance(result, dict):
                    if result.get("status") == "ready":
                        Raid._finder_tab_verified_via_dom = True
                        return True
                    if result.get("status") == "wrong_route":
                        return False
                    if result.get("status") == "needs_click" and not activation_attempted:
                        activation_attempted = bool(Game.evaluate_dom_js(activate_js))
                        Game.wait(1.5 if activation_attempted else poll_interval)
                        continue
                Game.wait(poll_interval)

        if not allow_image_fallback:
            return False

        # Preserve legacy image-only mode when CDP is disabled/unavailable. The Finder image is
        # safe; never substitute the neighbouring Recent tab because that discards the saved filter.
        if Game.find_and_click_button(
                "raid_tab_finder", tries = 3, suppress_error = True,
                custom_confidence = 0.75):
            Game.wait(1.5)
            MessageLog.print_message("[RAID] Finder tab selected through the image fallback.")
            return True
        return False

    @staticmethod
    def _refresh_raid_list(previous_snapshot = None, polls: int = 12,
                           poll_interval: float = 0.5) -> RaidRefreshResult:
        """Refresh Finder once and confirm that its card DOM or content actually changed.

        The old implementation fell back to ``#tab-multi``, which is the Recent tab and can
        silently discard the user's Finder filter. This helper only uses the refresh control or
        switches to the Finder tab; otherwise the caller performs full navigation recovery.
        """
        from bot.game import Game

        if not getattr(Settings, "enable_dom_clicking", False):
            return RaidRefreshResult("failed", "DOM refresh is disabled; full navigation is required")

        before = previous_snapshot if isinstance(previous_snapshot, dict) else Raid._read_visible_raid_cards()
        refresh_js = r"""(() => {
            const hash = window.location.hash || '';
            if (!hash.startsWith('#quest/assist') || hash.startsWith('#quest/assist/unclaimed')) {
                return {status: 'wrong_route', hash: hash};
            }

            function rendered(el) {
                if (!el || !el.isConnected) return false;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' &&
                    Number(style.opacity) !== 0 && rect.width > 1 && rect.height > 1;
            }

            function activateOnce(el) {
                if (window.$ && typeof window.$(el).trigger === 'function') {
                    try {
                        window.$(el).trigger('tap');
                        return 'tap';
                    } catch (_) {}
                }
                el.click();
                return 'click';
            }

            const refresh = [...document.querySelectorAll('.btn-search-refresh')]
                .find(el => rendered(el) && !el.matches('.disabled,.disable,.is-disable,[aria-disabled="true"]'));
            if (refresh) {
                return {status: 'clicked', via: 'refresh', activation: activateOnce(refresh)};
            }
            return {status: 'not_ready'};
        })()"""

        # Finder can report selected before its toolbar finishes rendering. Poll briefly for the
        # dedicated refresh control instead of re-clicking Finder and pretending that was refresh.
        refresh_result = None
        for refresh_poll in range(6):
            refresh_result = Game.evaluate_dom_js(refresh_js)
            if isinstance(refresh_result, dict) and refresh_result.get("status") == "clicked":
                break
            if isinstance(refresh_result, dict) and refresh_result.get("status") == "wrong_route":
                break
            if refresh_poll < 5:
                Game.wait(poll_interval)

        if not isinstance(refresh_result, dict) or refresh_result.get("status") != "clicked":
            MessageLog.print_message("[RAID] Finder list could not be refreshed safely; full navigation recovery is required.")
            return RaidRefreshResult("failed", "refresh control was unavailable or the route was invalid")

        before_has_signature = bool(before.get("contentSig") or before.get("domSig"))
        for _ in range(max(1, polls)):
            Game.wait(poll_interval)
            after = Raid._read_visible_raid_cards()
            if after.get("status") == "no_cards":
                continue
            if after.get("status") != "ready":
                continue

            content_changed = after.get("contentSig") != before.get("contentSig")
            dom_changed = after.get("domSig") != before.get("domSig")
            identity_cards = list(before.get("cards") or []) + list(after.get("cards") or [])
            has_only_stable_identities = bool(identity_cards) and all(
                card.get("quality") in ("strong", "compound") for card in identity_cards
            )
            # A refresh commonly destroys and recreates the same DOM nodes. For stable request IDs,
            # domSig-only changes are therefore stale rerenders, not a new raid-card generation.
            reliable_dom_change = dom_changed and not has_only_stable_identities
            if not before_has_signature or content_changed or reliable_dom_change:
                MessageLog.print_message("[RAID] Finder refresh changed the visible raid-card snapshot.")
                return RaidRefreshResult("changed", f"activated via {refresh_result.get('via', 'unknown')}")

        MessageLog.print_message("[RAID] Finder refresh completed but the visible raid-card generation did not change.")
        return RaidRefreshResult("unchanged", f"activated via {refresh_result.get('via', 'unknown')}")

    @staticmethod
    def _remember_failed_raid(rejected_keys: set, transient_keys: set) -> None:
        """Blacklist the most recently selected card for the appropriate lifetime."""
        key = Raid._last_selected_raid_key
        if not key:
            MessageLog.print_message("[RAID] Ended raid had no DOM identity; the next retry will force a list refresh.")
            return

        rejected_keys.add(key)
        if Raid._last_selected_raid_key_quality != "strong":
            transient_keys.add(key)
        label = f" ({Raid._last_selected_raid_name})" if Raid._last_selected_raid_name else ""
        MessageLog.print_message(f"[RAID] Blacklisted ended raid card {key}{label} for subsequent retries.")

    @staticmethod
    def _join_raid(excluded_raid_keys = None) -> RaidJoinResult:
        """Select an untried Finder card and validate the immediate join response."""
        from bot.game import Game

        excluded_raid_keys = set(excluded_raid_keys or set())

        # Current location should be at the Backup Requests screen with the 'Recent' and 'Finder' tabs.
        # NOTE: The filter-setting process below (tab switching, Set Filters popup, clearing filters,
        # selecting difficulty tab, selecting the raid checkbox) has been intentionally skipped.
        # This relies on the game/browser remembering the previously-set Finder filters, so the
        # target raid is already showing in the list without needing to reconfigure filters.
        # If the correct raid does NOT reliably appear in the list without filtering, this section
        # will need the filter steps restored, along with corrected image assets for
        # raid_tab_finder / raid_set_filters / raid_filter_clear / raid_filter_1 /
        # raid_difficulty_standard / raid_difficulty_impossible / raid_select_difficulty / raid_filter_checkbox.

        # Wait for a usable card. Cards which already failed during this Raid.start() call are
        # excluded, so a stale Finder generation can never make us click the same instance again.
        tries = Raid._MAX_LIST_REFRESHES_PER_JOIN
        recovery_time = 10  # Reduced from 15 for faster cycling
        pending_recoveries = 0
        while tries > 0:
            # Check if "Check your pending battles" popup is currently visible on the screen
            _pending_popup_present = Game.evaluate_dom_js("""(() => {
                let popups = document.querySelectorAll('.pop-usual, .pop-show, .prt-popup-body, .txt-popup-body, [class*="pop-"]');
                for (let p of popups) {
                    if (p.offsetParent !== null && window.getComputedStyle(p).display !== 'none') {
                        let text = p.innerText || p.textContent || '';
                        if (text.toLowerCase().includes('pending')) {
                            return true;
                        }
                    }
                }
                return false;
            })()""")

            if _pending_popup_present:
                pending_recoveries += 1
                if pending_recoveries > 3:
                    return RaidJoinResult(
                        "navigation_error",
                        detail = "pending-battles popup persisted after three recovery attempts"
                    )
                MessageLog.print_message("[RAID] 'Check your pending battles' popup detected before joining raid. Clearing all pending battles...")
                Game.check_for_pending()
                # Return to Backup Requests through its route; pending recovery is DOM-only.
                already_at_assist = Game.evaluate_dom_js("""(() => {
                    let hash = window.location.hash || '';
                    return hash.includes('quest/assist') && !hash.includes('unclaimed');
                })()""")
                if not already_at_assist:
                    Game.evaluate_dom_js('window.location.hash = "#quest/assist"; true')
                    Game.wait(2.0)
                if not Raid._ensure_finder_tab(allow_image_fallback = False):
                    return RaidJoinResult(
                        "navigation_error",
                        detail = "Finder tab could not be restored after pending-battle recovery"
                    )
                continue

            selection = Raid._select_raid_card(excluded_keys = excluded_raid_keys)
            selection_status = selection.get("status")
            card_clicked = selection_status == "clicked"

            if selection_status == "wrong_route":
                return RaidJoinResult(
                    "navigation_error",
                    detail = f"Finder card scan ran on {selection.get('hash', 'an unknown route')}"
                )

            if selection_status == "wrong_filter":
                visible_names = ", ".join(selection.get("visibleNames") or []) or "unknown raids"
                return RaidJoinResult(
                    "wrong_filter",
                    detail = f"Finder expected {Settings.mission_name!r} but showed: {visible_names}"
                )

            # Image matching is only a compatibility fallback when the DOM scanner cannot see
            # cards. It must never run for all_excluded, otherwise it would click a blacklisted
            # first card and recreate the stale-card loop.
            if not card_clicked and selection_status in ("dom_error", "no_cards"):
                positions = ImageUtils.find_all("raid_time_remaining")
                MIN_Y_FOR_RAID_CARD = 300
                filtered_positions = [p for p in positions if p[1] >= MIN_Y_FOR_RAID_CARD]
                image_candidates = [
                    (point, f"image:{point[0]}:{point[1]}")
                    for point in filtered_positions
                    if f"image:{point[0]}:{point[1]}" not in excluded_raid_keys
                ]
                if image_candidates:
                    point, image_key = image_candidates[0]
                    Raid._last_selected_raid_key = image_key
                    Raid._last_selected_raid_key_quality = "weak"
                    Raid._last_selected_raid_name = "image fallback"
                    MouseUtils.move_and_click_point(point[0], point[1], "raid_time_remaining")
                    card_clicked = True

            if card_clicked:
                selected_label = Raid._last_selected_raid_name or Raid._last_selected_raid_key or "unknown card"
                MessageLog.print_message(f"[RAID] Selected raid card {selected_label}; validating join response...")

                # After joining, GBF may show one of at least two different popups that both block the
                # Summon Selection screen from appearing until dismissed:
                #   1. "EP is full. Use an item?" (Soul Balm/Soul Berry) - has a "Cancel" button to skip.
                #   2. "This raid battle has already ended." - only has "OK" button, NOT "Cancel".
                #   3. "Check your pending battles." - only has "OK" button.
                Game.wait(2.0)

                # Fast DOM-based detection of "This raid has already ended" popup.
                if Game.check_for_ended_raid():
                    MessageLog.print_message("[RAID] The raid that was just joined has already ended. Dismissing and looking for another raid...")
                    return RaidJoinResult(
                        "ended",
                        Raid._last_selected_raid_key,
                        Raid._last_selected_raid_key_quality,
                        "ended popup immediately after card selection"
                    )

                # Dismiss "Check your pending battles" popup if it appears right after joining.
                _pend_js_join = """(() => {
                    let popups = document.querySelectorAll(
                        '.pop-usual, .pop-show, .prt-popup-body, .txt-popup-body, [class*="pop-"]'
                    );
                    for (let p of popups) {
                        if (p.offsetParent !== null && window.getComputedStyle(p).display !== 'none') {
                            let text = p.innerText || p.textContent || '';
                            if (text.toLowerCase().includes('pending')) {
                                let okBtn = p.querySelector('.btn-usual-ok, .btn-ok, [class*="ok"]');
                                if (okBtn && okBtn.offsetParent !== null) {
                                    let activated = false;
                                    if (window.$ && typeof window.$(okBtn).trigger === 'function') {
                                        try {
                                            window.$(okBtn).trigger('tap');
                                            activated = true;
                                        } catch (_) {}
                                    }
                                    if (!activated) okBtn.click();
                                    return true;
                                }
                            }
                        }
                    }
                    return false;
                })()"""
                if Game.evaluate_dom_js(_pend_js_join):
                    pending_recoveries += 1
                    if pending_recoveries > 3:
                        return RaidJoinResult(
                            "navigation_error",
                            detail = "pending-battles popup kept returning after raid selection"
                        )
                    MessageLog.print_message("[RAID] 'Check your pending battles' popup appeared after trying to join raid.")
                    MessageLog.print_message("[RAID] Clearing all pending battles now...")
                    Game.wait(2.0)
                    Game.check_for_pending()

                    # Return to Backup Requests through its route; pending recovery is DOM-only.
                    already_at_assist = Game.evaluate_dom_js("""(() => {
                        let hash = window.location.hash || '';
                        return hash.includes('quest/assist') && !hash.includes('unclaimed');
                    })()""")
                    if not already_at_assist:
                        Game.evaluate_dom_js('window.location.hash = "#quest/assist"; true')
                        Game.wait(2.0)
                    if not Raid._ensure_finder_tab(allow_image_fallback = False):
                        return RaidJoinResult(
                            "navigation_error",
                            detail = "Finder tab could not be restored after clearing pending battles"
                        )
                    MessageLog.print_message("[RAID] Re-navigated to Backup Requests after clearing pending battles. Retrying raid join...")
                    continue

                if Game.find_and_click_button("cancel", tries = 5, suppress_error = True):
                    MessageLog.print_message("[RAID] Dismissed the 'EP is full' popup.")

                return RaidJoinResult(
                    "joined",
                    Raid._last_selected_raid_key,
                    Raid._last_selected_raid_key_quality,
                    "card selected without an immediate ended popup"
                )
            else:
                tries -= 1
                if tries <= 0:
                    return RaidJoinResult(
                        "no_raids",
                        detail = f"no usable cards after {Raid._MAX_LIST_REFRESHES_PER_JOIN} bounded Finder refresh attempts"
                    )

                sleep_time = random.randint(3, recovery_time)
                if selection_status == "all_excluded":
                    reason = "all visible raid cards were already rejected"
                else:
                    reason = "no usable raid cards were found"
                MessageLog.print_message(
                    f"[RAID] {reason.capitalize()}. Waiting {sleep_time} seconds before refreshing "
                    f"the Finder list. {tries} tries remaining."
                )
                Game.wait(sleep_time)
                refresh_result = Raid._refresh_raid_list(previous_snapshot = selection)
                if not refresh_result.changed:
                    return RaidJoinResult(
                        "navigation_error",
                        detail = f"Finder had no usable cards and refresh was {refresh_result.status}"
                    )

        return RaidJoinResult("no_raids", detail = "raid-card wait budget exhausted")

    @staticmethod
    def _navigate(excluded_raid_keys = None, force_refresh: bool = False) -> RaidJoinResult:
        """Navigate from Home to Finder, optionally refresh it, and select an untried card."""
        from bot.game import Game

        MessageLog.print_message(f"\n[RAID] Beginning process to navigate to the raid: {Settings.mission_name}...")

        # Head to the Home screen.
        Game.go_back_home(confirm_location_check = True)

        # Then navigate to the Quest screen.
        Game.find_and_click_button("quest")

        Game.wait(3.0)

        # Check for the "You retreated from the raid battle" popup.
        if ImageUtils.confirm_location("you_retreated_from_the_raid_battle", tries = 3):
            Game.find_and_click_button("ok")

        # Check for any Pending Battles popup. Its DOM-only recovery finishes at
        # #quest/assist, so do not navigate away through image-backed buttons afterward.
        pending_recovered = Game.check_for_pending()
        if pending_recovered:
            MessageLog.print_message(
                "[RAID] Pending rewards processed; continuing from Backup Requests through DOM."
            )
        else:
            # Now navigate to the Raid screen during ordinary full navigation.
            Game.find_and_click_button("raid")
            Game.wait(2.0)

        # NOTE: Skipping ImageUtils.confirm_location("raid") here intentionally.
        # That check matches against images/headers/raid_header.jpg, which has proven
        # fragile (scale mismatches and file corruption issues). Since find_and_click_button("raid")
        # already confirmed the Raid button was found and clicked (via raid_flat/raid_bouncing),
        # we proceed directly to the Backup Requests screen logic instead of re-verifying via the header image.

        # Joined raids check removed

        if not Raid._ensure_finder_tab(allow_image_fallback = not pending_recovered):
            return RaidJoinResult("navigation_error", detail = "Finder tab could not be confirmed after full navigation")

        if force_refresh:
            if Raid._finder_tab_verified_via_dom:
                MessageLog.print_message("[RAID] Full navigation reached Finder; requesting a fresh raid-card generation...")
                if not Raid._refresh_raid_list(previous_snapshot = Raid._read_visible_raid_cards()):
                    return RaidJoinResult("navigation_error", detail = "forced Finder refresh could not be activated safely")
            else:
                MessageLog.print_message(
                    "[RAID] CDP is unavailable; using the completed Home -> Finder navigation "
                    "as the legacy image-mode refresh boundary."
                )

        return Raid._join_raid(excluded_raid_keys = excluded_raid_keys)

    @staticmethod
    def _navigate_quick(force_refresh: bool = False, excluded_raid_keys = None) -> RaidJoinResult:
        """Navigasi cepat ke Backup Requests screen tanpa kembali ke Home.

        Digunakan pada run ke-2 dan seterusnya. Setelah loot collection selesai,
        bot masih berada di Quest Results screen dengan tombol "Backup Requests"
        yang sudah visible. Kita langsung klik tombol itu via DOM untuk kembali
        ke Backup Requests (raid finder) screen tanpa perlu Home → Quest → Raid.

        Jika tombol Backup Requests tidak ditemukan di DOM, fallback ke _navigate()
        yang penuh (via Home screen).

        Args:
            force_refresh (bool): If True, reload the raid list even when already at
                quest/assist. Use this after a retry-after-ended-raid so that stale
                (already-ended) cards are flushed from the list before the next pick.

        Returns:
            RaidJoinResult: Structured result from selecting and initially validating a raid.
        """
        from bot.game import Game

        MessageLog.print_message(f"\n[RAID] Quick navigation: clicking Backup Requests button directly from Quest Results screen...")

        Game.wait(2.0)

        already_at_assist_before_recovery = Game.evaluate_dom_js("""(() => {
            const hash = window.location.hash || '';
            return hash.startsWith('#quest/assist') && !hash.startsWith('#quest/assist/unclaimed');
        })()""")

        # Result content may already have been counted while a delayed progression overlay (such
        # as Extended Mastery Level) is still covering its navigation controls. Pending recovery
        # already returns to quest/assist, so do not invoke any result-screen fallback there.
        if not already_at_assist_before_recovery and Game.dismiss_post_battle_progression(max_attempts = 4):
            MessageLog.print_message("[RAID] Cleared post-battle progression overlay before quick navigation.")
            Game.wait(0.5)

        # Cek dan bersihkan pending battles sebelum coba join raid baru.
        # Ini mencegah slot pending penuh yang menyebabkan popup terus-menerus muncul
        # dan bot stuck dalam loop di Backup Requests screen.
        if Game.check_for_pending():
            MessageLog.print_message("[RAID] Pending battles cleared during quick navigation. Restoring Finder through DOM...")
            if not Raid._ensure_finder_tab(allow_image_fallback = False):
                return RaidJoinResult(
                    "navigation_error",
                    detail = "Finder tab could not be restored through DOM after pending-battle recovery"
                )
            if force_refresh and not Raid._refresh_raid_list(
                    previous_snapshot = Raid._read_visible_raid_cards()):
                return RaidJoinResult(
                    "navigation_error",
                    detail = "Finder DOM refresh failed after pending-battle recovery"
                )
            return Raid._join_raid(excluded_raid_keys = excluded_raid_keys)

        # Cek apakah bot sudah langsung ada di #quest/assist (Backup Requests screen).
        # Ini terjadi misalnya ketika popup Trophy/Achievement menutup dan game langsung navigasi ke sana.
        already_at_assist = Game.evaluate_dom_js("""(() => {
            let hash = window.location.hash || '';
            return hash.startsWith('#quest/assist') && !hash.startsWith('#quest/assist/unclaimed');
        })()""")

        if already_at_assist:
            if not Raid._ensure_finder_tab():
                MessageLog.print_message("[RAID] Finder tab could not be confirmed during quick navigation. Falling back to full navigation...")
                return Raid._navigate(
                    excluded_raid_keys = excluded_raid_keys,
                    force_refresh = force_refresh
                )
            if force_refresh:
                MessageLog.print_message("[RAID] Already at Backup Requests (force_refresh=True). Refreshing raid list to flush stale cards...")
                if not Raid._finder_tab_verified_via_dom:
                    return Raid._navigate(
                        excluded_raid_keys = excluded_raid_keys,
                        force_refresh = True
                    )
                if not Raid._refresh_raid_list(previous_snapshot = Raid._read_visible_raid_cards()):
                    return RaidJoinResult("navigation_error", detail = "forced quick refresh could not be activated safely")
            else:
                MessageLog.print_message("[RAID] Already at Backup Requests screen (quest/assist detected via DOM). Skipping navigation.")
            return Raid._join_raid(excluded_raid_keys = excluded_raid_keys)

        # Coba klik tombol "Backup Requests" via DOM — tombol ini muncul di Quest Results
        # screen setelah raid battle selesai (selector: div.btn-control[data-buton-name="Backup Requests"]).
        clicked_backup = Game.evaluate_dom_js("""(() => {
            const btn = [...document.querySelectorAll('.btn-control[data-buton-name="Backup Requests"]')]
                .find(el => el.offsetParent !== null && window.getComputedStyle(el).display !== 'none');
            if (btn) {
                let activated = false;
                if (window.$ && typeof window.$(btn).trigger === 'function') {
                    try {
                        window.$(btn).trigger('tap');
                        activated = true;
                    } catch (_) {}
                }
                if (!activated) btn.click();
                return true;
            }
            return false;
        })()""")

        if clicked_backup:
            MessageLog.print_message("[RAID] Clicked Backup Requests button via DOM. Waiting for Backup Requests screen...")
            Game.wait(3.0)

            # Confirm we arrived at quest/assist after clicking
            at_assist_after = Game.evaluate_dom_js("""(() => {
                let hash = window.location.hash || '';
                return hash.startsWith('#quest/assist') && !hash.startsWith('#quest/assist/unclaimed');
            })()""")
            if not at_assist_after:
                MessageLog.print_message("[RAID] Backup Requests screen not confirmed after click. Falling back to full navigation...")
                return Raid._navigate(
                    excluded_raid_keys = excluded_raid_keys,
                    force_refresh = force_refresh
                )
            if not Raid._ensure_finder_tab():
                MessageLog.print_message("[RAID] Finder tab was not confirmed after opening Backup Requests. Falling back to full navigation...")
                return Raid._navigate(
                    excluded_raid_keys = excluded_raid_keys,
                    force_refresh = force_refresh
                )
        else:
            # Fallback: tombol Backup Requests tidak ada di DOM (mungkin screen sudah berpindah).
            # Lakukan full navigation via Home screen.
            MessageLog.print_message("[RAID] Backup Requests button not found in DOM. Falling back to full navigation via Home screen...")
            return Raid._navigate(
                excluded_raid_keys = excluded_raid_keys,
                force_refresh = force_refresh
            )

        if force_refresh:
            MessageLog.print_message("[RAID] Backup Requests opened after an ended raid; refreshing before selection...")
            if not Raid._finder_tab_verified_via_dom:
                return Raid._navigate(
                    excluded_raid_keys = excluded_raid_keys,
                    force_refresh = True
                )
            if not Raid._refresh_raid_list(previous_snapshot = Raid._read_visible_raid_cards()):
                return RaidJoinResult("navigation_error", detail = "forced post-navigation refresh could not be activated safely")

        return Raid._join_raid(excluded_raid_keys = excluded_raid_keys)

    @staticmethod
    def start(first_run: bool):
        """Complete one raid run with bounded recovery for stale Backup Requests."""
        from bot.game import Game

        max_attempts = Raid._MAX_JOIN_ATTEMPTS_PER_CYCLE
        max_recovery_cycles = Raid._MAX_STALE_RECOVERY_CYCLES
        attempt_in_cycle = 0
        total_attempts = 0
        recovery_cycle = 0
        consecutive_ended = 0
        rejected_raid_keys = set()
        transient_rejected_keys = set()
        force_refresh = False
        force_full_navigation = first_run

        def remember_ended(reason: str) -> None:
            nonlocal consecutive_ended, force_refresh
            Raid._remember_failed_raid(rejected_raid_keys, transient_rejected_keys)
            consecutive_ended += 1
            force_refresh = True
            MessageLog.print_message(
                f"\n[RAID] {reason} Retrying with a different card "
                f"({attempt_in_cycle}/{max_attempts} in recovery cycle {recovery_cycle})."
            )

        pending_dismiss_js = """(() => {
            const popups = document.querySelectorAll(
                '.pop-usual, .pop-show, .prt-popup-body, .txt-popup-body, [class*="pop-"]'
            );
            for (const popup of popups) {
                if (popup.offsetParent === null || window.getComputedStyle(popup).display === 'none') continue;
                const text = popup.innerText || popup.textContent || '';
                if (!text.toLowerCase().includes('pending')) continue;
                const okButton = popup.querySelector('.btn-usual-ok, .btn-ok, [class*="ok"]');
                if (!okButton || okButton.offsetParent === null) return 'found_no_btn';
                let activated = false;
                if (window.$ && typeof window.$(okButton).trigger === 'function') {
                    try {
                        window.$(okButton).trigger('tap');
                        activated = true;
                    } catch (_) {}
                }
                if (!activated) okButton.click();
                return 'dismissed';
            }
            return null;
        })()"""

        while True:
            if attempt_in_cycle >= max_attempts:
                if recovery_cycle >= max_recovery_cycles:
                    raise RaidException(
                        f"Failed to join and complete a Raid after {total_attempts} attempts across "
                        f"{recovery_cycle + 1} card generations; {consecutive_ended} raids ended before completion."
                    )

                recovery_cycle += 1
                backoff = Raid._STALE_RECOVERY_BASE_WAIT_SECONDS * recovery_cycle
                MessageLog.print_message(
                    f"\n[RAID] Exhausted {max_attempts} join attempts in the current generation. "
                    f"Recovery {recovery_cycle}/{max_recovery_cycles}: returning Home and waiting "
                    f"{backoff:.0f}s for fresh Backup Requests..."
                )
                Game.go_back_home(confirm_location_check = True)
                Game.wait(backoff)

                # Strong request IDs remain rejected for this run. Weak/generation identities may
                # safely represent new cards after a full Home/backoff cycle, so release only those.
                rejected_raid_keys.difference_update(transient_rejected_keys)
                transient_rejected_keys.clear()
                attempt_in_cycle = 0
                force_full_navigation = True
                force_refresh = True
                continue

            attempt_in_cycle += 1
            total_attempts += 1

            if force_full_navigation:
                join_result = Raid._navigate(
                    excluded_raid_keys = rejected_raid_keys,
                    force_refresh = force_refresh
                )
                force_full_navigation = False
            else:
                join_result = Raid._navigate_quick(
                    force_refresh = force_refresh,
                    excluded_raid_keys = rejected_raid_keys
                )
            force_refresh = False

            if join_result.card_key:
                Raid._last_selected_raid_key = join_result.card_key
                Raid._last_selected_raid_key_quality = join_result.card_key_quality

            if join_result.status == "ended":
                remember_ended("The selected raid had already ended.")
                continue

            if join_result.status == "wrong_filter":
                raise RaidException(
                    f"Finder filter safety check failed: {join_result.detail}. "
                    "Restore the saved Finder filter before restarting the bot."
                )

            if not join_result.joined:
                MessageLog.print_message(
                    f"\n[RAID] Recoverable navigation result '{join_result.status}': "
                    f"{join_result.detail or 'no additional detail'}. Rebuilding the Finder route..."
                )
                force_full_navigation = True
                force_refresh = True
                continue

            # The ended popup can arrive after _join_raid's immediate validation window.
            if Game.check_for_ended_raid():
                remember_ended("The selected raid ended before Summon Selection appeared.")
                continue

            if Game.find_and_click_button("cancel", tries = 2, suppress_error = True):
                MessageLog.print_message("\n[RAID] Dismissed a lingering 'EP is full' popup before Summon Selection check.")

            at_summon = False
            raid_ended = False
            pending_recovered = False
            for _ in range(20):
                if Game.check_for_ended_raid():
                    raid_ended = True
                    break

                pending_result = Game.evaluate_dom_js(pending_dismiss_js)
                if pending_result in ("dismissed", "found_no_btn"):
                    MessageLog.print_message("[RAID] Pending battles popup detected before Summon Selection. Clearing pending battles now...")
                    Game.wait(2.0)
                    Game.check_for_pending()
                    pending_recovered = True
                    break

                if ImageUtils.confirm_location("select_a_summon", tries = 2, suppress_error = True):
                    at_summon = True
                    break

                on_supporter = Game.evaluate_dom_js(
                    "Boolean(window.location.hash && window.location.hash.includes('supporter'))"
                )
                if on_supporter:
                    if Game.check_for_ended_raid():
                        raid_ended = True
                        break
                    at_summon = True
                    break
                Game.wait(1.0)

            if pending_recovered:
                MessageLog.print_message("[RAID] Pending battles were recovered; rebuilding Finder without classifying the card as ended.")
                force_full_navigation = False
                force_refresh = True
                continue

            if raid_ended or Game.check_for_ended_raid():
                remember_ended("The selected raid ended while waiting for Summon Selection.")
                continue

            if not at_summon:
                MessageLog.print_message(
                    f"\n[RAID] Timed out waiting for Summon Selection after 20 checks "
                    f"({attempt_in_cycle}/{max_attempts}). Recovering via Home..."
                )
                Game.go_back_home(confirm_location_check = True)
                force_full_navigation = True
                force_refresh = True
                continue

            MessageLog.print_message("[RAID] Raid join confirmed at Summon Selection.")
            if not Game.select_summon(Settings.summon_list, Settings.summon_element_list):
                MessageLog.print_message("[RAID] Summon selection failed. Recovering navigation for another attempt...")
                force_full_navigation = True
                continue

            if not Game.find_party_and_start_mission(Settings.group_number, Settings.party_number):
                if getattr(Game, "_last_party_start_status", None) == "not_started":
                    MessageLog.print_message(
                        "[RAID] Party start was not confirmed. Rebuilding navigation without "
                        "misclassifying the selected raid as ended."
                    )
                    force_full_navigation = True
                    force_refresh = True
                else:
                    remember_ended("The raid ended before the party could enter battle.")
                continue

            if ImageUtils.confirm_location("no_loot", disable_adjustment = True):
                remember_ended("The raid ended while the party was entering and produced no loot.")
                continue

            if not CombatMode.start_combat_mode():
                MessageLog.print_message("\n[RAID] Combat Mode returned False (wipe, retreat, or time exceeded). Ending this raid run.")
                return None

            if ImageUtils.confirm_location(
                    "no_loot", tries = 5, suppress_error = True, disable_adjustment = True):
                remember_ended("The battle was concluded by others and produced no loot.")
                continue

            loot_collected = Game.collect_loot_safe(is_completed = True)
            if not loot_collected:
                MessageLog.print_message(
                    "\n[RAID] Run ended with loot recovery triggered or no loot available. "
                    "Moving to the next raid cycle..."
                )
            return None
