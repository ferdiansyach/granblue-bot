import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let els = document.querySelectorAll('[class*="auto"]');
                let found = [];
                for (let e of els) {
                    let r = e.getBoundingClientRect();
                    found.push({
                        cls: String(e.className),
                        x: Math.round(r.x),
                        y: Math.round(r.y),
                        w: Math.round(r.width),
                        h: Math.round(r.height),
                        style: e.getAttribute('style') || '',
                        computedDisplay: window.getComputedStyle(e).display
                    });
                }
                return found;
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            items = res.get('result', {}).get('result', {}).get('value') or []
            for it in items:
                print(it)

asyncio.run(main())
