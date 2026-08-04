#!/usr/bin/env python3
import cv2
import numpy as np
import sys

VIDEO_PATH = sys.argv[1] if len(sys.argv) > 1 else 'prueba/2026-08-02_09-00-18.mp4'
SKIP = int(sys.argv[2]) if len(sys.argv) > 2 else 20
FRAME_LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 60

LOWER = np.array([8, 100, 60])
UPPER = np.array([20, 255, 190])

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print('ERROR open', VIDEO_PATH)
    sys.exit(1)

frame_idx = 0
processed = 0
found_total = 0
while processed < FRAME_LIMIT:
    frame_idx += 1
    if frame_idx % SKIP != 0:
        if not cap.grab():
            break
        continue
    ret, frame = cap.read()
    if not ret:
        break
    h, w = frame.shape[:2]
    x1 = int(w * 0.08)
    x2 = int(w * 0.78)
    roi = frame[:, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER, UPPER)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.erode(mask, kernel, iterations=1)
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    local = cv2.dilate(dist, np.ones((15,15), np.uint8))
    peaks = (dist == local) & (dist > 12)
    peaks = peaks.astype(np.uint8)
    contours, _ = cv2.findContours(peaks, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centroids = []
    for cnt in contours:
        M = cv2.moments(cnt)
        if M['m00'] == 0:
            continue
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        centroids.append((cx, cy))
    found_total += len(centroids)
    print('frame', frame_idx, 'centroids', len(centroids), 'mask_sum', int(mask.sum()/255), 'contours', len(contours))
    processed += 1

print('frames processed', processed, 'avg', found_total/processed if processed else 0)
cap.release()
