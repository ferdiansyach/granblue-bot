"""
Script untuk menangkap dan menyimpan gambar referensi tombol HOME dari game.
Jalankan script ini SAAT game Granblue Fantasy terbuka di browser.

Langkah:
  1. Buka game di browser, pastikan bottom menu terlihat
  2. Jalankan script ini: python capture_home_button.py
  3. Script akan simpan full screenshot ke temp/full_screenshot.png
  4. Script akan otomatis cari bottom bar dan crop tombol HOME
"""

import os
import sys
import time
import shutil

import pyautogui
import cv2
import numpy as np
from PIL import Image

# ── Konfigurasi ──────────────────────────────────────────────────────────────
CURRENT_DIR     = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR        = os.path.join(CURRENT_DIR, "temp")
IMAGES_BTN_DIR  = os.path.join(CURRENT_DIR, "..", "images", "buttons")
IMAGES_BTN_DIR  = os.path.normpath(IMAGES_BTN_DIR)
OUTPUT_FULL     = os.path.join(TEMP_DIR, "full_screenshot.png")
OUTPUT_HOME     = os.path.join(TEMP_DIR, "new_home.jpg")
BACKUP_HOME     = os.path.join(IMAGES_BTN_DIR, "home_backup.jpg")
DEST_HOME       = os.path.join(IMAGES_BTN_DIR, "home.jpg")

# Warna bottom bar GBF (biru tua/navy) — toleransi warna piksel
BOTTOM_BAR_MIN_H = 40   # tinggi minimum area bar (piksel)
BOTTOM_BAR_MAX_H = 90   # tinggi maksimum area bar (piksel)
# ─────────────────────────────────────────────────────────────────────────────

os.makedirs(TEMP_DIR, exist_ok=True)

def take_fullscreen():
    print("[INFO] Mengambil screenshot layar penuh...")
    time.sleep(1)
    img = pyautogui.screenshot()
    img.save(OUTPUT_FULL)
    print(f"[OK]   Tersimpan di: {OUTPUT_FULL}")
    return np.array(img.convert("RGB"))

def find_bottom_bar(img_rgb: np.ndarray):
    """
    Scan dari bawah layar ke atas untuk menemukan area bottom bar game.
    Bottom bar GBF biasanya berwarna biru gelap (#1a2a4a range).
    """
    height, width, _ = img_rgb.shape

    img_hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)

    # Rentang warna biru gelap (bottom bar GBF)
    lower_blue = np.array([90, 40, 20])
    upper_blue = np.array([140, 255, 120])
    mask = cv2.inRange(img_hsv, lower_blue, upper_blue)

    bar_bottom = None
    bar_top    = None

    for y in range(height - 1, height - 200, -1):
        row_blue_ratio = np.sum(mask[y, :]) / (width * 255)
        if row_blue_ratio > 0.4:
            if bar_bottom is None:
                bar_bottom = y
            bar_top = y
        elif bar_bottom is not None and (bar_bottom - y) > BOTTOM_BAR_MAX_H:
            break

    if bar_top is None or bar_bottom is None:
        return None

    bar_h = bar_bottom - bar_top
    if bar_h < BOTTOM_BAR_MIN_H:
        return None

    return (0, bar_top, width, bar_h + 5)

def crop_home_from_bar(img_rgb: np.ndarray, bar_rect):
    """
    Dari area bar yang ditemukan, crop porsi HOME button.
    """
    x, y, w, h = bar_rect
    bar_crop = img_rgb[y:y+h, x:x+w]

    print(f"[INFO] Bottom bar ditemukan di y={y}, tinggi={h}px, lebar={w}px")
    bar_pil = Image.fromarray(bar_crop)
    bar_pil.save(os.path.join(TEMP_DIR, "bottom_bar.png"))
    print(f"[OK]   Bottom bar disimpan di: {TEMP_DIR}\\bottom_bar.png")

    existing_refs = [
        os.path.join(IMAGES_BTN_DIR, "home.jpg"),
        os.path.join(IMAGES_BTN_DIR, "calibration_right.jpg"),
    ]

    best_val = 0
    best_loc = None
    best_templ_size = (50, 25)

    bar_gray = cv2.cvtColor(bar_crop, cv2.COLOR_RGB2GRAY)

    for ref_path in existing_refs:
        if not os.path.exists(ref_path):
            continue
        templ = cv2.imread(ref_path, 0)
        if templ is None:
            continue
        for scale in [0.8, 0.9, 1.0, 1.1, 1.2]:
            th, tw = templ.shape[:2]
            new_w, new_h = int(tw * scale), int(th * scale)
            if new_w > bar_gray.shape[1] or new_h > bar_gray.shape[0]:
                continue
            resized = cv2.resize(templ, (new_w, new_h))
            result = cv2.matchTemplate(bar_gray, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best_val:
                best_val  = max_val
                best_loc  = max_loc
                best_templ_size = (new_w, new_h)
        print(f"[INFO] Match terhadap {os.path.basename(ref_path)}: {best_val:.4f}")

    if best_loc and best_val > 0.3:
        bx, by = best_loc
        bw, bh = best_templ_size
        pad_x, pad_y = 4, 3
        crop_x1 = max(0, bx - pad_x)
        crop_y1 = max(0, by - pad_y)
        crop_x2 = min(bar_crop.shape[1], bx + bw + pad_x)
        crop_y2 = min(bar_crop.shape[0], by + bh + pad_y)
        home_crop = bar_crop[crop_y1:crop_y2, crop_x1:crop_x2]
        print(f"[INFO] HOME ditemukan di bar offset ({bx},{by}), score={best_val:.4f}")
        return home_crop
    else:
        center_x = w // 2
        home_w   = w // 5
        home_crop = bar_crop[:, center_x - home_w//2 : center_x + home_w//2]
        print("[WARNING] Tidak bisa match otomatis. Fallback: crop tengah bar.")
        return home_crop

def save_new_home(home_crop_rgb: np.ndarray):
    if os.path.exists(DEST_HOME):
        shutil.copy2(DEST_HOME, BACKUP_HOME)
        print(f"[INFO] Backup home.jpg lama -> home_backup.jpg")

    home_pil = Image.fromarray(home_crop_rgb).convert("RGB")
    home_pil.save(OUTPUT_HOME)
    home_pil.save(DEST_HOME, quality=95)
    print(f"[OK]   home.jpg baru disimpan di: {DEST_HOME}")
    print(f"[OK]   Preview crop  disimpan di: {OUTPUT_HOME}")

def main():
    print("=" * 60)
    print("  Granblue Automation - Capture HOME Button Tool")
    print("=" * 60)
    print()
    print("Pastikan:")
    print("  * Game Granblue Fantasy terbuka di browser")
    print("  * Bottom menu (Home/Quest/Menu) terlihat jelas")
    print("  * Window game di notch ke-2")
    print()
    print("Pindahkan kursor ke window game sekarang...")
    for i in range(5, 0, -1):
        print(f"  Screenshot dalam {i} detik...", end="\r")
        time.sleep(1)
    print()

    img_rgb = take_fullscreen()

    print("[INFO] Mencari bottom bar game...")
    bar_rect = find_bottom_bar(img_rgb)

    if bar_rect is None:
        print()
        print("[ERROR] Bottom bar tidak ditemukan secara otomatis.")
        print(f"        Silakan buka file: {OUTPUT_FULL}")
        print("        Crop manual area tombol HOME, simpan ke:")
        print(f"        {DEST_HOME}")
        sys.exit(1)

    home_crop = crop_home_from_bar(img_rgb, bar_rect)
    save_new_home(home_crop)

    print()
    print("=" * 60)
    print("[SELESAI] Sekarang coba jalankan bot kembali.")
    print()
    print("Jika masih gagal, periksa file berikut secara manual:")
    print(f"  Full screenshot : {OUTPUT_FULL}")
    print(f"  Bottom bar      : {TEMP_DIR}\\bottom_bar.png")
    print(f"  Crop HOME baru  : {OUTPUT_HOME}")
    print()
    print("Crop HOME yang benar dan timpa file:")
    print(f"  {DEST_HOME}")
    print("=" * 60)

if __name__ == "__main__":
    main()
