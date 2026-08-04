import cv2
import numpy as np
import os
import sys

sys.path.insert(0, 'scripts')
from egg_count import detect_egg_centroids, EggTracker

VIDEO_PATH = r"prueba\2026-08-02_09-00-18.mp4"

def debug_tracks():
    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    line_y = int(h * 0.50)

    tracker = EggTracker(
        line_y=line_y,
        max_dist=45,
        min_track_frames=3,
        max_lost_frames=6,
        warmup_frames=45,
        direction='up',
        min_travel=40
    )

    counts_log = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        if frame_idx % 2 != 0:
            continue

        centroids = detect_egg_centroids(frame, peak_window=19, min_peak_dist=12.0, x_margin=25)
        prev_count = tracker.egg_count
        tracker.update(centroids)

        if tracker.egg_count > prev_count:
            # New count(s)!
            for tid, t in tracker.tracks.items():
                if t['counted'] and not any(c['tid'] == tid for c in counts_log):
                    counts_log.append({
                        'count': len(counts_log) + 1,
                        'frame': frame_idx,
                        'time': frame_idx / fps,
                        'tid': tid,
                        'cx': t['cx'],
                        'cy': t['cy'],
                        'init_cx': t['init_cx'],
                        'init_cy': t['init_cy'],
                        'frames': t['frames']
                    })

    cap.release()

    print(f"Total counted: {len(counts_log)}")

    # Group counts by timestamp / time window (e.g. 5-second bins)
    print("\nCount distribution over time (5-second bins):")
    time_bins = {}
    for c in counts_log:
        t_bin = int(c['time'] // 5) * 5
        time_bins[t_bin] = time_bins.get(t_bin, 0) + 1

    for t_bin in sorted(time_bins.keys()):
        print(f"Time {t_bin:3d}s - {t_bin+5:3d}s: {time_bins[t_bin]:2d} eggs counted")

    # Inspect x-coordinates of counts (are multiple eggs counted at same x at same time, or same x across time?)
    print("\nSample of counting events (frames 6800 to 9250):")
    for c in counts_log:
        print(f"#{c['count']:3d} | Frame {c['frame']:5d} ({c['time']:5.1f}s) | Track {c['tid']:4d} | pos=({c['cx']:3d}, {c['cy']:3d}) | init=({c['init_cx']:3d}, {c['init_cy']:3d}) | tracked {c['frames']} frames")

if __name__ == "__main__":
    debug_tracks()
