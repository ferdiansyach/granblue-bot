"""
Captures templates from the live browser:
1. supporter page (start.jpg, choose_a_summon.jpg)
2. battle screen (full_auto.jpg, full_auto_enabled.jpg, attack.jpg)
"""
import asyncio
import json
import base64
import aiohttp
import cv2
import numpy as np
import os

WS_URI = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'
IMAGES_DIR = 'images/buttons'

async def ws_eval(ws, msg_id, js):
    await ws.send_json({'id': msg_id, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
    msg = await ws.receive_json()
    return msg.get('result', {}).get('result', {}).get('value')

async def ws_screenshot(ws, msg_id):
    await ws.send_json({'id': msg_id, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
    msg = await ws.receive_json()
    data = base64.b64decode(msg['result']['data'])
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

def crop_game(img):
    """Crop to game canvas area (x=64..544 at viewport scale)"""
    h = img.shape[0]
    scale = h / 730
    x1 = int(64 * scale)
    x2 = int(544 * scale)
    return img[:, x1:x2], scale

def find_el_rect(ws, msg_id_start):
    """Returns coroutine to get element rects by CSS selector"""
    pass

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS_URI) as ws:
            msg_id = 1

            # === STEP 1: Screenshot the supporter selection page ===
            print("📸 Capturing supporter selection page...")
            img = await ws_screenshot(ws, msg_id); msg_id += 1
            game, scale = crop_game(img)
            cv2.imwrite('temp/supporter_page.png', img)
            
            # Get URL and page state
            url = await ws_eval(ws, msg_id, 'window.location.href'); msg_id += 1
            print(f"   URL: {url}")

            # Get rects of key elements
            js_rects = """
            (() => {
                let els = {
                    summon_area: document.querySelector('.prt-supporter-support'),
                    auto_select: document.querySelector('.btn-supporter-autoselect'),
                    start_btn: document.querySelector('.btn-usual-ok, .btn-primary, [class*="btn-start"]'),
                };
                let res = {};
                for (let [k, el] of Object.entries(els)) {
                    if (el) {
                        let r = el.getBoundingClientRect();
                        res[k] = {x:r.x, y:r.y, w:r.width, h:r.height, text: el.innerText.trim().slice(0,30)};
                    } else {
                        res[k] = null;
                    }
                }
                return JSON.stringify(res);
            })()
            """
            rects = json.loads(await ws_eval(ws, msg_id, js_rects) or '{}'); msg_id += 1
            print(f"   Elements: {json.dumps(rects, indent=2)}")

            # === STEP 2: Click Auto Select to pick a summon then click Start ===
            print("\n🖱️ Clicking Auto Select...")
            click_auto = """
            (() => {
                if (!window.$) return 'no jquery';
                let btn = $('.btn-supporter-autoselect, .btn-usual-autoselect');
                if (btn.length) { btn.trigger('tap'); return 'clicked auto select'; }
                return 'auto select not found';
            })()
            """
            res = await ws_eval(ws, msg_id, click_auto); msg_id += 1
            print(f"   {res}")
            await asyncio.sleep(2)
            
            # Take screenshot after auto select
            img2 = await ws_screenshot(ws, msg_id); msg_id += 1
            cv2.imwrite('temp/after_autoselect.png', img2)

            # === STEP 3: Get existing templates to test against supporter page ===
            print("\n🔍 Testing existing templates against supporter page...")
            game_crop, scale = crop_game(img2)
            
            for tmpl_name in ['choose_a_summon', 'start', 'summon']:
                tmpl_path = os.path.join(IMAGES_DIR, f'{tmpl_name}.jpg')
                if not os.path.exists(tmpl_path):
                    print(f"   ❌ {tmpl_name}.jpg not found")
                    continue
                tmpl = cv2.imread(tmpl_path)
                res = cv2.matchTemplate(game_crop, tmpl, cv2.TM_CCOEFF_NORMED)
                _, max_v, _, max_l = cv2.minMaxLoc(res)
                print(f"   {tmpl_name}.jpg: best score={max_v:.4f} at {max_l}")

            # === STEP 4: Click Start / OK button to go to battle ===
            print("\n🖱️ Clicking Start button...")
            click_start = """
            (() => {
                if (!window.$) return 'no jquery';
                // Try different button selectors
                let candidates = [
                    $('.btn-usual-ok'),
                    $('[class*="btn-start"]'),
                    $('.btn-primary'),
                    $('[data-action="decide"]'),
                ];
                for (let btn of candidates) {
                    if (btn.length) {
                        btn.first().trigger('tap');
                        return 'clicked: ' + btn.first().attr('class');
                    }
                }
                // List all buttons for debugging
                let btns = $('button, [class*="btn"]');
                return 'not found. buttons: ' + [...btns].slice(0,5).map(b=>b.className).join('|');
            })()
            """
            res = await ws_eval(ws, msg_id, click_start); msg_id += 1
            print(f"   {res}")
            await asyncio.sleep(3)
            
            url2 = await ws_eval(ws, msg_id, 'window.location.href'); msg_id += 1
            print(f"   URL after start: {url2}")

            # Screenshot
            img3 = await ws_screenshot(ws, msg_id); msg_id += 1
            cv2.imwrite('temp/battle_screen.png', img3)
            print("   Saved temp/battle_screen.png")

            return img3, url2

if __name__ == '__main__':
    img, url = asyncio.run(main())
    print(f"\n✅ Done! Final URL: {url}")
    print(f"   Battle screen size: {img.shape}")
