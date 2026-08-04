#!/usr/bin/env python3
import cv2
import numpy as np
import sys

VIDEO_PATH = sys.argv[1] if len(sys.argv) > 1 else 'prueba/2026-08-02_09-00-18.mp4'
FRAME_IDS = [100, 200, 300, 400, 500]

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print('ERROR: cannot open', VIDEO_PATH)
    sys.exit(1)

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print('video', VIDEO_PATH, 'size', width, 'x', height)

x1 = int(width * 0.08)
x2 = int(width * 0.78)
print('roi x1', x1, 'x2', x2, 'width', x2-x1)

for frame_id in FRAME_IDS:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
    ret, frame = cap.read()
    if not ret:
        print('frame', frame_id, 'not readable')
        continue
    roi = frame[:, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h = hsv[:,:,0].ravel()
    s = hsv[:,:,1].ravel()
    v = hsv[:,:,2].ravel()
    print(f'frame={frame_id} mean_hsv={h.mean():.1f},{s.mean():.1f},{v.mean():.1f} min_hsv={h.min()},{s.min()},{v.min()} max_hsv={h.max()},{s.max()},{v.max()}')
    count_in = np.sum((h >= 5) & (h <= 25) & (s >= 60) & (s <= 255) & (v >= 40) & (v <= 240))
    print(f'  pixels_in_range={count_in} / {h.size} = {count_in/h.size:.3f}')
    print('  hue_histogram', np.bincount(h, minlength=180)[0:40].tolist()[:20])
    # Save diagnostic images
    cv2.imwrite(f'prueba/hsv_debug_frame_{frame_id}.png', frame)
    cv2.imwrite(f'prueba/hsv_debug_roi_{frame_id}.png', roi)
    mask = cv2.inRange(hsv, np.array([5,60,40]), np.array([25,255,240]))
    cv2.imwrite(f'prueba/hsv_debug_mask_{frame_id}.png', mask)

cap.release()
print('wrote hsv debug images to prueba/hsv_debug_*')
