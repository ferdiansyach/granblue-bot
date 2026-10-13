import asyncio, base64, aiohttp, cv2, numpy as np, json, os

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            # Check url
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': 'window.location.href', 'returnByValue': True}})
            res = await ws.receive_json()
            url = res.get('result', {}).get('result', {}).get('value')
            print('URL:', url)

            # Screenshot
            await ws.send_json({'id': 2, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
            res2 = await ws.receive_json()
            data = base64.b64decode(res2['result']['data'])
            img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            os.makedirs('temp', exist_ok=True)
            cv2.imwrite('temp/current_battle_screen.png', img)
            print('Saved temp/current_battle_screen.png, shape:', img.shape)

            # Inspect elements related to auto / attack / battle
            js = """
            (() => {
                let els = document.querySelectorAll('*');
                let out = [];
                for (let e of els) {
                    let cls = (e.className || '').toString();
                    if (cls.match(/btn-attack|btn-auto|auto|full|semi|quick|heal|ability|summon/i)) {
                        let r = e.getBoundingClientRect();
                        if (r.width > 10 && r.height > 10 && r.x >= 0 && r.y >= 0 && r.x < 1000 && r.y < 800) {
                            out.push({
                                tag: e.tagName,
                                cls: cls.slice(0, 50),
                                x: Math.round(r.x),
                                y: Math.round(r.y),
                                w: Math.round(r.width),
                                h: Math.round(r.height),
                                text: (e.innerText || '').slice(0, 20).trim()
                            });
                        }
                    }
                }
                return JSON.stringify(out);
            })()
            """
            await ws.send_json({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res3 = await ws.receive_json()
            val = res3.get('result', {}).get('result', {}).get('value')
            els = json.loads(val or '[]')
            print(f'Found {len(els)} elements:')
            for e in els:
                print(' ', e)

asyncio.run(main())
