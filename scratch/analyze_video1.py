import os
import sys
import cv2
import numpy as np
import math

sys.path.insert(0, 'scripts')
from egg_count import detect_egg_centroids, EggTracker

VIDEO_PATH = r"prueba\2026-08-02_09-00-18.mp4"

def analyze():
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("Cannot open video")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    print(f"Video {VIDEO_PATH}: {w}x{h}, {fps} fps, {total_frames} frames")

    # Let's run tracker and log all counting events (frame, track_id, init_pos, current_pos, travel distance, etc.)
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

    events = []
    track_history = {} # tid -> list of (frame_idx, cx, cy)
    centroid_counts = []

    frame_idx = 0
    processed = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % 2 != 0:
            continue

        processed += 1
        centroids = detect_egg_centroids(frame, peak_window=19, min_peak_dist=12.0, x_margin=25)
        centroid_counts.append((frame_idx, len(centroids)))

        prev_count = tracker.egg_count
        tracker.update(centroids)

        # Record active track positions
        for tid, t in tracker.tracks.items():
            if tid not in track_history:
                track_history[tid] = []
            track_history[tid].append((frame_idx, t['cx'], t['cy']))

        if tracker.egg_count > prev_count:
            # A new egg was counted! Find which track got counted
            for tid, t in tracker.tracks.items():
                if t['counted'] and (len(events) == 0 or events[-1]['tid'] != tid):
                    # Check if this tid is already in events
                    if not any(e['tid'] == tid for e in events):
                        events.append({
                            'event_no': tracker.egg_count,
                            'frame': frame_idx,
                            'tid': tid,
                            'init': (t['init_cx'], t['init_cy']),
                            'curr': (t['cx'], t['cy']),
                            'frames': t['frames']
                        })

    cap.release()

    print(f"\nTotal counted eggs: {tracker.egg_count}")
    print(f"Total unique tracks created: {tracker._next_id}")
    print(f"Total count events recorded: {len(events)}")

    # Print first 20 count events and last 20 count events
    print("\n--- First 15 count events ---")
    for e in events[:15]:
        print(f"Count #{e['event_no']}: Frame {e['frame']} (time {e['frame']/fps:.1f}s), Track {e['tid']}, Init {e['init']} -> Curr {e['curr']}, tracked {e['frames']} frames")

    print("\n--- Summary of motion direction for tracks ---")
    # Check y velocity of tracks: cy_end - cy_start
    dy_list = []
    for tid, pts in track_history.items():
        if len(pts) >= 5:
            dy = pts[-1][2] - pts[0][2] # positive means moving DOWN, negative means moving UP
            dy_list.append(dy)

    if dy_list:
        moving_up = sum(1 for dy in dy_list if dy < -10)
        moving_down = sum(1 for dy in dy_list if dy > 10)
        stationary = sum(1 for dy in dy_list if abs(dy) <= 10)
        print(f"Tracks >= 5 frames: Total={len(dy_list)}, Moving UP (dy< -10)={moving_up}, Moving DOWN (dy>10)={moving_down}, Stationary={stationary}")

    # Check average centroids per frame across video timeline in chunks
    print("\n--- Average centroids per frame by timeline slice ---")
    chunk_size = len(centroid_counts) // 5
    for i in range(5):
        chunk = centroid_counts[i*chunk_size : (i+1)*chunk_size]
        avg_c = sum(c[1] for c in chunk) / len(chunk) if chunk else 0
        min_f = chunk[0][0] if chunk else 0
        max_f = chunk[-1][0] if chunk else 0
        print(f"Frames {min_f}..{max_f} (time {min_f/fps:.0f}s..{max_f/fps:.0f}s): avg {avg_c:.2f} centroids/frame")

if __name__ == "__main__":
    analyze()
