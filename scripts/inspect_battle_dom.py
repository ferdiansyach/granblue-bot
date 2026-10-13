import asyncio, aiohttp, json

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def inspect():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(WS) as ws:
            js = """
            (() => {
                let list = [];
                let all = document.querySelectorAll('*');
                for (let e of all) {
                    let cls = typeof e.className === 'string' ? e.className : '';
                    let txt = (e.innerText || '').trim();
                    let id = e.id || '';
                    if (cls.includes('auto') || cls.includes('attack') || cls.includes('command') || 
                        cls.includes('btn') || cls.includes('ability') || cls.includes('character') ||
                        txt === 'Auto' || txt === 'Full' || txt === 'Semi' || txt === 'Attack') {
                        let r = e.getBoundingClientRect();
                        let st = window.getComputedStyle(e);
                        if (r.width > 5 && r.height > 5 && st.display !== 'none' && st.visibility !== 'hidden') {
                            list.push({
                                tag: e.tagName,
                                id: id,
                                cls: cls.slice(0, 40),
                                text: txt.slice(0, 30).replace(/\\n/g, ' '),
                                rect: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}
                            });
                        }
                    }
                }
                return list;
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}})
            r = await ws.receive_json()
            val = r.get('result', {}).get('result', {}).get('value', [])
            print(f"Total elements: {len(val)}")
            for item in val:
                print(item)

asyncio.run(inspect())
