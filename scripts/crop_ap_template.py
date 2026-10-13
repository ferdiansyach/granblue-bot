import asyncio
import json
import base64
import aiohttp
import cv2
import numpy as np

async def main():
    uri = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(uri) as ws:
            # Trigger the raid popup to appear
            js_trigger = """
            (() => {
                if (window.$) {
                    let btn = window.$('.btn-event-raid');
                    if (btn.length) {
                        btn.trigger('tap');
                        return 'Triggered popup open';
                    }
                    return 'btn-event-raid not found, page may be: ' + document.location.hash;
                }
                return 'No jQuery';
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js_trigger, 'returnByValue': True}})
            msg = await ws.receive_json()
            print('Trigger:', msg.get('result', {}).get('result', {}).get('value'))

            await asyncio.sleep(2)

            # Take screenshot
            await ws.send_json({'id': 2, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
            msg = await ws.receive_json()
            data = base64.b64decode(msg['result']['data'])
            with open('temp/popup_for_crop.png', 'wb') as f:
                f.write(data)
            print('Saved popup screenshot')

            # Get exact AP button positions
            js_positions = """
            (() => {
                let apEls = document.querySelectorAll('.txt-need-ap');
                let res = [];
                for (let el of apEls) {
                    let parent = el.parentElement;
                    let r = parent.getBoundingClientRect();
                    res.push({
                        cls: parent.className,
                        x: r.x, y: r.y, w: r.width, h: r.height,
                        cx: r.x + r.width/2, cy: r.y + r.height/2,
                        ap_text: el.innerText
                    });
                }
                return JSON.stringify(res);
            })()
            """
            await ws.send_json({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': js_positions, 'returnByValue': True}})
            msg = await ws.receive_json()
            positions = json.loads(msg.get('result', {}).get('result', {}).get('value') or '[]')
            print('AP Button positions:', json.dumps(positions, indent=2))

            return positions

if __name__ == '__main__':
    result = asyncio.run(main())
    
    # Now crop ap.jpg from the first (Very Hard) card
    img = cv2.imread('temp/popup_for_crop.png')
    if img is None:
        print('Could not load popup_for_crop.png')
        exit()
    
    print('Screenshot size:', img.shape)
    
    for i, pos in enumerate(result):
        ap_x = int(pos['x']) 
        ap_y = int(pos['y'])
        ap_w = int(pos['w'])
        ap_h = int(pos['h'])
        
        print(f'Card {i}: x={ap_x}, y={ap_y}, w={ap_w}, h={ap_h}')
        
        # Crop the AP cost text region (the green "AP-0" label inside the card)
        # ap_el is the child .txt-need-ap - need to get its rect
    
    if result:
        # Get AP text label position from first card
        pos = result[0]
        # The AP text is inside the card, roughly at y+110 area
        # From DOM: txt-need-ap at x=126, y=471, w=90, h=28 for first card
        # Let's crop from the 'ap' label using document coords
        pass
