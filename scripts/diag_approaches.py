#!/usr/bin/env python3
"""
Test multiple detection approaches on a single video to find the best one.
Compares: morphological refinement, Hough circles, contour+circularity.
"""
import os, sys, cv2, numpy as np, time

PRUEBA_DIR = os.path.join(os.path.dirname(__file__), '..', 'prueba')
OUT_DIR = os.path.join(PRUEBA_DIR, 'diag')
os.makedirs(OUT_DIR, exist_ok=True)

HSV_LOWER = np.array([5, 80, 60])
HSV_UPPER = np.array([22, 255, 230])
MORPH_KERNEL_SM = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))


def approach_morph_opening(frame, large_k=15):
    """Use large morphological opening to remove belt rod patterns, keep eggs."""
    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
    # Standard close/open
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, MORPH_KERNEL_SM, iterations=2)
    # Large opening: removes thin belt rods, keeps large round eggs
    large_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (large_k, large_k))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, large_kernel, iterations=2)
    
    # Find contours and filter by area/circularity
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centroids = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 200 < area < 8000:
            peri = cv2.arcLength(cnt, True)
            if peri > 0:
                circ = 4 * np.pi * area / (peri * peri)
                if circ > 0.3:  # reasonably circular
                    M = cv2.moments(cnt)
                    if M['m00'] > 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        centroids.append((cx, cy))
    return centroids, mask


def approach_hough_circles(frame, dp=1.2, min_dist=25, p1=80, p2=25, min_r=8, max_r=25):
    """Use Hough Circle Transform to detect round eggs."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=dp,
        minDist=min_dist, param1=p1, param2=p2,
        minRadius=min_r, maxRadius=max_r,
    )
    centroids = []
    if circles is not None:
        for c in circles[0]:
            centroids.append((int(c[0]), int(c[1])))
    return centroids


def approach_texture_bandpass(frame):
    """Bandpass filter to isolate egg-sized features from belt texture."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    # Heavy blur to remove fine belt texture
    bg = cv2.GaussianBlur(gray, (51, 51), 0)
    # Lighter blur
    fg = cv2.GaussianBlur(gray, (5, 5), 0)
    # Bandpass: features between 5px and 51px in scale
    diff = cv2.absdiff(fg, bg)
    diff_norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, thresh = cv2.threshold(diff_norm, 20, 255, cv2.THRESH_BINARY)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centroids = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 200 < area < 8000:
            peri = cv2.arcLength(cnt, True)
            if peri > 0:
                circ = 4 * np.pi * area / (peri * peri)
                if circ > 0.25:
                    M = cv2.moments(cnt)
                    if M['m00'] > 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        centroids.append((cx, cy))
    return centroids, thresh


def approach_adaptive_threshold(frame):
    """Use adaptive thresholding on grayscale to find egg shadows/highlights."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (11, 11), 0)
    
    # Adaptive threshold highlights local intensity variations
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 31, 5)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centroids = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 200 < area < 8000:
            peri = cv2.arcLength(cnt, True)
            if peri > 0:
                circ = 4 * np.pi * area / (peri * peri)
                if circ > 0.3:
                    M = cv2.moments(cnt)
                    if M['m00'] > 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        centroids.append((cx, cy))
    return centroids, thresh


def draw_detections(frame, centroids, color=(0, 0, 255), label=""):
    vis = frame.copy()
    for cx, cy in centroids:
        cv2.circle(vis, (cx, cy), 8, color, 2)
        cv2.circle(vis, (cx, cy), 2, color, -1)
    h, w = vis.shape[:2]
    cv2.line(vis, (0, h//2), (w, h//2), (255, 180, 0), 2)
    cv2.putText(vis, f'{label}: {len(centroids)} detections', (5, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return vis


# Test on sample frames from each video
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
    
    print(f'\n=== {vname} (expected ~{expected}) ===')
    
    for pct in [0.25, 0.50, 0.75]:
        frame_num = int(total * pct)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if not ret:
            continue
        
        print(f'  Frame {frame_num} ({int(pct*100)}%):')
        
        # Test each approach
        c_morph, mask_morph = approach_morph_opening(frame, large_k=15)
        print(f'    Morph opening (k=15):   {len(c_morph)} detections')
        
        c_morph2, mask_morph2 = approach_morph_opening(frame, large_k=21)
        print(f'    Morph opening (k=21):   {len(c_morph2)} detections')
        
        c_hough = approach_hough_circles(frame)
        print(f'    Hough circles:          {len(c_hough)} detections')
        
        c_hough2 = approach_hough_circles(frame, dp=1.5, p2=30, min_r=10, max_r=22)
        print(f'    Hough circles (strict): {len(c_hough2)} detections')
        
        c_band, mask_band = approach_texture_bandpass(frame)
        print(f'    Texture bandpass:       {len(c_band)} detections')
        
        c_adapt, mask_adapt = approach_adaptive_threshold(frame)
        print(f'    Adaptive threshold:     {len(c_adapt)} detections')
        
        # Save comparison images for the 50% frame
        if pct == 0.50:
            base = vname.replace('.mp4', '')
            
            vis_morph = draw_detections(frame, c_morph, (0, 255, 0), 'Morph k=15')
            cv2.imwrite(os.path.join(OUT_DIR, f'{base}_morph15.jpg'), vis_morph)
            
            vis_morph2 = draw_detections(frame, c_morph2, (0, 255, 0), 'Morph k=21')
            cv2.imwrite(os.path.join(OUT_DIR, f'{base}_morph21.jpg'), vis_morph2)
            
            vis_hough = draw_detections(frame, c_hough, (255, 0, 0), 'Hough')
            cv2.imwrite(os.path.join(OUT_DIR, f'{base}_hough.jpg'), vis_hough)
            
            vis_band = draw_detections(frame, c_band, (0, 0, 255), 'Bandpass')
            cv2.imwrite(os.path.join(OUT_DIR, f'{base}_bandpass.jpg'), vis_band)
            
            vis_adapt = draw_detections(frame, c_adapt, (255, 0, 255), 'Adaptive')
            cv2.imwrite(os.path.join(OUT_DIR, f'{base}_adaptive.jpg'), vis_adapt)
            
            # Also save the masks
            cv2.imwrite(os.path.join(OUT_DIR, f'{base}_mask_morph15.jpg'), mask_morph)
            cv2.imwrite(os.path.join(OUT_DIR, f'{base}_mask_band.jpg'), mask_band)
            cv2.imwrite(os.path.join(OUT_DIR, f'{base}_mask_adapt.jpg'), mask_adapt)
    
    cap.release()

print('\nComparison images saved to:', OUT_DIR)
