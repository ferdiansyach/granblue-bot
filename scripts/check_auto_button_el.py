import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let els = document.querySelectorAll('*');
                let found = [];
                for (let e of els) {
                    let t = (e.innerText || '').trim();
                    if (t === 'Auto Button') {
                        let r = e.getBoundingClientRect();
                        found.push({
                            tag: e.tagName,
                            cls: e.className,
                            parentTag: e.parentElement ? e.parentElement.tagName : null,
                            parentCls: e.parentElement ? e.parentElement.className : null,
                            x: r.x, y: r.y, w: r.width, h: r.height
                        });
                    }
                }
                return found;
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            val = res.get('result', {}).get('result', {}).get('value')
            print(val)

asyncio.run(main())
