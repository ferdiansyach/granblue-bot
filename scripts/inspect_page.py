import asyncio
import json
import aiohttp

async def main():
    uri = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(uri) as ws:
            js = """
            (() => {
                let pop = document.querySelector('.pop-select-raid');
                if (!pop) return 'No pop';
                let els = pop.querySelectorAll('*');
                let res = [];
                for (let e of els) {
                    let r = e.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0 && e.children.length === 0) {
                        res.push({
                            tag: e.tagName,
                            cls: e.className,
                            text: e.innerText ? e.innerText.trim() : '',
                            rect: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}
                        });
                    }
                }
                return JSON.stringify(res);
            })()
            """
            await ws.send_json({
                'id': 1,
                'method': 'Runtime.evaluate',
                'params': {'expression': js, 'returnByValue': True}
            })
            msg = await ws.receive_json()
            items = json.loads(msg.get('result', {}).get('result', {}).get('value') or '[]')
            print(f"Found {len(items)} elements inside pop-select-raid:")
            for item in items:
                print(item)

if __name__ == '__main__':
    asyncio.run(main())
