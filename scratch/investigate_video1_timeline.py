import cv2
import numpy as np
import os
import sys

sys.path.insert(0, 'scripts')
from egg_count import detect_egg_centroids, EggTracker

VIDEO_PATH = r"prueba\2026-08-02_09-00-18.mp4"

def inspect():
    cap = cv2.VideoCapture(VIDEO_PATH)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    print(f"Video {VIDEO_PATH}: {total_frames} frames, {fps} fps")

    # Sample every 300 frames (10 seconds)
    print(f"{'Frame':>7} | {'Time':>7} | {'Centroids':>9} | {'Mean Y':>7} | {'Min Y':>6} | {'Max Y':>6}")
    print("-" * 55)

    for f in range(1, total_frames, 300):
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ret, frame = cap.read()
        if not ret:
            continue

        centroids = detect_egg_centroids(frame, peak_window=19, min_peak_dist=12.0, x_margin=25)
        if centroids:
            ys = [c[1] for c in centroids]
            mean_y = sum(ys) / len(ys)
            min_y = min(ys)
            max_y = max(ys)
        else:
            mean_y, min_y, max_y = 0, 0, 0

        time_sec = f / fps
        print(f"{f:>7} | {time_sec:>6.1f}s | {len(centroids):>9} | {mean_y:>7.1f} | {min_y:>6} | {max_y:>6}")

    cap.release()

if __name__ == "__main__":
    inspect()
