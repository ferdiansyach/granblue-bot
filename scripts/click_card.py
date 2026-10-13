import asyncio, base64, aiohttp, cv2, numpy as np, json, os

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            # 1. Click the 3rd card (Impossible)
            print("Clicking Impossible card (index 2)...")
            click_js = """
            (() => {
                if (!window.$) return 'no jquery';
                let cards = $('.btn-quest-start');
                if (cards.length >= 3) {
                    $(cards[2]).trigger('tap');
                    return 'Tapped 3rd card';
                }
                return 'Cards length: ' + cards.length;
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': click_js, 'returnByValue': True}})
            res = await ws.receive_json()
            print("Click result:", res.get('result', {}).get('result', {}).get('value'))

            # Wait 3 seconds
            await asyncio.sleep(3)

            # Check URL
            await ws.send_json({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': 'window.location.href', 'returnByValue': True}})
            res2 = await ws.receive_json()
            url = res2.get('result', {}).get('result', {}).get('value')
            print("New URL:", url)

            # Take screenshot
            await ws.send_json({'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
            res3 = await ws.receive_json()
            data = base64.b64decode(res3['result']['data'])
            img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            os.makedirs('temp', exist_ok=True)
            cv2.imwrite('temp/after_click_card.png', img)
            print("Saved temp/after_click_card.png, shape:", img.shape)

asyncio.run(main())
