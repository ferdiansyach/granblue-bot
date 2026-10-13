import asyncio, base64, aiohttp, cv2, numpy as np, json, os

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            # 1. Open battle menu
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {
                'expression': "if (window.$) $('.btn-raid-menu.menu').trigger('tap');", 'returnByValue': True}})
            await ws.receive_json()
            await asyncio.sleep(1)

            # 2. Inspect buttons inside menu
            js = """
            (() => {
                let els = document.querySelectorAll('.cnt-raid-menu [class*="btn"], .pop-raid-menu [class*="btn"], [class*="btn-setting"]');
                let out = [];
                for (let e of els) {
                    let r = e.getBoundingClientRect();
                    out.push({cls: String(e.className), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), text: e.innerText});
                }
                return out;
            })()
            """
            await ws.send_json({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            print("Menu buttons:", res.get('result', {}).get('result', {}).get('value'))

asyncio.run(main())
