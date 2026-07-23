#!/usr/bin/env python3
"""
hsv_tuner.py - Prueba rangos HSV mas ajustados para separar huevos de barras.
La cinta ocupa aprox x=165 a x=475 del frame de 640px de ancho.
Los huevos son mas naranja-rojos (H 5-18) que las barras de la cinta (H 20-30).
"""
import sys
import cv2
import numpy as np

VIDEO_PATH = r"prueba\prueba-mejorada.mp4"

# ROI de la cinta: solo la zona central donde estan los huevos
# Frame 640x480: cinta aprox de x=160 a x=480, y=0 a y=480
ROI_X1, ROI_X2 = 160, 480

RANGOS_TEST = [
    # (nombre, H_low, H_high, S_low, S_high, V_low, V_high)
    ("Naranja saturado",   8,  18, 130, 255, 60, 210),
    ("Naranja amplio",     5,  20, 110, 255, 50, 230),
    ("Muy naranja",       10,  20, 140, 255, 80, 200),
    ("Naranja rojo",       5,  15, 120, 255, 60, 220),
]

FRAME_NUM = 100


def main():
    cap = cv2.VideoCapture(VIDEO_PATH)
    cap.set(cv2.CAP_PROP_POS_FRAMES, FRAME_NUM)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("ERROR: no se pudo leer el frame")
        sys.exit(1)

    h, w = frame.shape[:2]
    print(f"Frame {FRAME_NUM}: {w}x{h}")
    print(f"ROI aplicada: x={ROI_X1} a x={ROI_X2} (ancho={ROI_X2-ROI_X1}px)")
    print()

    # Aplicar ROI
    roi = frame[:, ROI_X1:ROI_X2].copy()
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

    for nombre, h_lo, h_hi, s_lo, s_hi, v_lo, v_hi in RANGOS_TEST:
        lower = np.array([h_lo, s_lo, v_lo])
        upper = np.array([h_hi, s_hi, v_hi])

        mask = cv2.inRange(hsv_roi, lower, upper)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=1)

        # Contar blobs y sus areas
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
        blobs_validos = []
        for i in range(1, n_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if 500 <= area <= 25000:
                blobs_validos.append(area)

        pct = 100.0 * cv2.countNonZero(mask) / (roi.shape[0] * roi.shape[1])
        print(f"[{nombre:20s}]  pixeles={cv2.countNonZero(mask):6d} ({pct:.1f}%)  "
              f"blobs_validos={len(blobs_validos)}  areas={[int(a) for a in blobs_validos[:10]]}")

        # Guardar overlay
        full_frame   = frame.copy()
        # Dibujar ROI en el frame completo
        cv2.rectangle(full_frame, (ROI_X1, 0), (ROI_X2, h), (255, 0, 0), 2)
        # Superponer mascara verde en ROI
        full_mask    = np.zeros((h, w), dtype=np.uint8)
        full_mask[:, ROI_X1:ROI_X2] = mask
        full_frame[full_mask > 0] = [0, 255, 0]
        # Dibujar contornos y centroides de blobs validos
        for i in range(1, n_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if 500 <= area <= 25000:
                cx = int(centroids[i][0]) + ROI_X1
                cy = int(centroids[i][1])
                cv2.circle(full_frame, (cx, cy), 8, (0, 0, 255), -1)
        out = f"prueba/tuner_{nombre.replace(' ', '_')}.jpg"
        cv2.imwrite(out, full_frame)

    print()
    print("Imagenes guardadas en prueba/tuner_*.jpg")


if __name__ == '__main__':
    main()
