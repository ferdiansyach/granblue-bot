import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let cancels = document.querySelectorAll('.btn-usual-cancel, .pop-summon-detail .btn-usual-cancel');
                let res = [];
                for (let c of cancels) {
                    let r = c.getBoundingClientRect();
                    res.push({cls: c.className, x: r.x, y: r.y, w: r.width, h: r.height});
                    if (r.width > 0) {
                        c.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                        if (window.$) $(c).trigger('tap');
                    }
                }
                return res;
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            print(res.get('result', {}).get('result', {}).get('value'))

asyncio.run(main())
