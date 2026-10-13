import cv2

old_summon = cv2.imread('images/buttons/summon.jpg')
cv2.imwrite('temp/old_summon.png', old_summon)
print("Saved temp/old_summon.png, shape:", old_summon.shape)
