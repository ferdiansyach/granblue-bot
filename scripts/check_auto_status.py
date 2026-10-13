import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                // Find scripts or functions mentioning btn-auto
                let autoBtn = document.querySelector('.btn-auto');
                let info = {};
                if (autoBtn) {
                    info.outerHTML = autoBtn.outerHTML;
                    info.dataset = Object.assign({}, autoBtn.dataset);
                }
                // Check if window.Game or window.stage has auto toggle
                if (window.stage && window.stage.gGameStatus) {
                    let gs = window.stage.gGameStatus;
                    info.is_auto = gs.is_auto;
                    info.auto = gs.auto;
                }
                return info;
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            print(res.get('result', {}).get('result', {}).get('value'))

asyncio.run(main())
