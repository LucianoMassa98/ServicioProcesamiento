#!/usr/bin/env python3
"""
hsv_diagnostic.py - Extrae valores HSV reales de los huevos en el video
para calibrar correctamente el rango de color.

Guarda:
  - Un frame de muestra del video (frame_muestra.jpg)
  - La máscara HSV aplicada (frame_mascara.jpg)
  - Estadísticas HSV en stdout
"""

import sys
import cv2
import numpy as np

VIDEO_PATH = r"prueba\prueba-mejorada.mp4"

# Rangos a testear (amplios para diagnosticar)
RANGOS_TEST = [
    # (nombre, lower, upper)
    ("Original lateral",  np.array([ 5, 100,  80]), np.array([22, 255, 230])),
    ("Cenital v1",        np.array([ 5,  90,  70]), np.array([25, 255, 235])),
    ("Muy amplio",        np.array([ 0,  50,  50]), np.array([35, 255, 255])),
    ("Solo naranja",      np.array([ 8,  80,  60]), np.array([20, 255, 220])),
]

FRAME_NUMS = [100, 300, 500, 800, 1200]  # frames a analizar


def analizar_frame(cap, frame_num):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    if not ret:
        return None, None
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return frame, hsv


def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"ERROR: No se pudo abrir {VIDEO_PATH}")
        sys.exit(1)

    total   = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps     = cap.get(cv2.CAP_PROP_FPS)
    print(f"Video: {width}x{height} @ {fps:.1f}fps, {total} frames totales")
    print()

    best_frame = None
    best_frame_num = FRAME_NUMS[0]

    for frame_num in FRAME_NUMS:
        frame, hsv = analizar_frame(cap, frame_num)
        if frame is None:
            continue

        if best_frame is None:
            best_frame = frame
            best_frame_num = frame_num

        print(f"─── Frame {frame_num} ─────────────────────────────")
        for nombre, lower, upper in RANGOS_TEST:
            mask    = cv2.inRange(hsv, lower, upper)
            pixeles = cv2.countNonZero(mask)
            pct     = 100.0 * pixeles / (width * height)
            print(f"  [{nombre:20s}]  píxeles={pixeles:6d}  ({pct:.1f}% del frame)")

        # Estadísticas HSV del frame completo
        h_vals = hsv[:, :, 0].flatten()
        s_vals = hsv[:, :, 1].flatten()
        v_vals = hsv[:, :, 2].flatten()

        # Filtrar píxeles con saturación media (probable color de huevo)
        mask_sat = (hsv[:, :, 1] > 60) & (hsv[:, :, 0] < 35) & (hsv[:, :, 0] > 2)
        if mask_sat.sum() > 100:
            h_egg = hsv[:, :, 0][mask_sat]
            s_egg = hsv[:, :, 1][mask_sat]
            v_egg = hsv[:, :, 2][mask_sat]
            print(f"  Píxeles naranjas/marrones (S>60, H 2-35): {mask_sat.sum()}")
            print(f"    H: min={h_egg.min()}  max={h_egg.max()}  mean={h_egg.mean():.1f}")
            print(f"    S: min={s_egg.min()}  max={s_egg.max()}  mean={s_egg.mean():.1f}")
            print(f"    V: min={v_egg.min()}  max={v_egg.max()}  mean={v_egg.mean():.1f}")
            # Guardar máscara de este frame
            if frame_num == best_frame_num:
                best_frame = frame
        print()

    # Guardar frame de muestra y máscaras
    if best_frame is not None:
        frame_out = f"prueba/frame_muestra_{best_frame_num}.jpg"
        cv2.imwrite(frame_out, best_frame)
        print(f"Frame guardado: {frame_out}")

        hsv_frame = cv2.cvtColor(best_frame, cv2.COLOR_BGR2HSV)

        for nombre, lower, upper in RANGOS_TEST:
            mask  = cv2.inRange(hsv_frame, lower, upper)
            # Morfología básica
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask   = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask   = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=1)
            # Overlay sobre frame original
            overlay        = best_frame.copy()
            overlay[mask > 0] = [0, 255, 0]
            out_name = f"prueba/mascara_{nombre.replace(' ', '_')}.jpg"
            cv2.imwrite(out_name, overlay)
            print(f"Máscara [{nombre}] guardada: {out_name}")

    cap.release()
    print("\n¡Diagnóstico completo!")


if __name__ == '__main__':
    main()
