import cv2
import numpy as np
import os
import sys

sys.path.insert(0, 'scripts')
from egg_count import detect_egg_centroids, EggTracker

VIDEO_PATH = r"prueba\2026-08-02_09-00-18.mp4"
OUT_DIR = r"prueba\diag\video1_frames"
os.makedirs(OUT_DIR, exist_ok=True)

def visualize_video1():
    cap = cv2.VideoCapture(VIDEO_PATH)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fps = cap.get(cv2.CAP_PROP_FPS)

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

    frame_idx = 0
    save_frames = [6850, 6900, 7000, 7100, 7200, 7500, 7800, 8100, 8400, 8700]

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        if frame_idx % 2 != 0:
            continue

        centroids = detect_egg_centroids(frame, peak_window=19, min_peak_dist=12.0, x_margin=25)
        tracker.update(centroids)

        if frame_idx in save_frames or (frame_idx > 6850 and frame_idx < 6950 and frame_idx % 10 == 0):
            vis = frame.copy()
            # Draw line_y
            cv2.line(vis, (0, line_y), (w, line_y), (255, 180, 0), 2)
            cv2.putText(vis, f"Count: {tracker.egg_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(vis, f"Frame: {frame_idx}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            # Draw centroids
            for cx, cy in centroids:
                cv2.circle(vis, (cx, cy), 5, (0, 0, 255), -1)

            # Draw active tracks
            for tid, t in tracker.tracks.items():
                if t['lost'] == 0:
                    color = (0, 255, 255) if not t['counted'] else (0, 128, 255)
                    cv2.circle(vis, (t['cx'], t['cy']), 8, color, 2)
                    cv2.putText(vis, f"#{tid}", (t['cx']+5, t['cy']-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

            out_path = os.path.join(OUT_DIR, f"frame_{frame_idx:05d}_count_{tracker.egg_count}.jpg")
            cv2.imwrite(out_path, vis)

    cap.release()
    print(f"Saved visualization frames to {OUT_DIR}")
    print(f"Final Count on video 1: {tracker.egg_count}")

if __name__ == "__main__":
    visualize_video1()
