import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let btns = document.querySelectorAll('.btn-usual-close, .btn-close, .btn-set-setting');
                for (let b of btns) {
                    let r = b.getBoundingClientRect();
                    if (r.width > 0) {
                        b.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                        if (window.$) $(b).trigger('tap');
                        return 'Clicked ' + b.className;
                    }
                }
                return 'None';
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            print(res.get('result', {}).get('result', {}).get('value'))

asyncio.run(main())
