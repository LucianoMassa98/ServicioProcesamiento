#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egg_count.py  -  Conteo de huevos marrones en cadena transportadora.

Algoritmo:
  1. Convierte cada frame a HSV y aplica mascara para color naranja-marron.
  2. SIN morphologia de cierre (para no rellenar los huecos entre varillas
     de la cinta, que fusionarian todo en un solo blob masivo).
  3. Usa Distance Transform + supresion de no-maximos para encontrar
     el centro de cada huevo individual.
  4. Rastrea centroides entre frames (nearest-neighbour greedy).
  5. Cuenta cada huevo la primera vez que su centroide cruza
     la linea horizontal de conteo, con requisitos de:
     - Warmup: no contar durante los primeros N frames
     - Distancia minima de viaje: el track debe haberse movido
       al menos M px desde su posicion inicial
     - Frames minimos de track: el track debe haber sido
       rastreado en al menos K frames

Direccion configurable:
  - 'up'   (default): huevos suben (abajo->arriba). Cruza cuando prev_cy > line_y >= cy.
  - 'down':           huevos bajan (arriba->abajo). Cruza cuando prev_cy < line_y <= cy.

Uso:
  python egg_count.py <video_path> [opciones]

Salida (stdout): JSON  { eggs, processedFrames, processingTime }
Errores (stderr): mensajes de diagnostico
"""

import sys
import json
import time
import math
import argparse

import cv2
import numpy as np


# --- Defaults (sobreescribibles por args) ---
DEFAULT_LINE_RATIO       = 0.50   # posicion de la linea como fraccion del alto (centro)
DEFAULT_SKIP_FRAMES      = 1      # procesar todos los frames (sin salteo)
DEFAULT_MAX_DIST         = 30     # distancia maxima px para asociar al mismo track
DEFAULT_MIN_TRACK_FRAMES = 3      # frames minimos rastreados antes de poder contar
DEFAULT_MAX_LOST_FRAMES  = 6      # frames sin deteccion antes de eliminar track
DEFAULT_WARMUP_FRAMES    = 30     # frames iniciales de calentamiento (no se cuenta)
DEFAULT_PEAK_WINDOW      = 13     # ventana para supresion de no-maximos en Distance Transform
DEFAULT_MIN_PEAK_DIST    = 11.5   # umbral minimo de Distance Transform (px a borde)
DEFAULT_X_MARGIN         = 20     # pixeles a recortar de cada lado (excluir maquinaria del borde)
DEFAULT_DIRECTION        = 'up'   # direccion del movimiento de huevos
DEFAULT_MIN_TRAVEL       = 22     # distancia minima (px) que un track debe recorrer desde su posicion inicial


# --- Rango HSV para huevos naranja-marrones ---
HSV_LOWER = np.array([ 5, 80,  60])
HSV_UPPER = np.array([22, 255, 230])

# Kernel pequeno solo para noise removal (sin rellenar huecos entre varillas)
MORPH_KERNEL_SMALL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))


# ---
def parse_args():
    p = argparse.ArgumentParser(description='Cuenta huevos marrones en un video.')
    p.add_argument('video_path',                                     help='Ruta al video')
    p.add_argument('--line-ratio',       type=float, default=DEFAULT_LINE_RATIO)
    p.add_argument('--skip-frames',      type=int,   default=DEFAULT_SKIP_FRAMES)
    p.add_argument('--max-dist',         type=float, default=DEFAULT_MAX_DIST)
    p.add_argument('--min-track-frames', type=int,   default=DEFAULT_MIN_TRACK_FRAMES)
    p.add_argument('--max-lost-frames',  type=int,   default=DEFAULT_MAX_LOST_FRAMES)
    p.add_argument('--warmup-frames',    type=int,   default=DEFAULT_WARMUP_FRAMES)
    p.add_argument('--peak-window',      type=int,   default=DEFAULT_PEAK_WINDOW,
                   help='Tamano de ventana de supresion de no-maximos (Distance Transform)')
    p.add_argument('--min-peak-dist',    type=float, default=DEFAULT_MIN_PEAK_DIST,
                   help='Umbral minimo de Distance Transform para detectar centroides')
    p.add_argument('--x-margin',         type=int,   default=DEFAULT_X_MARGIN,
                   help='Pixeles a recortar de cada lado del frame')
    p.add_argument('--direction',        type=str,   default=DEFAULT_DIRECTION,
                   choices=['up', 'down'],
                   help='Direccion del movimiento: up (abajo->arriba) o down (arriba->abajo)')
    p.add_argument('--min-travel',       type=int,   default=DEFAULT_MIN_TRAVEL,
                   help='Distancia minima (px) de viaje antes de contar un track')
    return p.parse_args()


# ---
def detect_egg_centroids(frame: np.ndarray,
                         peak_window: int = DEFAULT_PEAK_WINDOW,
                         min_peak_dist: float = DEFAULT_MIN_PEAK_DIST,
                         x_margin: int = DEFAULT_X_MARGIN) -> list:
    """
    Detecta centroides de huevos usando Distance Transform + Supresion de No-Maximos.

    Clave: NO se aplica MORPH_CLOSE para no rellenar los huecos entre las varillas
    de la cinta transportadora. Sin closing, las varillas quedan como franjas separadas
    en la mascara, y solo los huevos (que cubren multiples varillas) crean blobs anchos
    con valores altos de Distance Transform.
    """
    h, w = frame.shape[:2]

    # Recortar bordes laterales (maquinaria/engranajes del borde de la cinta)
    x_start = min(x_margin, w // 4)
    x_end = max(w - x_margin, w * 3 // 4)
    roi = frame[:, x_start:x_end]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask_roi = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)

    # Solo open pequeno para eliminar ruido puntual, SIN close
    mask_roi = cv2.morphologyEx(mask_roi, cv2.MORPH_OPEN, MORPH_KERNEL_SMALL, iterations=1)

    # Transformada de distancia
    dist = cv2.distanceTransform(mask_roi, cv2.DIST_L2, 5)
    dist_smooth = cv2.GaussianBlur(dist, (7, 7), 0)

    # Supresion de no-maximos locales
    kernel = np.ones((peak_window, peak_window), np.uint8)
    local_max = cv2.dilate(dist_smooth, kernel)

    # Los picos locales son los maximos dentro de la ventana que superan el umbral
    peaks_mask = (dist_smooth == local_max) & (dist_smooth >= min_peak_dist)
    ys, xs = np.where(peaks_mask)

    # Ajustar coordenadas x de vuelta al frame completo
    return [(int(x + x_start), int(y)) for x, y in zip(xs, ys)]


# ---
class EggTracker:
    """
    Rastrea huevos entre frames usando nearest-neighbour greedy matching
    y cuenta cada huevo cuando su centroide cruza la linea horizontal de conteo.

    Requisitos para contar:
    - El tracker debe haber pasado el periodo de warmup
    - El track debe tener al menos min_track_frames detecciones
    - El track debe haber viajado al menos min_travel px desde su posicion inicial
    - El centroide debe cruzar la linea en la direccion correcta
    """

    def __init__(self, line_y: int, max_dist: float,
                 min_track_frames: int, max_lost_frames: int,
                 warmup_frames: int = DEFAULT_WARMUP_FRAMES,
                 direction: str = DEFAULT_DIRECTION,
                 min_travel: int = DEFAULT_MIN_TRAVEL):
        self.line_y           = line_y
        self.max_dist         = max_dist
        self.min_track_frames = min_track_frames
        self.max_lost_frames  = max_lost_frames
        self.warmup_frames    = warmup_frames
        self.direction        = direction
        self.min_travel       = min_travel
        self.tracks: dict     = {}   # id -> {cx, cy, init_cx, init_cy, frames, counted, lost}
        self._next_id: int    = 0
        self.egg_count: int   = 0
        self._frame_count: int = 0   # contador interno de frames procesados

    def update(self, centroids: list) -> None:
        self._frame_count += 1
        in_warmup = self._frame_count <= self.warmup_frames

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

            # No contar durante warmup
            if in_warmup:
                continue

            # Calcular distancia de viaje desde posicion inicial
            travel = math.hypot(
                cx - self.tracks[tid]['init_cx'],
                cy - self.tracks[tid]['init_cy']
            )

            # Determinar cruce de linea segun direccion configurada
            if self.direction == 'up':
                crossed = prev_cy > self.line_y >= cy
            else:
                crossed = prev_cy < self.line_y <= cy

            if (not self.tracks[tid]['counted']
                    and self.tracks[tid]['frames'] >= self.min_track_frames
                    and travel >= self.min_travel
                    and crossed):
                self.tracks[tid]['counted'] = True
                self.egg_count += 1

        for tid in list(self.tracks):
            if tid not in used_tracks:
                self.tracks[tid]['lost'] += 1

        for cidx, (cx, cy) in enumerate(centroids):
            if cidx not in used_centroids:
                self.tracks[self._next_id] = {
                    'cx': cx, 'cy': cy,
                    'init_cx': cx, 'init_cy': cy,
                    'frames': 1,
                    'counted': False,
                    'lost': 0,
                }
                self._next_id += 1

        self.tracks = {
            tid: t for tid, t in self.tracks.items()
            if t['lost'] <= self.max_lost_frames
        }


# ---
def main():
    args       = parse_args()
    start_time = time.time()

    cap = cv2.VideoCapture(args.video_path)
    if not cap.isOpened():
        print(json.dumps({'error': f'No se pudo abrir el video: {args.video_path}'}),
              file=sys.stdout)
        sys.exit(1)

    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    line_y = int(height * args.line_ratio)

    print(f'[egg_count] {width}x{height}  line_y={line_y}px  dir={args.direction}'
          f'  x_margin={args.x_margin}  min_travel={args.min_travel}'
          f'  video={args.video_path}',
          file=sys.stderr)

    tracker = EggTracker(
        line_y           = line_y,
        max_dist         = args.max_dist,
        min_track_frames = args.min_track_frames,
        max_lost_frames  = args.max_lost_frames,
        warmup_frames    = args.warmup_frames,
        direction        = args.direction,
        min_travel       = args.min_travel,
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
            peak_window=args.peak_window,
            min_peak_dist=args.min_peak_dist,
            x_margin=args.x_margin,
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
