"""
Navigate to new Impossible raid battle, wait for battle to load,
then capture full_auto and semi_auto button screenshots.
"""
import asyncio, base64, aiohttp, cv2, numpy as np, json, os, shutil, time

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'
IMAGES_DIR = 'images/buttons'
BACKUP_DIR = 'images/buttons_backup'
os.makedirs(BACKUP_DIR, exist_ok=True)

async def ws_eval(ws, i, js):
    await ws.send_json({'id': i, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
    msg = await ws.receive_json()
    return msg.get('result', {}).get('result', {}).get('value')

async def ws_screenshot(ws, i):
    await ws.send_json({'id': i, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
    msg = await ws.receive_json()
    return cv2.imdecode(np.frombuffer(base64.b64decode(msg['result']['data']), np.uint8), cv2.IMREAD_COLOR)

def crop_vp(img, x, y, w, h, scale, pad=2):
    x1 = max(0, int((x+pad)*scale))
    y1 = max(0, int((y+pad)*scale))
    x2 = int((x+w-pad)*scale)
    y2 = int((y+h-pad)*scale)
    return img[y1:y2, x1:x2]

def backup_save(arr, name):
    dest = os.path.join(IMAGES_DIR, name)
    if os.path.exists(dest):
        shutil.copy2(dest, os.path.join(BACKUP_DIR, name))
        print(f"  Backed up {name}")
    cv2.imwrite(dest, arr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"  SAVED {name} {arr.shape}")

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            n = 1

            # Close popup first
            await ws_eval(ws, n, """
                if (window.$) {
                    let close = $('.btn-usual-close, .btn-close');
                    if (close.length) close.trigger('tap');
                }
            """); n += 1
            await asyncio.sleep(1)

            # Open raid popup and click Impossible (3rd card)
            print("Opening raid popup...")
            await ws_eval(ws, n, "if (window.$) $('.btn-event-raid').trigger('tap')"); n += 1
            await asyncio.sleep(2)

            # Click 3rd card (Impossible)
            print("Clicking Impossible card...")
            result = await ws_eval(ws, n, """
            (() => {
                if (!window.$) return 'no jquery';
                let cards = $('.btn-quest-start');
                if (cards.length >= 3) {
                    $(cards[2]).trigger('tap');
                    return 'Clicked IM card. Total cards=' + cards.length;
                }
                return 'Cards found=' + cards.length;
            })()
            """); n += 1
            print(f"  {result}")
            await asyncio.sleep(4)

            url = await ws_eval(ws, n, 'window.location.href'); n += 1
            print(f"URL after click: {url}")

            # If we're on supporter page, auto-select summon and start
            if 'supporter' in (url or ''):
                print("On supporter page, auto-selecting and starting...")
                # Auto select
                await ws_eval(ws, n, """
                    if (window.$) {
                        let auto = $('.btn-supporter-autoselect, .btn-usual-autoselect');
                        if (auto.length) auto.trigger('tap');
                    }
                """); n += 1
                await asyncio.sleep(2)
                
                # Click OK/Start
                res = await ws_eval(ws, n, """
                (() => {
                    if (!window.$) return 'no jq';
                    let ok = $('.btn-usual-ok');
                    if (ok.length) { ok.trigger('tap'); return 'clicked ok'; }
                    return 'ok not found';
                })()
                """); n += 1
                print(f"  Start: {res}")
                await asyncio.sleep(5)
                
                url2 = await ws_eval(ws, n, 'window.location.href'); n += 1
                print(f"URL after start: {url2}")

            # Wait for battle to fully load (up to 30s)
            print("Waiting for battle to load...")
            loaded = False
            for i in range(15):
                await asyncio.sleep(2)
                js_check = """
                (() => {
                    let atk = document.querySelector('.btn-attack-start');
                    if (atk) {
                        let r = atk.getBoundingClientRect();
                        return JSON.stringify({found: true, x:r.x, y:r.y, w:r.width, h:r.height});
                    }
                    return JSON.stringify({found: false});
                })()
                """
                val = json.loads(await ws_eval(ws, n, js_check) or '{}'); n += 1
                if val.get('found'):
                    print(f"  Battle loaded! Attack at ({val['x']:.0f},{val['y']:.0f})")
                    loaded = True
                    break
                print(f"  [{(i+1)*2}s] waiting...")

            if not loaded:
                print("Battle not loaded after 30s, taking screenshot anyway")

            img = await ws_screenshot(ws, n); n += 1
            cv2.imwrite('temp/battle_new.png', img)
            scale = img.shape[0] / 730
            print(f"Screenshot saved: {img.shape}, scale={scale:.4f}")

            # Find ALL battle UI elements
            js_all_battle = """
            (() => {
                let result = [];
                let all = document.querySelectorAll('[class]');
                for (let el of all) {
                    let r = el.getBoundingClientRect();
                    if (r.width > 20 && r.height > 10 && r.x > 50 && r.x < 560 && r.y > 0 && r.y < 730) {
                        let cls = (el.className || '').toString();
                        if (cls.match(/btn-|auto|full|semi|attack/i)) {
                            result.push({
                                cls: cls.slice(0,60),
                                x: Math.round(r.x), y: Math.round(r.y),
                                w: Math.round(r.width), h: Math.round(r.height),
                                text: el.innerText.slice(0,20).trim()
                            });
                        }
                    }
                }
                return JSON.stringify(result.slice(0,30));
            })()
            """
            battle_els = json.loads(await ws_eval(ws, n, js_all_battle) or '[]'); n += 1
            print(f"\nBattle UI elements ({len(battle_els)}):")
            for el in battle_els:
                print(f"  [{el['cls']:55}] ({el['x']:4},{el['y']:4}) {el['w']}x{el['h']} '{el['text']}'")

asyncio.run(main())
