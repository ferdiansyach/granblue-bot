import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let autoBtn = document.querySelector('.btn-auto');
                let listeners = null;
                return {
                    auto_flag: window.auto_flag,
                    autoBtnDisplay: autoBtn ? autoBtn.style.display : null,
                    autoBtnParent: autoBtn ? autoBtn.parentElement.className : null
                };
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            print(res.get('result', {}).get('result', {}).get('value'))

asyncio.run(main())
