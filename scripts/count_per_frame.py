#!/usr/bin/env python3
"""
count_per_frame.py - Muestra cuantos centroides detecta el nuevo algoritmo
por frame en distintos momentos, para saber si el problema es deteccion o tracking.
"""
import sys
import cv2

sys.path.insert(0, 'scripts')
from egg_count import detect_egg_centroids, DEFAULT_MIN_AREA, DEFAULT_MAX_AREA, APPROX_EGG_RADIUS_PX

VIDEO_PATH = r"prueba\prueba-mejorada.mp4"
SAMPLE_FRAMES = [200, 500, 900, 1200, 1500, 2000, 3000, 4500, 6000, 7500, 9000]

def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    print(f"APPROX_EGG_RADIUS_PX = {APPROX_EGG_RADIUS_PX}")
    print(f"{'Frame':>7}  {'Tiempo':>8}  {'Centroides':>12}")
    print("-" * 35)
    for f in SAMPLE_FRAMES:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ret, frame = cap.read()
        if not ret:
            continue
        centroids = detect_egg_centroids(frame, DEFAULT_MIN_AREA, DEFAULT_MAX_AREA)
        seg = f / 30.0
        mins = int(seg // 60)
        segs = seg % 60
        print(f"{f:>7}  {mins}:{segs:05.2f}  {len(centroids):>12}  {centroids[:5]}")
    cap.release()

if __name__ == '__main__':
    main()
