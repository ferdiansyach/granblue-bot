import cv2, shutil, os

dest = 'images/buttons/back.jpg'
backup = 'images/buttons_backup/back.jpg'
os.makedirs('images/buttons_backup', exist_ok=True)
if os.path.exists(dest) and not os.path.exists(backup):
    shutil.copy2(dest, backup)
    print(f"Backed up {dest} to {backup}")

new_back = cv2.imread('temp/new_back.png')
cv2.imwrite(dest, new_back, [cv2.IMWRITE_JPEG_QUALITY, 95])
print(f"Successfully saved {dest} with shape {new_back.shape}")
