#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egg_count.py  –  Conteo de huevos marrones en cadena transportadora.

Algoritmo:
  1. Convierte cada frame a HSV y aplica máscara para color naranja-marrón sobre el ROI de la cadena.
  2. Usa Distance Transform + supresión de no-máximos para encontrar
     el centro de cada huevo individual, incluso dentro de clusters contiguos.
  3. Rastrea centroides entre frames (nearest-neighbour greedy).
  4. Cuenta cada huevo la primera vez que su centroide cruza
     la línea horizontal de conteo (movimiento de arriba→abajo).

Orientación de cámara: LATERAL (vista desde el costado, cadena inclinada).
  - La cadena traversa el frame de arriba a abajo con inclinación.
  - Los huevos se desplazan de la parte superior hacia la inferior.

Uso:
  python egg_count.py <video_path> [opciones]

Salida (stdout): JSON  { eggs, processedFrames, processingTime }
Errores (stderr): mensajes de diagnóstico
"""

import sys
import json
import time
import math
import argparse

import cv2
import numpy as np


# ─── Defaults (sobreescribibles por args) ─────────────────────────────────────
DEFAULT_LINE_RATIO       = 0.50   # posición de la línea como fracción del alto (a la altura de los plásticos blancos a la mitad)
DEFAULT_MIN_AREA         = 150    # reservado para filtros secundarios
DEFAULT_MAX_AREA         = 12000  # reservado para filtros secundarios
DEFAULT_SKIP_FRAMES      = 2      # procesar 1 de cada N frames
DEFAULT_MAX_DIST         = 45     # distancia máxima px para asociar al mismo track
DEFAULT_MIN_TRACK_FRAMES = 1      # frames mínimos rastreados antes de poder contar
DEFAULT_MAX_LOST_FRAMES  = 6      # frames sin detección antes de eliminar track
DEFAULT_ROI_WIDTH_RATIO  = 0.78   # fracción del ancho a procesar (excluye engranajes a la izquierda y riel metálico lateral a la derecha)
DEFAULT_WARMUP_FRAMES    = 60     # frames iniciales de calentamiento
DEFAULT_PEAK_WINDOW      = 19     # ventana para supresión de no-máximos en Distance Transform
DEFAULT_MIN_PEAK_DIST    = 9.5    # umbral mínimo de Distance Transform (px a borde)


# ─── Rango HSV para huevos naranja-marrones sobre fondo blanco ────────────────
HSV_LOWER = np.array([ 5, 60,  40])
HSV_UPPER = np.array([25, 255, 240])

ROI_WIDTH_RATIO = float(DEFAULT_ROI_WIDTH_RATIO)
MORPH_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
CLAHE = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))


# ──────────────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description='Cuenta huevos marrones en un video.')
    p.add_argument('video_path',                                     help='Ruta al video')
    p.add_argument('--line-ratio',       type=float, default=DEFAULT_LINE_RATIO)
    p.add_argument('--min-area',         type=int,   default=DEFAULT_MIN_AREA)
    p.add_argument('--max-area',         type=int,   default=DEFAULT_MAX_AREA)
    p.add_argument('--skip-frames',      type=int,   default=DEFAULT_SKIP_FRAMES)
    p.add_argument('--max-dist',         type=float, default=DEFAULT_MAX_DIST)
    p.add_argument('--min-track-frames', type=int,   default=DEFAULT_MIN_TRACK_FRAMES)
    p.add_argument('--max-lost-frames',  type=int,   default=DEFAULT_MAX_LOST_FRAMES)
    p.add_argument('--warmup-frames',    type=int,   default=DEFAULT_WARMUP_FRAMES)
    p.add_argument('--peak-window',      type=int,   default=DEFAULT_PEAK_WINDOW,
                   help='Tamaño de ventana de supresión de no-máximos (Distance Transform)')
    p.add_argument('--min-peak-dist',    type=float, default=DEFAULT_MIN_PEAK_DIST,
                   help='Umbral mínimo de Distance Transform para detectar centroides')
    p.add_argument('--roi-ratio',        type=float, default=DEFAULT_ROI_WIDTH_RATIO,
                   help='Fracción del ancho del frame a analizar (0.0-1.0)')
    return p.parse_args()


# ──────────────────────────────────────────────────────────────────────────────
def detect_egg_centroids(frame: np.ndarray,
                         roi_ratio: float = ROI_WIDTH_RATIO,
                         peak_window: int = DEFAULT_PEAK_WINDOW,
                         min_peak_dist: float = DEFAULT_MIN_PEAK_DIST) -> list:
    """
    Detecta centroides de huevos usando Distance Transform + Supresión de No-Máximos sobre el ROI de la cinta.
    Aplica CLAHE al canal V para garantizar robustez ante variaciones de iluminación a distintas horas del día.
    Excluye bordes laterales (engranajes a la izquierda y rieles metálicos a la derecha).
    """
    h, w = frame.shape[:2]
    x1 = int(w * 0.08)
    x2 = int(w * roi_ratio)
    roi = frame[:, x1:x2]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # Normalización adaptativa de brillo para manejar distintos niveles de iluminación durante el día
    hsv[:, :, 2] = CLAHE.apply(hsv[:, :, 2])

    mask_roi = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)

    mask_roi = cv2.morphologyEx(mask_roi, cv2.MORPH_CLOSE, MORPH_KERNEL, iterations=2)
    mask_roi = cv2.morphologyEx(mask_roi, cv2.MORPH_OPEN,  MORPH_KERNEL, iterations=1)

    # Transformada de distancia sobre la máscara recortada del ROI
    dist = cv2.distanceTransform(mask_roi, cv2.DIST_L2, 5)
    dist_smooth = cv2.GaussianBlur(dist, (7, 7), 0)

    # Supresión de no-máximos locales usando dilatación con kernel de tamaño peak_window
    kernel = np.ones((peak_window, peak_window), np.uint8)
    local_max = cv2.dilate(dist_smooth, kernel)

    # Los picos locales son los máximos dentro de la ventana que superan el umbral de distancia
    peaks_mask = (dist_smooth == local_max) & (dist_smooth >= min_peak_dist)
    ys, xs = np.where(peaks_mask)
    return [(x + x1, y) for x, y in zip(xs, ys)]


# ──────────────────────────────────────────────────────────────────────────────
class EggTracker:
    """
    Rastrea huevos entre frames usando nearest-neighbour greedy matching
    y cuenta cada huevo cuando su centroide cruza la línea horizontal de conteo (movimiento abajo -> arriba).
    """

    def __init__(self, line_y: int, max_dist: float,
                 min_track_frames: int, max_lost_frames: int,
                 warmup_frames: int = DEFAULT_WARMUP_FRAMES):
        self.line_y           = line_y
        self.max_dist         = max_dist
        self.min_track_frames = min_track_frames
        self.max_lost_frames  = max_lost_frames
        self.warmup_frames    = warmup_frames
        self.tracks: dict     = {}   # id → {cx, cy, frames, counted, lost}
        self._next_id: int    = 0
        self.egg_count: int   = 0

    def update(self, centroids: list) -> None:
        used_tracks    = set()
        used_centroids = set()

        candidates = []
        for tid, track in self.tracks.items():
            for cidx, (cx, cy) in enumerate(centroids):
                dist = math.hypot(cx - track['cx'], cy - track['cy'])
                if dist <= self.max_dist:
                    candidates.append((dist, tid, cidx))
        candidates.sort()

        for dist, tid, cidx in candidates:
            if tid in used_tracks or cidx in used_centroids:
                continue
            used_tracks.add(tid)
            used_centroids.add(cidx)

            cx, cy   = centroids[cidx]
            prev_cy  = self.tracks[tid]['cy']

            self.tracks[tid]['cx']     = cx
            self.tracks[tid]['cy']     = cy
            self.tracks[tid]['frames'] += 1
            self.tracks[tid]['lost']   = 0

            # Dirección de abajo hacia arriba: prev_cy >= line_y > cy
            if (not self.tracks[tid]['counted']
                    and self.tracks[tid]['frames'] >= self.min_track_frames
                    and prev_cy >= self.line_y > cy):
                self.tracks[tid]['counted'] = True
                self.egg_count += 1

        for tid in list(self.tracks):
            if tid not in used_tracks:
                self.tracks[tid]['lost'] += 1

        for cidx, (cx, cy) in enumerate(centroids):
            if cidx not in used_centroids:
                self.tracks[self._next_id] = {
                    'cx': cx, 'cy': cy,
                    'frames': 1,
                    'counted': False,
                    'lost': 0,
                }
                self._next_id += 1

        self.tracks = {
            tid: t for tid, t in self.tracks.items()
            if t['lost'] <= self.max_lost_frames
        }


# ──────────────────────────────────────────────────────────────────────────────
def main():
    args       = parse_args()
    start_time = time.time()

    cap = cv2.VideoCapture(args.video_path)
    if not cap.isOpened():
        print(json.dumps({'error': f'No se pudo abrir el video: {args.video_path}'}),
              file=sys.stdout)
        sys.exit(1)

    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    line_y = int(height * args.line_ratio)

    print(f'[egg_count] line_y={line_y}px  roi={args.roi_ratio:.2f}  video={args.video_path}',
          file=sys.stderr)

    tracker = EggTracker(
        line_y           = line_y,
        max_dist         = args.max_dist,
        min_track_frames = args.min_track_frames,
        max_lost_frames  = args.max_lost_frames,
        warmup_frames    = args.warmup_frames,
    )

    frame_idx  = 0
    processed  = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % args.skip_frames != 0:
            continue

        centroids = detect_egg_centroids(
            frame,
            roi_ratio=args.roi_ratio,
            peak_window=args.peak_window,
            min_peak_dist=args.min_peak_dist,
        )
        tracker.update(centroids)
        processed += 1

    cap.release()

    elapsed = round(time.time() - start_time, 2)
    result  = {
        'eggs':           tracker.egg_count,
        'processedFrames': processed,
        'processingTime':  elapsed,
    }
    print(json.dumps(result))


if __name__ == '__main__':
    main()
