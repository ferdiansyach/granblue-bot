import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let btn = document.querySelector('.btn-auto');
                if (!btn) return 'no btn';
                // Check event listeners or backbone view
                let view = window.stage ? window.stage.gGameStatus : null;
                let autoSetting = window.Game ? window.Game.setting : null;
                return {
                    className: btn.className,
                    style: btn.style.cssText,
                    rect: btn.getBoundingClientRect(),
                    autoSetting: autoSetting ? JSON.stringify(autoSetting).slice(0, 300) : null
                };
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            val = res.get('result', {}).get('result', {}).get('value')
            print(val)

asyncio.run(main())
