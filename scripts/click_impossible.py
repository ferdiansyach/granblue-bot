import asyncio
import json
import base64
import aiohttp
import cv2

async def main():
    """Navigate to a battle and capture screenshot for template update"""
    uri = 'ws://127.0.0.1:9222/devtools/page/77DC126F2B953A628BA4F37B9A4123CB'
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(uri) as ws:
            # First close any popup  
            js_close = """
            (() => {
                if (window.$) {
                    let closeBtn = window.$('.btn-usual-close');
                    if (closeBtn.length) {
                        closeBtn.trigger('tap');
                        return 'Closed popup';
                    }
                }
                return 'No popup to close';
            })()
            """
            await ws.send_json({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js_close, 'returnByValue': True}})
            msg = await ws.receive_json()
            print('Close:', msg.get('result', {}).get('result', {}).get('value'))
            
            await asyncio.sleep(1)

            # Trigger click on Impossible card (3rd card) - center x=437.5, y=448
            js_click_im = """
            (() => {
                if (window.$) {
                    let btn = window.$('.btn-event-raid');
                    if (btn.length) {
                        btn.trigger('tap');
                        return 'Opened raid popup';
                    }
                }
                return 'btn not found';
            })()
            """
            await ws.send_json({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_click_im, 'returnByValue': True}})
            msg = await ws.receive_json()
            print('Open popup:', msg.get('result', {}).get('result', {}).get('value'))
            
            await asyncio.sleep(2)
            
            # Click the 3rd card (Impossible) by tapping on btn-quest-start ico-clear
            js_click_im_card = """
            (() => {
                if (window.$) {
                    let cards = window.$('.btn-quest-start');
                    if (cards.length >= 3) {
                        window.$(cards[2]).trigger('tap');
                        return 'Clicked Impossible card, cards found: ' + cards.length;
                    }
                    return 'Cards found: ' + cards.length;
                }
                return 'No jQuery';
            })()
            """
            await ws.send_json({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': js_click_im_card, 'returnByValue': True}})
            msg = await ws.receive_json()
            print('Click IM card:', msg.get('result', {}).get('result', {}).get('value'))
            
            await asyncio.sleep(3)
            
            # Screenshot
            await ws.send_json({'id': 4, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}})
            msg = await ws.receive_json()
            data = base64.b64decode(msg['result']['data'])
            with open('temp/after_click_im.png', 'wb') as f:
                f.write(data)
            print('Saved temp/after_click_im.png')
            
            # Check URL to see if we navigated to a raid
            await ws.send_json({'id': 5, 'method': 'Runtime.evaluate', 'params': {'expression': 'window.location.href', 'returnByValue': True}})
            msg = await ws.receive_json()
            print('URL after click:', msg.get('result', {}).get('result', {}).get('value'))

if __name__ == '__main__':
    asyncio.run(main())
