import asyncio, aiohttp

async def click_menu():
    url = 'http://127.0.0.1:9222/json'
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            tabs = await r.json()
            ws_url = [t['webSocketDebuggerUrl'] for t in tabs if 'granbluefantasy' in t.get('url', '')][0]
        async with s.ws_connect(ws_url) as ws:
            # Click menu using dispatchMouseEvent at x=480, y=30
            await ws.send_json({'id': 1, 'method': 'Input.dispatchMouseEvent', 'params': {'type': 'mousePressed', 'x': 480, 'y': 30, 'button': 'left', 'clickCount': 1}})
            await ws.receive_json()
            await ws.send_json({'id': 2, 'method': 'Input.dispatchMouseEvent', 'params': {'type': 'mouseReleased', 'x': 480, 'y': 30, 'button': 'left', 'clickCount': 1}})
            await ws.receive_json()
            await asyncio.sleep(1)
            
            # Inspect popups
            js = """(() => {
                let els = document.querySelectorAll('*');
                let found = [];
                for (let e of els) {
                    let cls = (e.className || '').toString();
                    let r = e.getBoundingClientRect();
                    if (r.width > 20 && r.height > 10 && (cls.includes('retreat') || cls.includes('btn') || cls.includes('pop'))) {
                        found.push({cls, text: e.innerText?.slice(0, 20), r: {x: r.x, y: r.y, w: r.width, h: r.height}});
                    }
                }
                return found.filter(f => f.r.y > 50 && f.r.y < 600);
            })()"""
            await ws.send_json({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            items = res['result']['result']['value']
            print(f'Found {len(items)} items:')
            for item in items:
                print(item)

if __name__ == '__main__':
    asyncio.run(click_menu())
