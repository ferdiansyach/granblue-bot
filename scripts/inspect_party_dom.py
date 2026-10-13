import asyncio, aiohttp, json

async def main():
    url = 'http://127.0.0.1:9222/json'
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            tabs = await r.json()
            ws_url = [t['webSocketDebuggerUrl'] for t in tabs if 'granbluefantasy' in t.get('url', '')][0]
        async with s.ws_connect(ws_url) as ws:
            # Navigate to party
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': 'window.location.hash = "#party/index/0/0/1"', 'returnByValue': True}})
            await ws.receive_json()
            await asyncio.sleep(2)
            
            # Inspect party tabs, groups, decks
            js = """(() => {
                let els = document.querySelectorAll('*');
                let found = [];
                for (let e of els) {
                    let cls = (e.className || '').toString();
                    if (cls.match(/btn-set|tab-set|prt-deck|btn-deck|deck-group|btn-group|party-name/i)) {
                        let r = e.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) {
                            found.push({
                                tag: e.tagName,
                                cls: cls.slice(0, 50),
                                text: e.innerText ? e.innerText.slice(0, 20).trim() : '',
                                rect: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}
                            });
                        }
                    }
                }
                return {hash: window.location.hash, found};
            })()"""
            await ws.send_json({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            data = res['result']['result']['value']
            print('Hash:', data['hash'])
            print(f'Found {len(data["found"])} elements:')
            for item in data['found']:
                print(item)

if __name__ == '__main__':
    asyncio.run(main())
