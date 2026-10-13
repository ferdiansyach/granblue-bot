"""
Update templates from live battle screen:
1. attack.jpg - from btn-attack-start
2. full_auto.jpg - from btn-event-raid after clicking attack
3. semi_auto.jpg - if visible
"""
import asyncio, base64, aiohttp, cv2, numpy as np, json, os, shutil

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'
IMAGES_DIR = 'images/buttons'
BACKUP_DIR = 'images/buttons_backup'

os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs('temp', exist_ok=True)

async def ws_eval(ws, i, js):
    await ws.send_json({'id': i, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
    msg = await ws.receive_json()
    return msg.get('result', {}).get('result', {}).get('value')

async def ws_screenshot(ws, i):
    await ws.send_json({'id': i, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
    msg = await ws.receive_json()
    return cv2.imdecode(np.frombuffer(base64.b64decode(msg['result']['data']), np.uint8), cv2.IMREAD_COLOR)

def crop_scaled(img, x, y, w, h, scale, pad=3):
    x1 = max(0, int((x + pad) * scale))
    y1 = max(0, int((y + pad) * scale))
    x2 = int((x + w - pad) * scale)
    y2 = int((y + h - pad) * scale)
    return img[y1:y2, x1:x2]

def backup_save(crop, name):
    dest = os.path.join(IMAGES_DIR, name)
    if os.path.exists(dest):
        shutil.copy2(dest, os.path.join(BACKUP_DIR, name))
        print(f"  Backed up {name}")
    # Convert to jpg
    dest_jpg = dest if dest.endswith('.jpg') else dest
    cv2.imwrite(dest_jpg, crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"  UPDATED: {dest_jpg} size={crop.shape}")

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            n = 1
            
            # === STEP 1: Capture ATTACK button ===
            img = await ws_screenshot(ws, n); n += 1
            h, w_img = img.shape[:2]
            scale = h / 730
            print(f"Scale: {scale:.4f}")

            # btn-attack-start at (349, 365, 195x65) from DOM
            attack_crop = crop_scaled(img, 349, 365, 195, 65, scale, pad=5)
            cv2.imwrite('temp/attack_new.png', attack_crop)
            print(f"Attack button cropped: {attack_crop.shape}")

            # Test existing attack.jpg on game area
            game = img[:, int(64*scale):int(544*scale)]
            existing_atk = cv2.imread(os.path.join(IMAGES_DIR, 'attack.jpg'))
            res = cv2.matchTemplate(game, existing_atk, cv2.TM_CCOEFF_NORMED)
            _, max_v, _, max_loc = cv2.minMaxLoc(res)
            print(f"Existing attack.jpg match: {max_v:.4f} at {max_loc}")

            if max_v < 0.8:
                print("  -> attack.jpg needs update!")
                backup_save(attack_crop, 'attack.jpg')
            else:
                print("  -> attack.jpg OK (score >= 0.8), no update needed")

            # === STEP 2: Click ATTACK to reveal auto buttons ===
            print("\nClicking btn-attack-start...")
            click_js = """
            (() => {
                let btn = document.querySelector('.btn-attack-start');
                if (btn) {
                    btn.click();
                    return 'Clicked btn-attack-start class=' + btn.className;
                }
                return 'not found';
            })()
            """
            res = await ws_eval(ws, n, click_js); n += 1
            print(f"  {res}")
            await asyncio.sleep(3)

            img2 = await ws_screenshot(ws, n); n += 1
            cv2.imwrite('temp/after_attack.png', img2)

            # Find auto buttons
            js_find_auto = """
            (() => {
                let els = document.querySelectorAll('[class*="auto"], [class*="full"]');
                return JSON.stringify([...els].map(el => {
                    let r = el.getBoundingClientRect();
                    return {cls: el.className, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
                }).filter(e => e.w > 20 && e.h > 10));
            })()
            """
            auto_data = json.loads(await ws_eval(ws, n, js_find_auto) or '[]'); n += 1
            print(f"Auto elements after click:")
            for a in auto_data:
                print(f"  cls={a['cls'][:50]} pos=({a['x']},{a['y']}) size={a['w']}x{a['h']}")

            # Also find all battle action buttons
            js_all_btns = """
            (() => {
                let els = document.querySelectorAll('[class*="btn"]');
                let result = [];
                for (let el of els) {
                    let r = el.getBoundingClientRect();
                    if (r.width > 20 && r.height > 10 && r.width < 400 && r.x > 50 && r.x < 560) {
                        result.push({cls: (el.className||'').slice(0,60), x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height)});
                    }
                }
                return JSON.stringify(result.slice(0,20));
            })()
            """
            all_btns = json.loads(await ws_eval(ws, n, js_all_btns) or '[]'); n += 1
            print(f"\nAll buttons after click:")
            for b in all_btns:
                print(f"  [{b['cls']:55}] ({b['x']:4},{b['y']:4}) {b['w']}x{b['h']}")

asyncio.run(main())
