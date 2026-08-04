import cv2
import numpy as np
import os
import sys

sys.path.insert(0, 'scripts')
from egg_count import detect_egg_centroids, EggTracker

VIDEO_PATH = r"prueba\2026-08-02_09-00-18.mp4"

def test_params():
    cap = cv2.VideoCapture(VIDEO_PATH)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Let's test various combinations of parameters on video 1 (manual count = 48)
    param_grid = [
        # max_lost, min_track, max_dist, min_travel, peak_window, min_peak_dist
        (6,  3, 45, 40, 19, 12.0), # DEFAULT (returns 124)
        (12, 3, 45, 40, 19, 12.0),
        (18, 3, 45, 40, 19, 12.0),
        (24, 3, 45, 40, 19, 12.0),
        (18, 5, 45, 40, 19, 12.0),
        (18, 5, 50, 40, 19, 12.0),
        (18, 5, 45, 60, 19, 12.0),
        (18, 5, 45, 40, 21, 12.0),
        (18, 5, 45, 40, 23, 13.0),
        (18, 5, 45, 40, 25, 14.0),
        (18, 5, 45, 40, 25, 15.0),
    ]

    print(f"{'max_lost':>8} {'min_tr':>6} {'max_dst':>7} {'min_trv':>7} {'pk_win':>6} {'pk_dist':>7} | {'Eggs':>6}")
    print("-" * 65)

    for max_lost, min_track, max_dist, min_travel, peak_win, min_peak_dist in param_grid:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        line_y = int(h * 0.50)
        tracker = EggTracker(
            line_y=line_y,
            max_dist=max_dist,
            min_track_frames=min_track,
            max_lost_frames=max_lost,
            warmup_frames=45,
            direction='up',
            min_travel=min_travel
        )

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            if frame_idx % 2 != 0:
                continue

            centroids = detect_egg_centroids(frame, peak_window=peak_win, min_peak_dist=min_peak_dist, x_margin=25)
            tracker.update(centroids)

        print(f"{max_lost:>8} {min_track:>6} {max_dist:>7} {min_travel:>7} {peak_win:>6} {min_peak_dist:>7.1f} | {tracker.egg_count:>6}")

    cap.release()

if __name__ == "__main__":
    test_params()
