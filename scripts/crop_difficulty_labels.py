"""
Crop exact difficulty label templates from popup_fresh.png.
Also crop full_auto from battle screenshots.
"""
import asyncio, base64, aiohttp, cv2, numpy as np, json, os, shutil

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'
IMAGES_DIR = 'images/buttons'
BACKUP_DIR = 'images/buttons_backup'
os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_save(arr, name):
    dest = os.path.join(IMAGES_DIR, name)
    if os.path.exists(dest):
        shutil.copy2(dest, os.path.join(BACKUP_DIR, name))
        print(f"  Backed up {name}")
    cv2.imwrite(dest, arr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"  SAVED {name} size={arr.shape}")

def crop_vp(img, x, y, w, h, scale, pad=2):
    x1 = max(0, int((x+pad)*scale))
    y1 = max(0, int((y+pad)*scale))
    x2 = int((x+w-pad)*scale)
    y2 = int((y+h-pad)*scale)
    return img[y1:y2, x1:x2]

# Load popup screenshot
popup = cv2.imread('temp/popup_fresh.png')
h_p, w_p = popup.shape[:2]
scale = h_p / 730
print(f"Popup: {w_p}x{h_p}, scale={scale:.4f}")

# From popup screenshot visual inspection:
# Cards are at approximately:
#   VH card: x=105..235, y=363..532
#   EX card: x=238..368, y=363..532
#   IM card: x=372..502, y=363..532
#
# The difficulty LABEL text ("VERY HARD", "EXTREME", "IMPOSSIBLE") is at y~442..475
# It's the colored text inside each card
# From DOM: AP-0 label at y=471, height=28 -> difficulty text must be just above AP at y~430..465

# Let's get exact positions of all text in popup
async def get_all_text():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let result = [];
                let node;
                while (node = walker.nextNode()) {
                    let txt = node.textContent.trim();
                    if (txt.length > 2 && txt.length < 30) {
                        let el = node.parentElement;
                        let r = el.getBoundingClientRect();
                        if (r.width > 20 && r.height > 8 && r.x > 60 && r.x < 550) {
                            result.push({
                                text: txt,
                                cls: (el.className||'').slice(0,40),
                                x: r.x, y: r.y, w: r.width, h: r.height
                            });
                        }
                    }
                }
                return JSON.stringify(result);
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            msg = await ws.receive_json()
            return json.loads(msg.get('result', {}).get('result', {}).get('value') or '[]')

all_text = asyncio.run(get_all_text())
print(f"\nAll popup text elements ({len(all_text)}):")
for t in sorted(all_text, key=lambda x: (x['y'], x['x'])):
    print(f"  '{t['text']:25}' [{t['cls']:35}] ({t['x']:.0f},{t['y']:.0f}) {t['w']:.0f}x{t['h']:.0f}")

print("\n=== Cropping difficulty labels ===")
# Find VH, EX, IM text elements
vh_el = next((t for t in all_text if 'VERY HARD' in t['text'].upper()), None)
ex_el = next((t for t in all_text if 'EXTREME' in t['text'].upper() and 'AP' not in t['text'].upper()), None)
im_el = next((t for t in all_text if 'IMPOSSIBLE' in t['text'].upper()), None)

for name, el in [('VH', vh_el), ('EX', ex_el), ('IM', im_el)]:
    if el:
        print(f"  {name}: '{el['text']}' at ({el['x']:.0f},{el['y']:.0f}) {el['w']:.0f}x{el['h']:.0f}")
    else:
        print(f"  {name}: NOT FOUND")

# Fallback: use visual coordinates from the popup screenshot
# In popup_fresh.png, looking at y~370-460 area for difficulty text
# VH "VERY HARD" red text: approximately y=363, x=105..235
# Let's crop the lower third of each card (difficulty text + badge area)

print("\n=== Cropping from visual inspection ===")
# The difficulty text in each card (y=365..530 per card)
# Looking at the image, "VERY HARD" label is in the lower portion
# Let's crop the full card content area (no badge)

card_data = [
    # (name,              x,    y,    w,    h)   -- inner card content
    ('event_raid_very_hard.jpg',  110, 375, 122, 95),   # full card body
    ('event_raid_extreme.jpg',    244, 375, 122, 95),   # full card body  
    ('event_raid_impossible.jpg', 378, 375, 122, 95),   # full card body
]

for fname, x, y, w, h in card_data:
    crop = crop_vp(popup, x, y, w, h, scale, pad=2)
    preview_path = f'temp/{fname}'
    cv2.imwrite(preview_path, crop)
    print(f"  {fname}: {crop.shape}")

# Show cropped templates
print("\nDone! Check temp/ for previews before deciding to save")
