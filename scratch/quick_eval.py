import cv2
import sys
import os

sys.path.insert(0, 'scripts')
from egg_count import detect_egg_centroids, EggTracker

PRUEBA_DIR = r"prueba"

def test_combo(max_lost, min_track, max_dist, min_travel, peak_win, min_peak_dist):
    videos = [
        ('2026-08-02_09-00-18.mp4', 48),
        ('2026-08-02_09-05-26.mp4', 250),
        ('2026-08-02_09-10-26.mp4', 84),
        ('2026-08-02_09-15-26.mp4', 3),
        ('2026-08-02_09-20-26.mp4', 281),
    ]

    print(f"\n--- Testing: max_lost={max_lost}, min_track={min_track}, max_dist={max_dist}, min_travel={min_travel}, peak_win={peak_win}, min_peak_dist={min_peak_dist} ---")
    for vname, expected in videos:
        vpath = os.path.join(PRUEBA_DIR, vname)
        cap = cv2.VideoCapture(vpath)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        tracker = EggTracker(
            line_y=int(h * 0.50),
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
        cap.release()
        diff = tracker.egg_count - expected
        pct = (diff / expected * 100) if expected > 0 else 0
        print(f"  {vname:<25}: Manual {expected:>3} | Counted {tracker.egg_count:>3} | Diff {diff:>+4d} ({pct:>+5.1f}%)")

if __name__ == "__main__":
    # Test a few strong candidate settings
    test_combo(max_lost=15, min_track=4, max_dist=50, min_travel=45, peak_win=19, min_peak_dist=12.0)
    test_combo(max_lost=18, min_track=4, max_dist=50, min_travel=50, peak_win=19, min_peak_dist=13.0)
    test_combo(max_lost=20, min_track=5, max_dist=55, min_travel=50, peak_win=19, min_peak_dist=13.0)
