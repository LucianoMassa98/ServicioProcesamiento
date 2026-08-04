#!/usr/bin/env python3
import cv2
import numpy as np
import sys
from pathlib import Path

VIDEO_PATH = sys.argv[1] if len(sys.argv) > 1 else 'prueba/2026-08-02_09-00-18.mp4'
SKIP = int(sys.argv[2]) if len(sys.argv) > 2 else 20

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print('ERROR: cannot open', VIDEO_PATH)
    sys.exit(1)

orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
print('video', VIDEO_PATH, 'size', orig_w, 'x', orig_h, 'fps', fps)

frame_idx = 0
processed = 0
print('frame,contours,filtered,mask_sum,area_min,area_max,area_mean,bbox_min,bbox_max')
while processed < 30:
    frame_idx += 1
    if frame_idx % SKIP != 0:
        if not cap.grab():
            break
        continue
    ret, frame = cap.read()
    if not ret:
        break
    h,w = frame.shape[:2]
    x1 = int(w * 0.08)
    x2 = int(w * 0.78)
    roi = frame[:, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([5,60,40]), np.array([25,255,240]))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)), iterations=1)
    contours,_ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filtered = []
    areas = []
    bbox_areas = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 150 or area > 12000:
            continue
        M = cv2.moments(cnt)
        if M['m00'] == 0:
            continue
        filtered.append(cnt)
        areas.append(area)
        x,y,wc,hc = cv2.boundingRect(cnt)
        bbox_areas.append((wc*hc, wc, hc))
    mask_sum = int(mask.sum())
    area_min = int(min(areas)) if areas else 0
    area_max = int(max(areas)) if areas else 0
    area_mean = round(sum(areas)/len(areas),1) if areas else 0
    bbox_min = min((b[0] for b in bbox_areas), default=0)
    bbox_max = max((b[0] for b in bbox_areas), default=0)
    print(f'{frame_idx},{len(contours)},{len(filtered)},{mask_sum},{area_min},{area_max},{area_mean},{bbox_min},{bbox_max}')
    processed += 1

cap.release()
