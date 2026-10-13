import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let cards = document.querySelectorAll('.btn-quest-start, [class*="quest-start"], [class*="raid-start"], [class*="btn-raid"]');
                let out = [];
                for (let c of cards) {
                    let r = c.getBoundingClientRect();
                    out.push({cls: (c.className||'').toString(), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), text: (c.innerText||'').slice(0, 30)});
                }
                return JSON.stringify(out);
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            val = res.get('result', {}).get('result', {}).get('value')
            for item in json.loads(val or '[]'):
                print(item)

asyncio.run(main())
