#!/usr/bin/env python3
import cv2
import numpy as np
import sys

VIDEO_PATH = sys.argv[1] if len(sys.argv) > 1 else 'prueba/2026-08-02_09-00-18.mp4'
FRAME_IDS = [100, 200, 300, 400, 500]

thresholds = [
    (5, 60, 40, 240),
    (8, 80, 50, 220),
    (10, 100, 60, 200),
    (12, 120, 80, 190),
    (15, 130, 90, 180),
    (18, 140, 100, 170),
]

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print('ERROR: cannot open', VIDEO_PATH)
    sys.exit(1)

for frame_id in FRAME_IDS:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
    ret, frame = cap.read()
    if not ret:
        print('ERROR frame', frame_id)
        continue
    h,w = frame.shape[:2]
    x1=int(w*0.08); x2=int(w*0.78)
    roi=frame[:,x1:x2]
    hsv=cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    print('\nframe', frame_id, 'roi shape', roi.shape)
    for h_low, s_low, v_low, v_high in thresholds:
        mask = cv2.inRange(hsv, np.array([h_low, s_low, v_low]), np.array([25,255,v_high]))
        cnts,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        areas=[cv2.contourArea(c) for c in cnts]
        print('  thresh', (h_low,s_low,v_low,v_high), 'mask', mask.sum()/255, 'contours', len(cnts), 'median_area', np.median(areas) if areas else 0, 'max_area', max(areas) if areas else 0)
cap.release()
