"""
Crop and update all failing templates:
1. event_raid_impossible.jpg, event_raid_extreme.jpg, event_raid_very_hard.jpg from popup screenshot
2. full_auto.jpg, full_auto_enabled.jpg, semi_auto.jpg from battle (need to trigger turn first)
"""
import asyncio, base64, aiohttp, cv2, numpy as np, json, os, shutil

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'
IMAGES_DIR = 'images/buttons'
BACKUP_DIR = 'images/buttons_backup'
os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_save(arr, name):
    dest = os.path.join(IMAGES_DIR, name)
    if os.path.exists(dest):
        shutil.copy2(dest, os.path.join(BACKUP_DIR, name))
    cv2.imwrite(dest, arr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"  SAVED: {name} {arr.shape}")

def crop_vp(img, x, y, w, h, scale, pad=0):
    """Crop using viewport coords"""
    x1 = max(0, int((x+pad)*scale))
    y1 = max(0, int((y+pad)*scale))
    x2 = int((x+w-pad)*scale)
    y2 = int((y+h-pad)*scale)
    return img[y1:y2, x1:x2]

# === PART 1: Crop Raid Difficulty Labels from Popup ===
print("=== PART 1: Raid difficulty labels from popup ===")
popup = cv2.imread('temp/popup_for_crop.png')
h, w = popup.shape[:2]
scale = h / 730
print(f"Popup: {w}x{h}, scale={scale:.4f}")

# From DOM: Cards at x=105,238,372, y=363, w=130, h=169
# We need the header text of each card: "VERY HARD", "EXTREME", "IMPOSSIBLE"
# These are at the top of each card
# Card headers are approximately y=363..395 (top ~32px of each card)
card_positions = [
    ('event_raid_very_hard.jpg',  105, 363, 130, 38),   # VH header
    ('event_raid_extreme.jpg',    238, 363, 130, 38),   # EX header  
    ('event_raid_impossible.jpg', 372, 363, 130, 38),   # IM header
]

for name, x, y, w_c, h_c in card_positions:
    crop = crop_vp(popup, x, y, w_c, h_c, scale, pad=2)
    cv2.imwrite(f'temp/{name}', crop)
    
    # Also try matching existing template on popup
    existing = cv2.imread(os.path.join(IMAGES_DIR, name))
    if existing is not None:
        p_game = popup[:, int(64*scale):int(544*scale)]
        res = cv2.matchTemplate(p_game, existing, cv2.TM_CCOEFF_NORMED)
        _, score, _, _ = cv2.minMaxLoc(res)
        print(f"  {name}: existing score={score:.4f}, crop={crop.shape}")
        if score < 0.75:
            backup_save(crop, name)
    else:
        backup_save(crop, name)

# Also try to crop the full card for event_raid_impossible.jpg
# (used by the bot to find the "Impossible" label in the popup)
imp_full_card = crop_vp(popup, 372, 363, 130, 55, scale, pad=2)
cv2.imwrite('temp/event_raid_impossible_full.png', imp_full_card)
print(f"  Full impossible card crop: {imp_full_card.shape}")

print()
print("=== PART 2: Auto buttons from battle ===")
# The full_auto, semi_auto etc appear in the action panel
# which scrolls into view. They are in the bottom action area
# Let's load the battle current screenshot and look for them
battle = cv2.imread('temp/battle_current.png')
bh, bw = battle.shape[:2]
bscale = bh / 730
print(f"Battle: {bw}x{bh}, scale={bscale:.4f}")
b_game = battle[:, int(64*bscale):int(544*bscale)]

# From visual inspection of battle_current.png:
# - Heal button: y=628..676, x=75..245
# - Auto button: y=628..676, x=285..399 (the "Auto" charge attack button)
# - Skip button: y=628..676, x=416..541

# The Full Auto / Semi Auto toggle appears in the upper area during combat
# In the bot's design, full_auto.jpg is the "FULL" text on the Auto toggle button
# Looking at the screenshot: there's no full_auto visible yet in this state
# The full_auto button appears after scrolling or in a different state

# Let's check if the full_auto appears in viewport area y=357-450
# In the screenshot: y=357 area has ATTACK button

# The full_auto should appear below skills - need to scroll down in battle UI
# Actually in GBF, full_auto is a small toggle at the top-left of battle
# Let's check image of full_auto.jpg we have (it says "FULL" in yellow)

print()
print("Looking for FULL text in battle screenshot...")
# Convert to HSV to find yellow/golden text
hsv = cv2.cvtColor(b_game, cv2.COLOR_BGR2HSV)
# Yellow: H=20-35, S=100-255, V=150-255
yellow_mask = cv2.inRange(hsv, np.array([15,100,150]), np.array([35,255,255]))
contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"  Yellow regions found: {len(contours)}")
for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
    x,y,w,h = cv2.boundingRect(c)
    area = cv2.contourArea(c)
    if area > 50:
        print(f"    area={area:.0f} at ({x},{y}) {w}x{h}")

# Let's also check the music/sound button area for any auto-related UI
# In the battle UI, the auto toggle is at the top-left area
# From DOM: btn-switch-sound at (64, 3, 101x60) - that's the music/sound ON indicator
# The ON/OFF toggle for auto is at the same area

print()
print("Checking for 'ON' indicator position (auto/manual mode)...")
# From DOM: btn-switch-sound at (64, 3, 101x60) shows "ON" text
on_crop = crop_vp(battle, 64, 3, 101, 60, bscale, pad=2)
cv2.imwrite('temp/auto_mode_indicator.png', on_crop)
print(f"  ON indicator crop saved: {on_crop.shape}")

# The full_auto button - let's look at the full battle screenshot in y=350-430
# to find where full auto control might be
# Actually let's crop the area around y=355-430 which shows character cards area
action_area = battle[int(350*bscale):int(450*bscale), int(64*bscale):int(544*bscale)]
cv2.imwrite('temp/action_area.png', action_area)
print(f"  Action area crop: {action_area.shape}")

asyncio.run(asyncio.sleep(0))
