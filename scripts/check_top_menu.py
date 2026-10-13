import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let els = document.querySelectorAll('*');
                let out = [];
                for (let e of els) {
                    let r = e.getBoundingClientRect();
                    if (r.y >= 0 && r.y <= 60 && r.x >= 400 && r.x <= 560 && r.width > 20) {
                        out.push({tag: e.tagName, cls: e.className, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), text: e.innerText});
                    }
                }
                return out;
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            print(res.get('result', {}).get('result', {}).get('value'))

asyncio.run(main())
