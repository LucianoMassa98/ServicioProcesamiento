#!/usr/bin/env python3
"""
Test reduced morphology approach: the key insight is that MORPH_CLOSE with 7x7 kernel
fills the gaps between belt rods, creating one massive blob. By reducing/removing closing,
belt rods stay as thin stripes while eggs create wider blobs.
"""
import os, sys, cv2, numpy as np

PRUEBA_DIR = os.path.join(os.path.dirname(__file__), '..', 'prueba')
OUT_DIR = os.path.join(PRUEBA_DIR, 'diag')
os.makedirs(OUT_DIR, exist_ok=True)

HSV_LOWER = np.array([5, 80, 60])
HSV_UPPER = np.array([22, 255, 230])


def detect_eggs_reduced_morph(frame, close_k=3, close_iter=1, open_k=3, open_iter=1,
                                peak_window=15, min_peak_dist=8.0,
                                x_margin=20):
    """Detect eggs with minimal morphology so belt gaps stay open."""
    h, w = frame.shape[:2]
    
    # Crop edges to exclude belt machinery
    roi = frame[:, x_margin:w-x_margin]
    
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
    
    # Minimal morphology - don't fill belt gaps!
    if close_k > 0:
        k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_k, close_k))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k_close, iterations=close_iter)
    if open_k > 0:
        k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_k, open_k))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k_open, iterations=open_iter)
    
    # Distance transform
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    dist_smooth = cv2.GaussianBlur(dist, (7, 7), 0)
    
    # Peak detection
    kernel = np.ones((peak_window, peak_window), np.uint8)
    local_max = cv2.dilate(dist_smooth, kernel)
    peaks_mask = (dist_smooth == local_max) & (dist_smooth >= min_peak_dist)
    ys, xs = np.where(peaks_mask)
    
    # Adjust x coordinates back to full frame
    centroids = [(x + x_margin, y) for x, y in zip(xs, ys)]
    
    return centroids, mask, dist_smooth


# Test configurations
configs = [
    # name, close_k, close_iter, open_k, open_iter, peak_window, min_peak_dist, x_margin
    ('no_morph',           0, 0, 0, 0, 15, 6.0, 20),
    ('tiny_close',         3, 1, 3, 1, 15, 6.0, 20),
    ('small_close',        5, 1, 3, 1, 15, 7.0, 20),
    ('no_morph_strict',    0, 0, 0, 0, 19, 8.0, 25),
    ('tiny_strict',        3, 1, 3, 1, 19, 8.0, 25),
    ('no_morph_vstrict',   0, 0, 0, 0, 21, 10.0, 25),
]

videos = {
    '2026-08-02_09-00-18.mp4': 48,
    '2026-08-02_09-05-26.mp4': 250,
    '2026-08-02_09-10-26.mp4': 84,
    '2026-08-02_09-15-26.mp4': 3,
    '2026-08-02_09-20-26.mp4': 281,
}

for vname, expected in videos.items():
    vpath = os.path.join(PRUEBA_DIR, vname)
    cap = cv2.VideoCapture(vpath)
    if not cap.isOpened():
        continue
    
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f'\n=== {vname} (expected ~{expected}, {w}x{h}) ===')
    
    for pct in [0.25, 0.50, 0.75]:
        frame_num = int(total * pct)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            continue
        
        print(f'  Frame {frame_num} ({int(pct*100)}%):')
        
        for cfg_name, ck, ci, ok, oi, pw, mpd, xm in configs:
            centroids, mask, dist = detect_eggs_reduced_morph(
                frame, close_k=ck, close_iter=ci, open_k=ok, open_iter=oi,
                peak_window=pw, min_peak_dist=mpd, x_margin=xm
            )
            mask_pct = 100.0 * cv2.countNonZero(mask) / (mask.shape[0] * mask.shape[1])
            dist_max = dist.max() if dist.max() > 0 else 0
            print(f'    [{cfg_name:20s}] det={len(centroids):3d}  mask={mask_pct:5.1f}%  dist_max={dist_max:.1f}')
            
            # Save visualization for the 50% frame
            if pct == 0.50:
                base = vname.replace('.mp4', '')
                vis = frame.copy()
                line_y = h // 2
                cv2.line(vis, (0, line_y), (w, line_y), (255, 180, 0), 2)
                for cx, cy in centroids:
                    cv2.circle(vis, (cx, cy), 8, (0, 255, 0), 2)
                    cv2.circle(vis, (cx, cy), 2, (0, 0, 255), -1)
                cv2.putText(vis, f'{cfg_name}: {len(centroids)} det', (5, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.imwrite(os.path.join(OUT_DIR, f'{base}_v2_{cfg_name}.jpg'), vis)
                
                # Save mask
                cv2.imwrite(os.path.join(OUT_DIR, f'{base}_v2_mask_{cfg_name}.jpg'), mask)
                
                # Save distance transform (normalized)
                if dist.max() > 0:
                    dist_vis = (dist / dist.max() * 255).astype(np.uint8)
                    dist_vis = cv2.applyColorMap(dist_vis, cv2.COLORMAP_JET)
                    cv2.imwrite(os.path.join(OUT_DIR, f'{base}_v2_dist_{cfg_name}.jpg'), dist_vis)
    
    cap.release()

print('\nImages saved to:', OUT_DIR)
