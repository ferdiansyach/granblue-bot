import re

with open('backend/bot/combat_mode.py', 'r', encoding='utf-8') as f:
    text = f.read()

imgs = set()
for match in re.finditer(r'(?:find_button|find_and_click_button|confirm_location|wait_vanish|find_all)\(["\']([^"\']+)["\']', text):
    imgs.add(match.group(1))

print(f'Templates used in combat_mode.py ({len(imgs)}):')
for img in sorted(imgs):
    print(' ', img)
