import cv2, numpy as np

img = cv2.imread('temp/popup_for_crop.png')
print('Screenshot size (h,w):', img.shape[:2])

# AP text positions from DOM:
# Scale factor: screenshot h=912 vs viewport h=730, so scale=912/730=1.249
scale = img.shape[0] / 730
print(f'Scale factor: {scale:.4f}')

aps = [
    ('VH',  125.5, 470.7, 90, 27.7),
    ('EX',  259.0, 470.7, 90, 27.7),
    ('IM',  392.5, 470.7, 90, 27.7),
]

for name, x, y, w, h in aps:
    x1 = int(x * scale)
    y1 = int(y * scale)
    x2 = int((x + w) * scale)
    y2 = int((y + h) * scale)
    crop = img[y1:y2, x1:x2]
    fname = f'temp/ap_{name}_label.png'
    cv2.imwrite(fname, crop)
    print(f'{name}: saved {fname} size {crop.shape}')

# Crop popup game area
game_x1 = int(64 * scale)
game_x2 = int(544 * scale)
popup = img[:, game_x1:game_x2]
cv2.imwrite('temp/popup_game_area.png', popup)
print(f'Saved popup_game_area.png size {popup.shape}')

# Test match of existing ap.jpg template on scaled area
tmpl = cv2.imread('images/buttons/ap.jpg')
print(f'ap.jpg template size: {tmpl.shape}')
res = cv2.matchTemplate(popup, tmpl, cv2.TM_CCOEFF_NORMED)
locs = np.where(res >= 0.85)
pts = sorted(zip(*locs[::-1]), key=lambda p: -res[p[1], p[0]])
clusters = []
for pt in pts:
    if not any(abs(pt[0]-c[0]) < 20 and abs(pt[1]-c[1]) < 20 for c in clusters):
        clusters.append(pt)
        if len(clusters) >= 5:
            break
print('Matches >= 0.85:')
for c in clusters:
    print(f'  x={c[0]+int(64*scale)}, y={c[1]}, score={res[c[1],c[0]]:.4f}')
