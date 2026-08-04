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

for frame_id in FRAME_IDS:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
    ret, frame = cap.read()
    if not ret:
        print('ERROR reading frame', frame_id)
        continue
    h,w = frame.shape[:2]
    x1 = int(w*0.08); x2 = int(w*0.78)
    roi = frame[:, x1:x2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7,7), 1.5)
    hist = cv2.calcHist([blur],[0],None,[256],[0,256]).ravel()
    total = blur.size
    for th in [50, 70, 90, 110, 130, 150]:
        count = int((blur < th).sum())
        print(f'frame={frame_id} th<{th} count={count} pct={count/total:.3f}')
    print('  gray min/max/mean', int(blur.min()), int(blur.max()), round(float(blur.mean()),1))
    if frame_id == FRAME_IDS[0]:
        print('  sample gray values', blur.ravel()[:50].tolist())
    dark = (blur < 100).astype(np.uint8) * 255
    cnts,_ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas = [cv2.contourArea(c) for c in cnts]
    areas.sort(reverse=True)
    print('  dark contours', len(cnts), 'top areas', areas[:10])
    print('---')
cap.release()
