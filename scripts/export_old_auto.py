import cv2

fa = cv2.imread('images/buttons/full_auto.jpg')
sa = cv2.imread('images/buttons/semi_auto.jpg')
fae = cv2.imread('images/buttons/full_auto_enabled.jpg')
sae = cv2.imread('images/buttons/semi_auto_enabled.jpg')

cv2.imwrite('temp/old_full_auto.png', fa)
cv2.imwrite('temp/old_semi_auto.png', sa)
cv2.imwrite('temp/old_full_auto_enabled.png', fae)
cv2.imwrite('temp/old_semi_auto_enabled.png', sae)

print("Saved old auto templates.")
