import cv2, os

img = cv2.imread('temp/current_battle_now.png')
print(f"Testing templates against current battle screen ({img.shape}):\n")

templates_to_test = [
    ('images/buttons/attack.jpg', 'Attack'),
    ('images/buttons/heal.jpg', 'Heal'),
    ('images/buttons/home_back.jpg', 'Bottom Bar Back'),
    ('images/buttons/reload.jpg', 'Bottom Bar Reload'),
    ('images/buttons/home.jpg', 'Bottom Bar Home'),
    ('images/buttons/summon.jpg', 'Summon Deck'),
    ('images/buttons/event_raid_very_hard.jpg', 'Raid Very Hard (Event Popup)'),
    ('images/buttons/event_raid_extreme.jpg', 'Raid Extreme (Event Popup)'),
    ('images/buttons/event_raid_impossible.jpg', 'Raid Impossible (Event Popup)'),
    ('images/buttons/ap.jpg', 'AP badge (Event Popup)'),
]

for p, desc in templates_to_test:
    if os.path.exists(p):
        tmpl = cv2.imread(p)
        res = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_v, _, max_l = cv2.minMaxLoc(res)
        status = "MATCHED (ACTIVE)" if max_v >= 0.8 else "AVAILABLE (OFF-SCREEN / OTHER SCREEN)"
        print(f"{os.path.basename(p):30} | {desc:32} | max={max_v:.4f} at {max_l} -> {status}")
    else:
        print(f"{os.path.basename(p):30} | {desc:32} | NOT FOUND")
