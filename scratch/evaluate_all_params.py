import cv2
import numpy as np
import os
import sys
import time

sys.path.insert(0, 'scripts')
from egg_count import detect_egg_centroids, EggTracker

PRUEBA_DIR = r"prueba"
VIDEOS = {
    '2026-08-02_09-00-18.mp4': 48,
    '2026-08-02_09-05-26.mp4': 250,
    '2026-08-02_09-10-26.mp4': 84,
    '2026-08-02_09-15-26.mp4': 3,
    '2026-08-02_09-20-26.mp4': 281,
}

CONFIGS = [
    {
        'name': 'Default (.env current)',
        'max_dist': 45, 'min_track': 3, 'max_lost': 6, 'min_travel': 40, 'peak_win': 19, 'min_peak_dist': 12.0
    },
    {
        'name': 'Higher lost memory (max_lost=15, min_track=4)',
        'max_dist': 50, 'min_track': 4, 'max_lost': 15, 'min_travel': 40, 'peak_win': 19, 'min_peak_dist': 12.0
    },
    {
        'name': 'Higher lost memory + min_travel 50 (max_lost=18, min_track=4)',
        'max_dist': 50, 'min_track': 4, 'max_lost': 18, 'min_travel': 50, 'peak_win': 19, 'min_peak_dist': 12.0
    },
    {
        'name': 'Peak dist 14.0 + max_lost 18 + min_track 5',
        'max_dist': 55, 'min_track': 5, 'max_lost': 18, 'min_travel': 50, 'peak_win': 19, 'min_peak_dist': 14.0
    },
    {
        'name': 'Peak win 21 + dist 14.0 + max_lost 20 + min_track 5',
        'max_dist': 55, 'min_track': 5, 'max_lost': 20, 'min_travel': 50, 'peak_win': 21, 'min_peak_dist': 14.0
    },
]

def run_eval():
    print("=" * 80)
    print("EVALUATING CONFIGURATIONS ACROSS ALL 5 TEST VIDEOS")
    print("=" * 80)

    for cfg in CONFIGS:
        print(f"\n--- Testing Config: {cfg['name']} ---")
        print(f"    params: max_dist={cfg['max_dist']}, min_track={cfg['min_track']}, max_lost={cfg['max_lost']}, min_travel={cfg['min_travel']}, peak_win={cfg['peak_win']}, min_peak_dist={cfg['min_peak_dist']}")

        total_diff_abs = 0
        video_results = []

        for vname, expected in VIDEOS.items():
            vpath = os.path.join(PRUEBA_DIR, vname)
            if not os.path.exists(vpath):
                continue

            cap = cv2.VideoCapture(vpath)
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            tracker = EggTracker(
                line_y=int(h * 0.50),
                max_dist=cfg['max_dist'],
                min_track_frames=cfg['min_track'],
                max_lost_frames=cfg['max_lost'],
                warmup_frames=45,
                direction='up',
                min_travel=cfg['min_travel']
            )

            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_idx += 1
                if frame_idx % 2 != 0:
                    continue

                centroids = detect_egg_centroids(
                    frame,
                    peak_window=cfg['peak_win'],
                    min_peak_dist=cfg['min_peak_dist'],
                    x_margin=25
                )
                tracker.update(centroids)

            cap.release()

            counted = tracker.egg_count
            diff = counted - expected
            pct_diff = (diff / expected * 100) if expected > 0 else 0
            status = 'OK' if abs(pct_diff) <= 20 else '!!'
            video_results.append((vname, expected, counted, diff, pct_diff, status))
            total_diff_abs += abs(diff)

        print(f"  {'Video':<26} | {'Manual':>6} | {'Counted':>7} | {'Diff':>6} | {'Diff %':>7} | {'Status'}")
        print("  " + "-" * 70)
        ok_count = 0
        for r in video_results:
            print(f"  {r[0]:<26} | {r[1]:>6} | {r[2]:>7} | {r[3]:>+6d} | {r[4]:>+6.1f}% | {r[5]}")
            if r[5] == 'OK':
                ok_count += 1
        print(f"  Summary: {ok_count}/5 OK (within +/-20%). Total Abs Error: {total_diff_abs}")

if __name__ == "__main__":
    run_eval()
