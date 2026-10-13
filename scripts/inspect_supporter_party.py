import asyncio, aiohttp, json

async def main():
    url = 'http://127.0.0.1:9222/json'
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            tabs = await r.json()
            ws_url = [t['webSocketDebuggerUrl'] for t in tabs if 'granbluefantasy' in t.get('url', '')][0]
        async with s.ws_connect(ws_url) as ws:
            # Navigate to supporter page
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': 'window.location.hash = "#quest/supporter/947041/1/0/10673"', 'returnByValue': True}})
            await ws.receive_json()
            await asyncio.sleep(2)
            
            # Click auto select if available
            click_auto = """(() => {
                let btn = document.querySelector('.btn-usual-ok.se-quest-start, .btn-supporter-autoselect');
                if (btn) {
                    btn.click();
                    return 'clicked auto select';
                }
                return 'not found';
            })()"""
            await ws.send_json({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': click_auto, 'returnByValue': True}})
            res = await ws.receive_json()
            print('Auto select click:', res['result']['result']['value'])
            await asyncio.sleep(2)
            
            # Now let's inspect the entire DOM of the party confirmation page!
            js = """(() => {
                let all = document.querySelectorAll('*');
                let found = [];
                for (let e of all) {
                    let cls = (e.className || '').toString();
                    let id = e.id || '';
                    let text = (e.innerText || '').slice(0, 30).trim();
                    let r = e.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0 && (
                        cls.match(/deck|party|set|group|ok|start|btn/i) ||
                        text.match(/ok|start|party|group|set/i)
                    )) {
                        found.push({
                            tag: e.tagName,
                            id: id,
                            cls: cls.slice(0, 50),
                            text: text,
                            r: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}
                        });
                    }
                }
                return {
                    url: window.location.href,
                    scrollY: window.scrollY,
                    scrollHeight: document.body.scrollHeight,
                    innerHeight: window.innerHeight,
                    found: found
                };
            })()"""
            await ws.send_json({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res2 = await ws.receive_json()
            data = res2['result']['result']['value']
            print('URL:', data['url'])
            print('ScrollY:', data['scrollY'], 'ScrollHeight:', data['scrollHeight'], 'InnerHeight:', data['innerHeight'])
            print(f'Found {len(data["found"])} candidate elements:')
            for f in data['found']:
                print(f)

if __name__ == '__main__':
    asyncio.run(main())
