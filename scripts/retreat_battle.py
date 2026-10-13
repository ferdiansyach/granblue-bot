import asyncio, aiohttp

async def retreat():
    url = 'http://127.0.0.1:9222/json'
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            tabs = await r.json()
            ws_url = [t['webSocketDebuggerUrl'] for t in tabs if 'granbluefantasy' in t.get('url', '')][0]
        async with s.ws_connect(ws_url) as ws:
            # Click raid menu
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {
                'expression': 'document.querySelector(".btn-raid-menu.menu")?.click()',
                'returnByValue': True
            }})
            await ws.receive_json()
            await asyncio.sleep(1)
            
            # Click retreat button in popup
            js_retreat = """(() => {
                let btns = document.querySelectorAll('.pop-raid-menu *');
                for (let b of btns) {
                    if ((b.className || '').includes('retreat') || (b.innerText || '').toLowerCase().includes('retreat')) {
                        b.click();
                        return 'clicked retreat: ' + b.className;
                    }
                }
                return 'retreat not found';
            })()"""
            await ws.send_json({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_retreat, 'returnByValue': True}})
            res2 = await ws.receive_json()
            print(res2['result']['result']['value'])
            await asyncio.sleep(1)
            
            # Click confirm retreat (usually .btn-usual-ok or .btn-pop-ok)
            js_confirm = """(() => {
                let ok = document.querySelector('.pop-usual .btn-usual-ok, .pop-usual .btn-primary, .pop-usual [class*="btn-ok"]');
                if (ok) {
                    ok.click();
                    return 'confirmed retreat';
                }
                return 'ok not found';
            })()"""
            await ws.send_json({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': js_confirm, 'returnByValue': True}})
            res3 = await ws.receive_json()
            print(res3['result']['result']['value'])

if __name__ == '__main__':
    asyncio.run(retreat())
