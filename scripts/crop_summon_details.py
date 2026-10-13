import cv2, numpy as np

img = cv2.imread('temp/summon_details.png')
scale = img.shape[0] / 730.0

# 1. Header: prt-popup-header x: 64, y: 143, w: 480, h: 80
# In the header, "Summons Details" is centered
# Center x ~ (64 + 240) = 304 in viewport -> 304 * scale
# Let's crop just the text "Summons Details"
# Looking at the header: y: 143, h: 80 -> text is around y: 160-195
y_hdr = int(160 * scale)
h_hdr = int(35 * scale)
x_hdr = int((304 - 100) * scale)
w_hdr = int(200 * scale)

crop_hdr = img[y_hdr : y_hdr + h_hdr, x_hdr : x_hdr + w_hdr]
cv2.imwrite('temp/new_summon_details_header.png', crop_hdr)

# 2. Cancel button: btn-usual-cancel x: 93, y: 505, w: 212, h: 54
x_c = int(93 * scale)
y_c = int(505 * scale)
w_c = int(212 * scale)
h_c = int(54 * scale)

# Crop the "Cancel" text area in the middle of button
crop_cancel = img[y_c + 6 : y_c + h_c - 6, x_c + 20 : x_c + w_c - 20]
cv2.imwrite('temp/new_cancel.png', crop_cancel)

# 3. OK button: btn-usual-ok x: 304, y: 505, w: 212, h: 54
x_ok = int(304 * scale)
y_ok = int(505 * scale)
w_ok = int(212 * scale)
h_ok = int(54 * scale)

# Crop the "OK" text area in the middle of button
crop_ok = img[y_ok + 6 : y_ok + h_ok - 6, x_ok + 20 : x_ok + w_ok - 20]
cv2.imwrite('temp/new_ok.png', crop_ok)

print("Saved crops. Testing matches:")
for name, c in [('header', crop_hdr), ('cancel', crop_cancel), ('ok', crop_ok)]:
    res = cv2.matchTemplate(img, c, cv2.TM_CCOEFF_NORMED)
    _, max_v, _, max_l = cv2.minMaxLoc(res)
    print(f" {name:10} shape={str(c.shape):15} max_val={max_v:.4f} at {max_l}")
