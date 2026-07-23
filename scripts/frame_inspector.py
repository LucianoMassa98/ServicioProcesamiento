#!/usr/bin/env python3
"""
frame_inspector.py - Extrae frames de diferentes puntos del video
para diagnosticar que pasa cuando la cinta se detiene y reanuda.
"""
import sys
import cv2
import numpy as np

VIDEO_PATH = r"prueba\prueba-mejorada.mp4"

# Rangos HSV actuales
HSV_LOWER = np.array([ 8, 130,  60])
HSV_UPPER = np.array([18, 255, 215])
ROI_X1, ROI_X2 = 160, 480

def analizar_frame(cap, frame_num, save=True):
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    if not ret:
        print(f"  Frame {frame_num}: NO SE PUDO LEER")
        return

    h, w = frame.shape[:2]
    roi  = frame[:, ROI_X1:ROI_X2]
    hsv  = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=1)

    n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
    blobs_validos = [stats[i, cv2.CC_STAT_AREA] for i in range(1, n_labels) if 500 <= stats[i, cv2.CC_STAT_AREA] <= 25000]

    seg = frame_num / 30.0
    mins = int(seg // 60)
    segs = seg % 60
    print(f"  Frame {frame_num:5d} ({mins}:{segs:05.2f}) | pixeles={cv2.countNonZero(mask):5d} | blobs={len(blobs_validos)} | areas={[int(a) for a in blobs_validos[:6]]}")

    if save:
        overlay = frame.copy()
        full_mask = np.zeros((h, w), dtype=np.uint8)
        full_mask[:, ROI_X1:ROI_X2] = mask
        overlay[full_mask > 0] = [0, 255, 0]
        cv2.rectangle(overlay, (ROI_X1, 0), (ROI_X2, h), (255, 0, 0), 2)
        # Linea de conteo
        line_y = int(h * 0.55)
        cv2.line(overlay, (0, line_y), (w, line_y), (0, 180, 255), 2)
        for i in range(1, n_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if 500 <= area <= 25000:
                cx = int(centroids[i][0]) + ROI_X1
                cy = int(centroids[i][1])
                cv2.circle(overlay, (cx, cy), 8, (0, 0, 255), -1)
        out = f"prueba/inspect_f{frame_num:05d}.jpg"
        cv2.imwrite(out, overlay)


def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print("ERROR abriendo video")
        sys.exit(1)

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps   = cap.get(cv2.CAP_PROP_FPS)
    dur   = total / fps
    print(f"Video: {total} frames, {fps}fps, duracion={dur:.1f}s ({int(dur//60)}:{dur%60:.1f}s)")
    print()

    # Analizar frames cada 30 segundos para ver el panorama completo
    print("=== PANORAMA GENERAL (cada 30s) ===")
    for seg in range(0, int(dur), 30):
        frame_num = int(seg * fps)
        analizar_frame(cap, frame_num, save=False)

    print()
    print("=== FRAMES CLAVE (guardados como imagenes) ===")
    # Frames clave: inicio, justo antes de 700 procesado, mitad, fin
    frames_clave = [
        100,    # inicio
        500,    # principio
        1500,   # donde empieza a contar (procesado 700 = frame real ~1400)
        3600,   # frame real donde termino de contar
        4500,   # despues del conteo
        6000,   # 3:20
        7500,   # 4:10
        9000,   # 5:00
    ]
    for f in frames_clave:
        if f < total:
            analizar_frame(cap, f, save=True)

    cap.release()
    print()
    print("Imagenes guardadas en prueba/inspect_*.jpg")


if __name__ == '__main__':
    main()
