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
        print('ERROR frame', frame_id)
        continue
    h,w = frame.shape[:2]
    x1 = int(w*0.08)
    x2 = int(w*0.78)
    roi = frame[:, x1:x2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9,9), 2)
    circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.1,
        minDist=25,
        param1=70,
        param2=18,
        minRadius=6,
        maxRadius=24,
    )
    print('frame', frame_id, 'circles', 0 if circles is None else len(circles[0]))
    out = roi.copy()
    if circles is not None:
        for c in circles[0]:
            cv2.circle(out, (int(c[0]), int(c[1])), int(c[2]), (0,255,0), 2)
            cv2.circle(out, (int(c[0]), int(c[1])), 2, (0,0,255), -1)
    cv2.imwrite(f'prueba/hough_{frame_id}.png', out)

cap.release()
print('wrote hough debug images')
