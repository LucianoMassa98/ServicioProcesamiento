#!/usr/bin/env python3
"""
egg_count_debug.py  –  Versión de debug del contador de huevos.

Genera un video anotado con:
  - Contornos verdes sobre los huevos detectados
  - Punto rojo en el centroide de cada detección
  - ID de track y estado (activo / contado)
  - Línea de conteo horizontal en azul
  - Contador total en la esquina superior izquierda

Uso:
  python scripts/egg_count_debug.py prueba/prueba.mp4
  python scripts/egg_count_debug.py prueba/prueba.mp4 --out prueba/debug_out.mp4
"""

import sys
import math
import argparse

import cv2
import numpy as np

# ─── Importar lógica del script principal ─────────────────────────────────────
sys.path.insert(0, 'scripts')
from egg_count import (
    build_egg_mask, separate_blobs_watershed, detect_egg_centroids,
    EggTracker,
    DEFAULT_LINE_RATIO, DEFAULT_MIN_AREA, DEFAULT_MAX_AREA,
    DEFAULT_SKIP_FRAMES, DEFAULT_MAX_DIST,
    DEFAULT_MIN_TRACK_FRAMES, DEFAULT_MAX_LOST_FRAMES,
)

# ─── Colores BGR ──────────────────────────────────────────────────────────────
COLOR_LINE      = (255, 180,   0)   # azul claro  → línea de conteo
COLOR_CONTOUR   = (  0, 255,   0)   # verde       → contorno detectado
COLOR_CENTROID  = (  0,   0, 255)   # rojo        → centroide
COLOR_COUNTED   = (  0, 200, 255)   # amarillo    → huevo ya contado
COLOR_TEXT      = (255, 255, 255)   # blanco      → textos


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('video_path')
    p.add_argument('--out',              default=None,                  help='Ruta de salida del video anotado')
    p.add_argument('--line-ratio',       type=float, default=DEFAULT_LINE_RATIO)
    p.add_argument('--min-area',         type=int,   default=DEFAULT_MIN_AREA)
    p.add_argument('--max-area',         type=int,   default=DEFAULT_MAX_AREA)
    p.add_argument('--skip-frames',      type=int,   default=DEFAULT_SKIP_FRAMES)
    p.add_argument('--max-dist',         type=float, default=DEFAULT_MAX_DIST)
    p.add_argument('--min-track-frames', type=int,   default=DEFAULT_MIN_TRACK_FRAMES)
    p.add_argument('--max-lost-frames',  type=int,   default=DEFAULT_MAX_LOST_FRAMES)
    return p.parse_args()


def draw_overlay(frame, tracker, line_y, egg_count, frame_idx):
    h, w = frame.shape[:2]

    # ── Línea de conteo ────────────────────────────────────────────────────
    cv2.line(frame, (0, line_y), (w, line_y), COLOR_LINE, 2)
    cv2.putText(frame, f'Linea conteo ({int(100*line_y/h)}%)',
                (10, line_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_LINE, 1)

    # ── Tracks activos ─────────────────────────────────────────────────────
    for tid, t in tracker.tracks.items():
        cx, cy   = t['cx'], t['cy']
        counted  = t['counted']
        color    = COLOR_COUNTED if counted else COLOR_CENTROID

        cv2.circle(frame, (cx, cy), 6, color, -1)
        cv2.putText(frame, f'#{tid}', (cx + 8, cy - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    # ── Contador principal ─────────────────────────────────────────────────
    label = f'Huevos: {egg_count}'
    cv2.rectangle(frame, (8, 8), (200, 48), (0, 0, 0), -1)
    cv2.putText(frame, label, (14, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, COLOR_TEXT, 2)

    # ── Frame index ────────────────────────────────────────────────────────
    cv2.putText(frame, f'Frame {frame_idx}', (w - 130, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_TEXT, 1)

    return frame


def main():
    args = parse_args()

    cap = cv2.VideoCapture(args.video_path)
    if not cap.isOpened():
        print(f'ERROR: No se pudo abrir {args.video_path}', file=sys.stderr)
        sys.exit(1)

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    line_y = int(height * args.line_ratio)

    out_path = args.out or args.video_path.replace('.mp4', '_debug.mp4').replace('.MP4', '_debug.mp4')
    writer   = cv2.VideoWriter(
        out_path,
        cv2.VideoWriter_fourcc(*'mp4v'),
        fps / args.skip_frames,   # compensar frames salteados
        (width, height),
    )

    tracker   = EggTracker(line_y, args.max_dist, args.min_track_frames, args.max_lost_frames)
    frame_idx = 0
    processed = 0

    print(f'Procesando {args.video_path}  ({width}x{height} @ {fps:.1f}fps, {total} frames)')
    print(f'Línea de conteo: y={line_y}px  |  salida: {out_path}')

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % args.skip_frames != 0:
            continue

        # Detectar y actualizar tracker
        centroids = detect_egg_centroids(frame, args.min_area, args.max_area)
        tracker.update(centroids)

        # Dibujar contornos sobre la máscara
        mask    = build_egg_mask(frame)
        markers = separate_blobs_watershed(frame, mask)
        for label in np.unique(markers):
            if label <= 1:
                continue
            component = np.zeros(mask.shape, dtype=np.uint8)
            component[markers == label] = 255
            area = cv2.countNonZero(component)
            if not (args.min_area <= area <= args.max_area):
                continue
            contours, _ = cv2.findContours(component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(frame, contours, -1, COLOR_CONTOUR, 2)

        # Superponer información
        frame = draw_overlay(frame, tracker, line_y, tracker.egg_count, frame_idx)
        writer.write(frame)
        processed += 1

        if processed % 50 == 0:
            pct = 100 * frame_idx / max(total, 1)
            print(f'  {pct:.1f}%  frames procesados={processed}  huevos={tracker.egg_count}')

    cap.release()
    writer.release()

    print(f'\n=== RESULTADO FINAL ===')
    print(f'Huevos contados : {tracker.egg_count}')
    print(f'Frames procesados: {processed}')
    print(f'Video debug     : {out_path}')


if __name__ == '__main__':
    main()
