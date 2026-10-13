import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let rules = [];
                for (let sheet of document.styleSheets) {
                    try {
                        for (let rule of sheet.cssRules) {
                            if (rule.selectorText && rule.selectorText.includes('.btn-auto')) {
                                rules.push(rule.cssText);
                            }
                        }
                    } catch(e) {}
                }
                return rules;
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            for r in res.get('result', {}).get('result', {}).get('value') or []:
                print(r)

asyncio.run(main())
