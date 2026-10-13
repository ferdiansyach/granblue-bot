import asyncio, base64, aiohttp, cv2, numpy as np, json, os

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let c = document.querySelector('.btn-usual-close.ev-back');
                if (c) {
                    c.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                    if (window.$) $(c).trigger('tap');
                    return 'Clicked close';
                }
                return 'No close button';
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            print(res.get('result', {}).get('result', {}).get('value'))

            await asyncio.sleep(1)

            # Screenshot
            await ws.send_json({'id': 2, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
            res2 = await ws.receive_json()
            data = base64.b64decode(res2['result']['data'])
            img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            cv2.imwrite('temp/after_close_menu.png', img)
            print("Saved temp/after_close_menu.png")

asyncio.run(main())
