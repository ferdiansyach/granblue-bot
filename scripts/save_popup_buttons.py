import cv2, shutil, os

# Backup and save:
# 1. summon_details_header.jpg
dest_hdr = 'images/headers/summon_details_header.jpg'
backup_hdr = 'images/headers_backup/summon_details_header.jpg'
os.makedirs('images/headers_backup', exist_ok=True)
if os.path.exists(dest_hdr) and not os.path.exists(backup_hdr):
    shutil.copy2(dest_hdr, backup_hdr)
    print(f"Backed up {dest_hdr}")
new_hdr = cv2.imread('temp/new_summon_details_header.png')
cv2.imwrite(dest_hdr, new_hdr, [cv2.IMWRITE_JPEG_QUALITY, 95])
print(f"Saved {dest_hdr} shape={new_hdr.shape}")

# 2. ok.jpg
dest_ok = 'images/buttons/ok.jpg'
backup_ok = 'images/buttons_backup/ok.jpg'
os.makedirs('images/buttons_backup', exist_ok=True)
if os.path.exists(dest_ok) and not os.path.exists(backup_ok):
    shutil.copy2(dest_ok, backup_ok)
    print(f"Backed up {dest_ok}")
new_ok = cv2.imread('temp/new_ok.png')
cv2.imwrite(dest_ok, new_ok, [cv2.IMWRITE_JPEG_QUALITY, 95])
print(f"Saved {dest_ok} shape={new_ok.shape}")

# 3. cancel.jpg
dest_cancel = 'images/buttons/cancel.jpg'
backup_cancel = 'images/buttons_backup/cancel.jpg'
if os.path.exists(dest_cancel) and not os.path.exists(backup_cancel):
    shutil.copy2(dest_cancel, backup_cancel)
    print(f"Backed up {dest_cancel}")
new_cancel = cv2.imread('temp/new_cancel.png')
cv2.imwrite(dest_cancel, new_cancel, [cv2.IMWRITE_JPEG_QUALITY, 95])
print(f"Saved {dest_cancel} shape={new_cancel.shape}")
