import cv2, numpy as np

img = cv2.imread('temp/back_to_party.png')
# prt-list-top btn-command-summon summon-on: x: 414, y: 458, w: 74, h: 150
scale = img.shape[0] / 730.0
x = int(414 * scale)
y = int(458 * scale)
w = int(74 * scale)
h = int(150 * scale)

print(f"Crop rect: ({x}, {y}, {w}, {h})")
crop = img[y+2 : y+h-2, x+2 : x+w-2]
cv2.imwrite('temp/new_summon.png', crop)
print("New summon crop shape:", crop.shape)

res = cv2.matchTemplate(img, crop, cv2.TM_CCOEFF_NORMED)
min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
print(f"Match new_summon: max_val={max_v:.4f} at {max_l}")
