import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            js = """
            (() => {
                let pop = document.querySelector('.pop-usual, .prt-popup-header, .cnt-raid-menu, [class*="pop-"]');
                let all = (pop ? pop.parentElement : document).querySelectorAll('*');
                let out = [];
                for (let e of all) {
                    let r = e.getBoundingClientRect();
                    if (r.width > 20 && r.height > 10 && r.x > 50 && r.x < 550 && r.y > 0 && r.y < 700) {
                        let t = (e.innerText || '').slice(0, 30).trim();
                        let cls = (e.className || '').toString();
                        if (cls.includes('btn') || t.length > 0) {
                            out.push({tag: e.tagName, cls: cls.slice(0, 40), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), text: t});
                        }
                    }
                }
                return out.slice(0, 25);
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            res = await ws.receive_json()
            items = res.get('result', {}).get('result', {}).get('value') or []
            for item in items:
                print(item)

asyncio.run(main())
