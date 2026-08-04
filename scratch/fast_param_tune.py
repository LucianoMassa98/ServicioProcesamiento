import cv2
import numpy as np
import os
import sys

sys.path.insert(0, 'scripts')
from egg_count import detect_egg_centroids, EggTracker

VIDEO_PATH = r"prueba\2026-08-02_09-00-18.mp4"

def fast_tune():
    cap = cv2.VideoCapture(VIDEO_PATH)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    # Pre-extract frame centroids for frames 6800 to 9250 (the active movement region)
    print("Extracting centroids for active region (frames 6800..9250)...")
    cap.set(cv2.CAP_PROP_POS_FRAMES, 6800)

    # Let's test detection parameters on full video segment
    for peak_win, min_peak_dist in [
        (19, 12.0),
        (19, 14.0),
        (19, 16.0),
        (21, 14.0),
        (21, 16.0),
        (25, 14.0),
        (25, 16.0),
    ]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # We will test tracker settings
        for max_lost, min_track, min_travel in [
            (6, 3, 40),
            (12, 3, 40),
            (15, 4, 40),
            (18, 5, 40),
            (18, 5, 60),
            (24, 6, 60),
        ]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            line_y = int(h * 0.50)
            tracker = EggTracker(
                line_y=line_y,
                max_dist=45,
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

            print(f"peak_win={peak_win:2d}, min_peak_dist={min_peak_dist:4.1f}, max_lost={max_lost:2d}, min_track={min_track:2d}, min_travel={min_travel:2d} => EGGS: {tracker.egg_count}")

    cap.release()

if __name__ == "__main__":
    fast_tune()
