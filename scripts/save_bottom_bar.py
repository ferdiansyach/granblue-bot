import cv2, shutil, os

img = cv2.imread('temp/rapid_atk_0.2s.png')
scale = img.shape[0] / 730.0

# 1. reload.jpg
dest_rel = 'images/buttons/reload.jpg'
backup_rel = 'images/buttons_backup/reload.jpg'
os.makedirs('images/buttons_backup', exist_ok=True)
if os.path.exists(dest_rel) and not os.path.exists(backup_rel):
    shutil.copy2(dest_rel, backup_rel)
new_reload = cv2.imread('temp/new_reload.png')
cv2.imwrite(dest_rel, new_reload, [cv2.IMWRITE_JPEG_QUALITY, 95])
print(f"Saved {dest_rel} shape={new_reload.shape}")

# 2. home.jpg
dest_home = 'images/buttons/home.jpg'
backup_home = 'images/buttons_backup/home.jpg'
if os.path.exists(dest_home) and not os.path.exists(backup_home):
    shutil.copy2(dest_home, backup_home)
new_home = cv2.imread('temp/new_home.png')
cv2.imwrite(dest_home, new_home, [cv2.IMWRITE_JPEG_QUALITY, 95])
print(f"Saved {dest_home} shape={new_home.shape}")

# 3. home_back.jpg (bottom bar Back button: x: 78, y: 670, w: 63, h: 48)
x_b = int(78 * scale)
y_b = int(670 * scale)
w_b = int(63 * scale)
h_b = int(48 * scale)
crop_hb = img[y_b+2 : y_b+h_b-2, x_b+2 : x_b+w_b-2]
cv2.imwrite('temp/new_home_back.png', crop_hb)

dest_hb = 'images/buttons/home_back.jpg'
backup_hb = 'images/buttons_backup/home_back.jpg'
if os.path.exists(dest_hb) and not os.path.exists(backup_hb):
    shutil.copy2(dest_hb, backup_hb)
cv2.imwrite(dest_hb, crop_hb, [cv2.IMWRITE_JPEG_QUALITY, 95])
print(f"Saved {dest_hb} shape={crop_hb.shape}")

# Test matching
for n, c in [('reload', new_reload), ('home', new_home), ('home_back', crop_hb)]:
    res = cv2.matchTemplate(img, c, cv2.TM_CCOEFF_NORMED)
    _, max_v, _, max_l = cv2.minMaxLoc(res)
    print(f"Match {n:10}: max_val={max_v:.4f} at {max_l}")
