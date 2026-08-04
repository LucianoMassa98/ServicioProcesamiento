#!/usr/bin/env python3
"""Quick diagnostic: extract sample frames, check HSV detection, report stats."""
import os, sys, cv2, numpy as np

PRUEBA_DIR = os.path.join(os.path.dirname(__file__), '..', 'prueba')
OUT_DIR = os.path.join(PRUEBA_DIR, 'diag')
os.makedirs(OUT_DIR, exist_ok=True)

HSV_LOWER = np.array([5, 80, 60])
HSV_UPPER = np.array([22, 255, 230])
MORPH_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

videos = [
    '2026-08-02_09-00-18.mp4',
    '2026-08-02_09-05-26.mp4',
    '2026-08-02_09-10-26.mp4',
    '2026-08-02_09-15-26.mp4',
    '2026-08-02_09-20-26.mp4',
]

for vname in videos:
    vpath = os.path.join(PRUEBA_DIR, vname)
    cap = cv2.VideoCapture(vpath)
    if not cap.isOpened():
        print(f'ERROR: {vname}')
        continue

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total / fps if fps > 0 else 0

    print(f'\n=== {vname} ===')
    print(f'  Dims: {w}x{h}  FPS: {fps:.1f}  Frames: {total}  Duration: {duration:.1f}s')

    # Sample frames at 10%, 25%, 50%, 75%
    for pct in [0.10, 0.25, 0.50, 0.75]:
        frame_num = int(total * pct)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            continue

        # HSV mask
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, MORPH_KERNEL, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, MORPH_KERNEL, iterations=1)

        px = cv2.countNonZero(mask)
        pct_area = 100.0 * px / (w * h)

        # Distance transform peaks
        dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        dist_smooth = cv2.GaussianBlur(dist, (7, 7), 0)
        kernel19 = np.ones((19, 19), np.uint8)
        local_max = cv2.dilate(dist_smooth, kernel19)
        peaks_mask = (dist_smooth == local_max) & (dist_smooth >= 9.5)
        num_peaks = np.sum(peaks_mask)

        # Also try smaller thresholds
        peaks_5 = np.sum((dist_smooth == local_max) & (dist_smooth >= 5.0))
        peaks_3 = np.sum((dist_smooth == local_max) & (dist_smooth >= 3.0))

        print(f'  Frame {frame_num} ({int(pct*100)}%): mask_px={px} ({pct_area:.1f}%) peaks(9.5)={num_peaks} peaks(5.0)={peaks_5} peaks(3.0)={peaks_3}')

        if dist_smooth.max() > 0:
            print(f'    dist_max={dist_smooth.max():.1f}  dist_mean(nonzero)={dist_smooth[dist_smooth>0].mean():.1f}')

        # Save annotated frame
        overlay = frame.copy()
        overlay[mask > 0] = [0, 255, 0]
        blended = cv2.addWeighted(frame, 0.6, overlay, 0.4, 0)

        # Draw peaks
        ys, xs = np.where(peaks_mask)
        for x, y in zip(xs, ys):
            cv2.circle(blended, (x, y), 4, (0, 0, 255), -1)

        # Draw line at 50%
        line_y = h // 2
        cv2.line(blended, (0, line_y), (w, line_y), (255, 180, 0), 2)

        base = vname.replace('.mp4', '')
        out_name = f'{base}_f{frame_num}.jpg'
        cv2.imwrite(os.path.join(OUT_DIR, out_name), blended)

    # Also check HSV distribution of detected pixels at frame 50%
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * 0.5))
    ret, frame = cap.read()
    if ret:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Check broader range
        for name, lo, hi in [
            ('current', np.array([5,80,60]), np.array([22,255,230])),
            ('broader', np.array([3,50,40]), np.array([25,255,240])),
            ('narrow',  np.array([8,100,80]), np.array([18,255,220])),
        ]:
            m = cv2.inRange(hsv, lo, hi)
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, MORPH_KERNEL, iterations=2)
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN, MORPH_KERNEL, iterations=1)
            print(f'  HSV [{name}]: {cv2.countNonZero(m)} px ({100*cv2.countNonZero(m)/(w*h):.1f}%)')

    cap.release()

print('\nDiagnostic frames saved to:', OUT_DIR)
