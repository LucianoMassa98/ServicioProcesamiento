#!/usr/bin/env python3
"""
egg_count.py  –  Conteo de huevos marrones en cinta transportadora.

Algoritmo:
  1. Convierte cada frame a HSV y aplica máscara para color marrón.
  2. Aplica ROI centrado en la cinta (excluye bordes con color similar).
  3. Usa Distance Transform + supresión de no-máximos para encontrar
     el centro de cada huevo individual, incluso dentro de clusters.
  4. Rastrea centroides entre frames (nearest-neighbour greedy).
  5. Cuenta cada huevo la primera vez que su centroide cruza
     la línea horizontal de conteo (movimiento de arriba→abajo).
  6. Re-cuenta si el track se pierde y el huevo reaparece (ciclos de cinta).

Orientación de cámara: CENITAL (vista desde arriba, cinta vertical).
  - La cinta ocupa el centro del frame (~25% a 75% del ancho).
  - Los huevos se desplazan de la parte superior hacia la inferior.
  - La cinta hace pausas: MAX_LOST_FRAMES es alto para no perder tracks.

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
# CÁMARA CENITAL: la cinta ocupa el centro del frame, movimiento top→bottom.
DEFAULT_LINE_RATIO       = 0.55   # línea al 55% del alto
DEFAULT_MIN_AREA         = 800    # no usado en detección por distancia (solo filtro legacy)
DEFAULT_MAX_AREA         = 22000  # no usado en detección por distancia (solo filtro legacy)
DEFAULT_SKIP_FRAMES      = 2      # procesar 1 de cada N frames
DEFAULT_MAX_DIST         = 80     # distancia máxima px para asociar al mismo track
DEFAULT_MIN_TRACK_FRAMES = 3      # frames mínimos rastreados antes de poder contar
DEFAULT_MAX_LOST_FRAMES  = 60    # frames sin detección antes de eliminar track
                                   # (alto para tolerar pausas de la cinta)

# Radio aproximado de un huevo en píxeles (vista cenital, frame 640x480).
# Ajustar si la cámara cambia de altura o resolución.
# π * r² ≈ 2000px²  →  r ≈ 25px
APPROX_EGG_RADIUS_PX = 25


# ─── Rango HSV para huevos naranja-marrones (cámara cenital) ─────────────────
# Vista cenital: los huevos son muy saturados (S>130) y de tono naranja (H 8-18).
# Las barras de la cinta son más amarillas (H >20) y la malla/pared quedan fuera del ROI.
HSV_LOWER = np.array([ 8, 130,  60])
HSV_UPPER = np.array([18, 255, 215])

# ROI centrado en la cinta transportadora (vista cenital, frame 640x480).
# La cinta ocupa aproximadamente el 25%–75% del ancho del frame.
# Se excluyen los bordes con malla amarilla (izq) y pared amarilla (der).
ROI_X_START_RATIO = float(0.25)   # inicio en X como fracción del ancho
ROI_X_END_RATIO   = float(0.75)   # fin en X como fracción del ancho

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
    Genera una máscara binaria de los píxeles con color de huevo naranja-marrón.

    ROI centrado en X: excluye la malla amarilla (izquierda) y la pared
    amarilla (derecha) que tienen color similar a los huevos.
    Aplica cierre morfológico para rellenar huecos y apertura para quitar ruido.
    """
    h, w = frame.shape[:2]
    x1   = int(w * ROI_X_START_RATIO)
    x2   = int(w * ROI_X_END_RATIO)
    roi  = frame[:, x1:x2]

    hsv      = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask_roi = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)

    mask_roi = cv2.morphologyEx(mask_roi, cv2.MORPH_CLOSE, MORPH_KERNEL, iterations=2)
    mask_roi = cv2.morphologyEx(mask_roi, cv2.MORPH_OPEN,  MORPH_KERNEL, iterations=1)

    # Devolver máscara del tamaño del frame completo (rellenar laterales con 0)
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[:, x1:x2] = mask_roi
    return mask


# ──────────────────────────────────────────────────────────────────────────────
def separate_blobs_watershed(frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    (Usado solo en el script de debug para visualización.)
    Aplica Distance Transform + Watershed sobre la máscara para separar
    huevos que se tocan en el marcador binario.
    Retorna una imagen de marcadores etiquetados (np.int32).
    """
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist, 0.38 * dist.max(), 255, 0)
    sure_fg    = np.uint8(sure_fg)
    sure_bg    = cv2.dilate(mask, MORPH_KERNEL, iterations=2)
    unknown    = cv2.subtract(sure_bg, sure_fg)
    _, markers = cv2.connectedComponents(sure_fg)
    markers    = markers + 1
    markers[unknown == 255] = 0
    markers = cv2.watershed(frame, markers)
    return markers


# ──────────────────────────────────────────────────────────────────────────────
def detect_egg_centroids(frame: np.ndarray, min_area: int, max_area: int) -> list:
    """
    Detecta el centro de cada huevo individual en el frame.

    Pipeline:
      1. Máscara de color naranja-marrón sobre el ROI de la cinta.
      2. Distance Transform: cada píxel toma el valor de su distancia al borde.
         Los centros de huevo quedan como máximos locales.
      3. Supresión de no-máximos con kernel de radio de un huevo:
         en cada ventana del tamaño de un huevo solo queda UN máximo.
      4. Cada máximo local = un huevo individual, incluso dentro de clusters.

    Esta técnica evita el problema de blobs fusionados donde múltiples
    huevos tocados se detectaban como un único centroide.
    """
    mask = build_egg_mask(frame)

    if cv2.countNonZero(mask) == 0:
        return []

    # ── Distance Transform ──────────────────────────────────────────────
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    # dist[y,x] = distancia del píxel (x,y) al borde más cercano
    # Centro de un huevo de radio R tiene dist ≈ R

    # ── Supresión de no-máximos ────────────────────────────────────────
    # Dilatamos con un kernel del tamaño aproximado de un huevo.
    # Tras la dilatación, cada píxel tiene el valor del máximo de su vecindad.
    # Los máximos locales son donde dist ≈ dist_dilated (son el máximo local).
    kernel_diam = max(3, 2 * APPROX_EGG_RADIUS_PX + 5)   # dilámetro de búsqueda
    dil_kernel  = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (kernel_diam, kernel_diam))
    dist_dil    = cv2.dilate(dist, dil_kernel)

    # Un máximo local es un píxel que:
    #   a) Es prácticamente igual al máximo de su vecindad (dist ≥ 98% de dist_dil)
    #   b) Está suficientemente dentro del blob (dist > umbral mínimo)
    min_dist_thr = max(4.0, APPROX_EGG_RADIUS_PX * 0.4)
    local_max    = np.uint8(
        (dist >= dist_dil * 0.92) & (dist > min_dist_thr)
    )

    # Pequeña dilatación para unir máximos muy próximos del mismo huevo
    merge_k   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    local_max = cv2.dilate(local_max, merge_k, iterations=1)

    # ── Extraer centroides de cada máximo local ───────────────────────────
    n_labels, _, stats, cents = cv2.connectedComponentsWithStats(local_max)

    centroids = []
    h, w = mask.shape[:2]
    for i in range(1, n_labels):
        cx = int(cents[i][0])
        cy = int(cents[i][1])
        # Verificar que el centroide esté dentro de la máscara y tenga
        # distancia suficiente al borde (es un centro real, no ruido de borde)
        if 0 <= cy < h and 0 <= cx < w:
            if mask[cy, cx] > 0 and dist[cy, cx] > min_dist_thr:
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
