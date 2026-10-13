import asyncio, base64, aiohttp, cv2, numpy as np, json, os

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            # Click attack
            print("Clicking ATTACK...")
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {
                'expression': """
                (() => {
                    let atk = document.querySelector('.btn-attack-start');
                    if (atk) {
                        atk.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                        if (window.$) $(atk).trigger('tap');
                        return 'clicked';
                    }
                    return 'not found';
                })()
                """,
                'returnByValue': True
            }})
            res = await ws.receive_json()
            print("Atk click:", res.get('result', {}).get('result', {}).get('value'))

            # Take rapid screenshots
            for t in [0.1, 0.2, 0.4, 0.7, 1.2]:
                await asyncio.sleep(t)
                await ws.send_json({'id': int(t*100), 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
                r = await ws.receive_json()
                data = base64.b64decode(r['result']['data'])
                img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                cv2.imwrite(f'temp/rapid_atk_{t}s.png', img)
                print(f"Saved temp/rapid_atk_{t}s.png")

asyncio.run(main())
