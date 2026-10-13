import cv2, numpy as np

img = cv2.imread('temp/after_close_menu.png')
# btn-command-back display-on: x: 64, y: 368, w: 102, h: 54 in 730p viewport
scale = img.shape[0] / 730.0
x = int(64 * scale)
y = int(368 * scale)
w = int(102 * scale)
h = int(54 * scale)

print(f"Scale: {scale}, crop rect: ({x}, {y}, {w}, {h})")

# Crop button with small padding inside to avoid borders
crop = img[y+4 : y+h-4, x+4 : x+w-4]
cv2.imwrite('temp/new_back.png', crop)
print(f"New back crop shape: {crop.shape}")

# Test matching against img
res = cv2.matchTemplate(img, crop, cv2.TM_CCOEFF_NORMED)
min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
print(f"Match new_back: max_val={max_v:.4f} at {max_l}")

# Compare with old_back
old_back = cv2.imread('images/buttons/back.jpg')
res_old = cv2.matchTemplate(img, old_back, cv2.TM_CCOEFF_NORMED)
_, max_v_old, _, max_l_old = cv2.minMaxLoc(res_old)
print(f"Match old_back: max_val={max_v_old:.4f} at {max_l_old}")
