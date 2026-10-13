import asyncio, base64, aiohttp, cv2, numpy as np

WS = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS) as ws:
            for i in range(12):
                await asyncio.sleep(2)
                
                await ws.send_json({'id': i*10+1, 'method': 'Runtime.evaluate', 'params': {'expression': 'window.location.href', 'returnByValue': True}})
                msg = await ws.receive_json()
                url = msg.get('result', {}).get('result', {}).get('value', '')
                
                js_check = "document.querySelector('.btn-attack-normal') != null"
                await ws.send_json({'id': i*10+2, 'method': 'Runtime.evaluate', 'params': {'expression': js_check, 'returnByValue': True}})
                msg2 = await ws.receive_json()
                has_attack = msg2.get('result', {}).get('result', {}).get('value', False)
                
                print(f'  [{(i+1)*2}s] has_attack={has_attack} url={url}')
                
                if has_attack:
                    print('Battle screen detected!')
                    break
            
            await ws.send_json({'id': 999, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
            msg = await ws.receive_json()
            data = base64.b64decode(msg['result']['data'])
            img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            cv2.imwrite('temp/battle_loaded.png', img)
            print(f'Saved battle_loaded.png size={img.shape}')

asyncio.run(main())
