"""
Crops and updates battle screen templates from battle_loaded.png
Also clicks ATTACK via CDP to capture Full Auto button template
"""
import asyncio, base64, aiohttp, cv2, numpy as np, os, shutil

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'
IMAGES_DIR = 'images/buttons'
BACKUP_DIR = 'images/buttons_backup'

def backup_and_save(src_arr, dest_path):
    """Backup existing template and save new one"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(dest_path):
        bname = os.path.basename(dest_path)
        shutil.copy2(dest_path, os.path.join(BACKUP_DIR, bname))
        print(f"  Backed up {bname}")
    cv2.imwrite(dest_path, src_arr)
    print(f"  Saved {dest_path} size={src_arr.shape}")

async def ws_eval(ws, i, js):
    await ws.send_json({'id': i, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
    msg = await ws.receive_json()
    return msg.get('result', {}).get('result', {}).get('value')

async def ws_screenshot(ws, i):
    await ws.send_json({'id': i, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
    msg = await ws.receive_json()
    data = base64.b64decode(msg['result']['data'])
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

async def get_rect(ws, i, selector):
    js = f"""
    (() => {{
        let el = document.querySelector('{selector}');
        if (!el) return null;
        let r = el.getBoundingClientRect();
        return JSON.stringify({{x:r.x, y:r.y, w:r.width, h:r.height}});
    }})()
    """
    val = await ws_eval(ws, i, js)
    import json
    return json.loads(val) if val else None

def crop_scaled(img, x, y, w, h, scale):
    """Crop region from screenshot using viewport coords and scale"""
    x1 = int(x * scale)
    y1 = int(y * scale)
    x2 = int((x + w) * scale)
    y2 = int((y + h) * scale)
    return img[y1:y2, x1:x2]

async def main():
    # Load existing battle screenshot
    img = cv2.imread('temp/battle_loaded.png')
    h, w = img.shape[:2]
    scale = h / 730
    print(f"Battle screen: {w}x{h}, scale={scale:.4f}")

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            n = 1

            # === 1. Get ATTACK button rect ===
            attack_rect = await get_rect(ws, n, '.btn-attack-normal'); n += 1
            print(f"ATTACK button rect: {attack_rect}")
            
            if attack_rect:
                # Crop attack button - slightly smaller than full button to avoid edges
                pad = 5
                attack_crop = crop_scaled(img, attack_rect['x']+pad, attack_rect['y']+pad,
                                          attack_rect['w']-pad*2, attack_rect['h']-pad*2, scale)
                cv2.imwrite('temp/attack_crop.png', attack_crop)
                print(f"  Saved temp/attack_crop.png size={attack_crop.shape}")
                
                # Test against existing attack.jpg
                existing_attack = cv2.imread(os.path.join(IMAGES_DIR, 'attack.jpg'))
                res = cv2.matchTemplate(attack_crop, existing_attack, cv2.TM_CCOEFF_NORMED)
                _, max_v, _, _ = cv2.minMaxLoc(res)
                print(f"  Existing attack.jpg match on new crop: {max_v:.4f}")
                
                # Test existing attack.jpg on the full game area
                game = img[:, int(64*scale):int(544*scale)]
                res2 = cv2.matchTemplate(game, existing_attack, cv2.TM_CCOEFF_NORMED)
                _, max_v2, _, max_loc = cv2.minMaxLoc(res2)
                print(f"  Existing attack.jpg match on game area: {max_v2:.4f} at {max_loc}")

            # === 2. Get Full Auto button (appears after clicking ATTACK) ===
            # Click ATTACK
            print("\nClicking ATTACK button...")
            click_attack = """
            (() => {
                if (!window.$) return 'no jquery';
                let btn = $('.btn-attack-normal');
                if (btn.length) { btn.trigger('tap'); return 'clicked ATTACK'; }
                return 'ATTACK not found';
            })()
            """
            res = await ws_eval(ws, n, click_attack); n += 1
            print(f"  {res}")
            await asyncio.sleep(3)

            # Screenshot to see if full_auto appeared
            img2 = await ws_screenshot(ws, n); n += 1
            cv2.imwrite('temp/after_attack_click.png', img2)
            print("  Saved temp/after_attack_click.png")

            # Get Full Auto button rect
            fa_rect = await get_rect(ws, n, '.btn-full-auto, [class*="full-auto"]'); n += 1
            print(f"Full Auto rect: {fa_rect}")

            # Also query for any auto-related buttons
            js_auto = """
            (() => {
                let btns = document.querySelectorAll('button, [class*="auto"]');
                return JSON.stringify([...btns].slice(0,10).map(b => ({
                    cls: b.className,
                    rect: (() => { let r = b.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; })()
                })));
            })()
            """
            import json
            auto_btns = json.loads(await ws_eval(ws, n, js_auto) or '[]'); n += 1
            print("Auto-related elements:")
            for b in auto_btns:
                if b['rect']['w'] > 0:
                    print(f"  cls={b['cls'][:40]} rect={b['rect']}")

            if fa_rect:
                fa_crop = crop_scaled(img2, fa_rect['x'], fa_rect['y'], fa_rect['w'], fa_rect['h'], scale)
                cv2.imwrite('temp/full_auto_crop.png', fa_crop)
                print(f"  Saved temp/full_auto_crop.png size={fa_crop.shape}")

asyncio.run(main())
