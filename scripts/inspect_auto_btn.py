import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let btn = document.querySelector('.btn-auto');
                if (!btn) return 'no .btn-auto';
                let p = btn.parentElement;
                return {
                    btnOuter: btn.outerHTML.slice(0, 200),
                    parentOuter: p ? p.outerHTML.slice(0, 300) : null,
                    computedDisplay: window.getComputedStyle(btn).display,
                    computedVisibility: window.getComputedStyle(btn).visibility
                };
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            val = res.get('result', {}).get('result', {}).get('value')
            print(json.dumps(val, indent=2))

asyncio.run(main())
