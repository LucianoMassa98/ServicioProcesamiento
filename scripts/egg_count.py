#!/usr/bin/env python3
"""
egg_count.py  –  Conteo de huevos marrones en cinta transportadora.

Algoritmo:
  1. Convierte cada frame a HSV y aplica máscara para color marrón.
  2. Separa blobs tocados mediante Distance Transform + Watershed.
  3. Filtra detecciones por área y circularidad.
  4. Rastrea centroides entre frames (nearest-neighbour greedy).
  5. Cuenta cada huevo la primera vez que su centroide cruza
     la línea horizontal de conteo (movimiento de arriba→abajo).

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
DEFAULT_LINE_RATIO      = 0.65   # posición de la línea como fracción del alto
DEFAULT_MIN_AREA        = 600    # área mínima de un huevo (px²)
DEFAULT_MAX_AREA        = 18000  # área máxima de un huevo (px²)
DEFAULT_SKIP_FRAMES     = 2      # procesar 1 de cada N frames
DEFAULT_MAX_DIST        = 90     # distancia máxima px para asociar al mismo track
DEFAULT_MIN_TRACK_FRAMES = 4     # frames mínimos rastreados antes de poder contar
DEFAULT_MAX_LOST_FRAMES  = 10    # frames sin detección antes de eliminar track


# ─── Rango HSV para huevos marrones ───────────────────────────────────────────
# Huevos marrones típicos: matiz 5-25°, saturación media-alta, valor medio-alto.
# Ajustar si el tono varía con la iluminación.
HSV_LOWER = np.array([5,  40,  60])
HSV_UPPER = np.array([25, 255, 220])

# Kernel morfológico elíptico para operaciones de limpieza
MORPH_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))


# ──────────────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description='Cuenta huevos marrones en un video.')
    p.add_argument('video_path',                                    help='Ruta al video')
    p.add_argument('--line-ratio',       type=float, default=DEFAULT_LINE_RATIO)
    p.add_argument('--min-area',         type=int,   default=DEFAULT_MIN_AREA)
    p.add_argument('--max-area',         type=int,   default=DEFAULT_MAX_AREA)
    p.add_argument('--skip-frames',      type=int,   default=DEFAULT_SKIP_FRAMES)
    p.add_argument('--max-dist',         type=float, default=DEFAULT_MAX_DIST)
    p.add_argument('--min-track-frames', type=int,   default=DEFAULT_MIN_TRACK_FRAMES)
    p.add_argument('--max-lost-frames',  type=int,   default=DEFAULT_MAX_LOST_FRAMES)
    return p.parse_args()


# ──────────────────────────────────────────────────────────────────────────────
def build_egg_mask(frame: np.ndarray) -> np.ndarray:
    """
    Genera una máscara binaria de los píxeles con color de huevo marrón.
    Aplica cierre morfológico para rellenar huecos y apertura para quitar ruido.
    """
    hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)

    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, MORPH_KERNEL, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  MORPH_KERNEL, iterations=1)
    return mask


# ──────────────────────────────────────────────────────────────────────────────
def separate_blobs_watershed(frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Aplica Distance Transform + Watershed sobre la máscara para separar
    huevos que se tocan en el marcador binario.

    Retorna una imagen de marcadores etiquetados (np.int32).
    """
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)

    # "Seguro primer plano": píxeles con distancia alta al borde → núcleo del huevo
    _, sure_fg = cv2.threshold(dist, 0.38 * dist.max(), 255, 0)
    sure_fg    = np.uint8(sure_fg)

    # "Seguro fondo": dilatación de la máscara original
    sure_bg = cv2.dilate(mask, MORPH_KERNEL, iterations=2)

    # Zona desconocida: entre ambas regiones
    unknown = cv2.subtract(sure_bg, sure_fg)

    # Etiquetar componentes del primer plano como marcadores para watershed
    _, markers = cv2.connectedComponents(sure_fg)
    markers    = markers + 1           # reservar etiqueta 1 para fondo
    markers[unknown == 255] = 0        # zona desconocida → 0 (watershed la resolverá)

    markers = cv2.watershed(frame, markers)
    return markers


# ──────────────────────────────────────────────────────────────────────────────
def detect_egg_centroids(frame: np.ndarray, min_area: int, max_area: int) -> list:
    """
    Detecta huevos en un frame y devuelve una lista de centroides (cx, cy).

    Pipeline:
      1. Máscara de color marrón.
      2. Watershed para separar grupos de huevos.
      3. Por cada región etiquetada: filtrar por área y circularidad.
    """
    mask    = build_egg_mask(frame)
    markers = separate_blobs_watershed(frame, mask)

    centroids = []
    for label in np.unique(markers):
        if label <= 1:       # 1 = fondo, -1 = borde watershed
            continue

        component = np.zeros(mask.shape, dtype=np.uint8)
        component[markers == label] = 255

        area = cv2.countNonZero(component)
        if not (min_area <= area <= max_area):
            continue

        # Circularidad: 4π·A / P²  (1.0 = círculo perfecto)
        contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        perimeter = cv2.arcLength(contours[0], True)
        if perimeter == 0:
            continue
        circularity = 4 * math.pi * area / (perimeter ** 2)
        if not (0.35 <= circularity <= 1.4):
            continue

        M  = cv2.moments(component)
        if M['m00'] == 0:
            continue
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        centroids.append((cx, cy))

    return centroids


# ──────────────────────────────────────────────────────────────────────────────
class EggTracker:
    """
    Rastrea huevos entre frames usando nearest-neighbour greedy matching
    y cuenta cada uno cuando su centroide cruza la línea horizontal.

    Un huevo se cuenta solo si:
      - fue rastreado durante al menos `min_track_frames` frames (evita falsos positivos)
      - su centroide pasa de arriba de la línea a abajo (movimiento top→bottom)
      - aún no fue contado en este recorrido
    """

    def __init__(self, line_y: int, max_dist: float,
                 min_track_frames: int, max_lost_frames: int):
        self.line_y           = line_y
        self.max_dist         = max_dist
        self.min_track_frames = min_track_frames
        self.max_lost_frames  = max_lost_frames
        self.tracks: dict     = {}   # id → {cx, cy, frames, counted, lost}
        self._next_id: int    = 0
        self.egg_count: int   = 0

    # ── Asociar centroides a tracks existentes ────────────────────────────────
    def update(self, centroids: list) -> None:
        used_tracks    = set()
        used_centroids = set()

        # Calcular todas las distancias posibles y ordenar de menor a mayor
        candidates = []
        for tid, track in self.tracks.items():
            for cidx, (cx, cy) in enumerate(centroids):
                dist = math.hypot(cx - track['cx'], cy - track['cy'])
                if dist <= self.max_dist:
                    candidates.append((dist, tid, cidx))
        candidates.sort()

        # Asignar greedy
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

            # ── Lógica de conteo ─────────────────────────────────────────────
            if (not self.tracks[tid]['counted']
                    and self.tracks[tid]['frames'] >= self.min_track_frames
                    and prev_cy < self.line_y <= cy):
                self.tracks[tid]['counted'] = True
                self.egg_count += 1

        # Incrementar contador de frames perdidos para tracks sin match
        for tid in list(self.tracks):
            if tid not in used_tracks:
                self.tracks[tid]['lost'] += 1

        # Crear nuevos tracks para centroides sin asignar
        for cidx, (cx, cy) in enumerate(centroids):
            if cidx not in used_centroids:
                self.tracks[self._next_id] = {
                    'cx': cx, 'cy': cy,
                    'frames': 1,
                    'counted': False,
                    'lost': 0,
                }
                self._next_id += 1

        # Eliminar tracks obsoletos
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

    print(f'[egg_count] line_y={line_y}px  video={args.video_path}',
          file=sys.stderr)

    tracker = EggTracker(
        line_y           = line_y,
        max_dist         = args.max_dist,
        min_track_frames = args.min_track_frames,
        max_lost_frames  = args.max_lost_frames,
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

        centroids = detect_egg_centroids(frame, args.min_area, args.max_area)
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
