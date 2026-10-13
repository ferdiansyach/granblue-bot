import cv2

ok_tmpl = cv2.imread('images/buttons/ok.jpg')
cancel_tmpl = cv2.imread('images/buttons/cancel.jpg')
summon_header = cv2.imread('images/headers/summon_details_header.jpg')

cv2.imwrite('temp/old_ok.png', ok_tmpl)
cv2.imwrite('temp/old_cancel.png', cancel_tmpl)
cv2.imwrite('temp/old_summon_details_header.png', summon_header)

print(f"old_ok: {ok_tmpl.shape if ok_tmpl is not None else None}")
print(f"old_cancel: {cancel_tmpl.shape if cancel_tmpl is not None else None}")
print(f"old_summon_details_header: {summon_header.shape if summon_header is not None else None}")
