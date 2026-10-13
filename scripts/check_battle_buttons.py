import cv2, os, datetime

img = cv2.imread('temp/battle_ready.png')

check_buttons = [
    'attack.jpg',
    'heal.jpg',
    'reload.jpg',
    'home.jpg',
    'back.jpg',
    'home_back.jpg',
    'combat_cancel.jpg',
    'cancel.jpg',
    'full_auto.jpg',
    'semi_auto.jpg',
    'quick_summon1.jpg',
    'summon.jpg'
]

print(f"Screen shape: {img.shape}")
for name in check_buttons:
    p = os.path.join('images/buttons', name)
    if os.path.exists(p):
        tmpl = cv2.imread(p)
        if tmpl is not None:
            res = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
            min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M')
            print(f"{name:25} shape={str(tmpl.shape):15} max_val={max_v:.4f} at {max_l} ({mtime})")
        else:
            print(f"{name:25} failed to load")
    else:
        print(f"{name:25} NOT FOUND")
