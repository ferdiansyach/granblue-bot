import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                // Check battle settings in localStorage or window
                let out = {};
                for (let k of Object.keys(localStorage)) {
                    if (k.toLowerCase().includes('battle') || k.toLowerCase().includes('auto')) {
                        out[k] = localStorage.getItem(k);
                    }
                }
                return out;
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            val = res.get('result', {}).get('result', {}).get('value')
            print("LocalStorage:", val)

asyncio.run(main())
