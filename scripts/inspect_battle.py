import asyncio, base64, aiohttp, cv2, numpy as np, json, os

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            # Check elements
            js = """
            (() => {
                let all = document.querySelectorAll('*');
                let res = [];
                for (let e of all) {
                    let cls = (e.className || '').toString();
                    if (cls.match(/btn-attack|btn-auto|auto|full|semi|heal|summon|charge|skip|reload|back/i)) {
                        let r = e.getBoundingClientRect();
                        if (r.width > 15 && r.height > 10 && r.x >= 0 && r.y >= 0 && r.x < 600 && r.y < 750) {
                            res.push({
                                tag: e.tagName,
                                cls: cls.slice(0, 60),
                                x: Math.round(r.x),
                                y: Math.round(r.y),
                                w: Math.round(r.width),
                                h: Math.round(r.height),
                                text: (e.innerText || '').slice(0, 20).trim()
                            });
                        }
                    }
                }
                return JSON.stringify(res);
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            val = res.get('result', {}).get('result', {}).get('value')
            for item in json.loads(val or '[]'):
                print(item)

            # Screenshot
            await ws.send_json({'id': 2, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
            res2 = await ws.receive_json()
            data = base64.b64decode(res2['result']['data'])
            img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            cv2.imwrite('temp/battle_ready.png', img)
            print("Saved temp/battle_ready.png")

asyncio.run(main())
