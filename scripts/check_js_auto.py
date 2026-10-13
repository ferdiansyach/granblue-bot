import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let btn = document.querySelector('.btn-auto');
                if (!btn) return 'no btn';
                // Check if there is a function in stage or view
                let results = [];
                for (let k in window) {
                    if (k.toLowerCase().includes('auto')) results.push(k);
                }
                // Check stage.gGameStatus
                let gs = window.stage ? window.stage.gGameStatus : null;
                return {
                    windowAutoKeys: results,
                    btnParent: btn.parentElement ? btn.parentElement.className : null,
                    btnClasses: btn.className,
                    btnStyle: btn.style.cssText
                };
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            val = res.get('result', {}).get('result', {}).get('value')
            print(val)

asyncio.run(main())
