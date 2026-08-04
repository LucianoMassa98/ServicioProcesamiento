#!/usr/bin/env python3
"""
run_prueba.py  –  Ejecuta egg_count.py sobre todos los videos de prueba/
y compara los resultados con el conteo manual estimado de conteo-realizado.txt.

Uso:
  python scripts/run_prueba.py
"""

import os
import sys
import subprocess
import json
import time


# ─── Configuración ────────────────────────────────────────────────────────────
PRUEBA_DIR   = os.path.join(os.path.dirname(__file__), '..', 'prueba')
CONTEO_FILE  = os.path.join(PRUEBA_DIR, 'conteo-realizado.txt')
SCRIPT_PATH  = os.path.join(os.path.dirname(__file__), 'egg_count.py')
PYTHON_BIN   = os.environ.get('PYTHON_BIN', 'python')


def load_expected_counts():
    """Carga el archivo conteo-realizado.txt → dict {filename: count}"""
    expected = {}
    with open(CONTEO_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or ',' not in line:
                continue
            parts = line.split(',')
            filename = parts[0].strip()
            count = int(parts[1].strip())
            expected[filename] = count
    return expected


def run_egg_count(video_path):
    """Ejecuta egg_count.py y retorna el resultado JSON."""
    cmd = [
        PYTHON_BIN, SCRIPT_PATH, video_path,
        '--direction', 'up',
        '--line-ratio', '0.50',
        '--x-margin', '25',
        '--min-travel', '40',
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f'  ERROR (exit {result.returncode}): {result.stderr.strip()}', file=sys.stderr)
        return None

    if result.stderr.strip():
        print(f'  [log] {result.stderr.strip()}', file=sys.stderr)

    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        print(f'  ERROR parsing JSON: {e} — stdout: {result.stdout.strip()}', file=sys.stderr)
        return None


def main():
    expected = load_expected_counts()

    if not expected:
        print(f'ERROR: No se encontraron conteos en {CONTEO_FILE}')
        sys.exit(1)

    print('=' * 70)
    print('  PRUEBA DE CONTEO DE HUEVOS')
    print('  Direccion: abajo -> arriba  |  Linea: 50%  |  ROI: 100%')
    print('=' * 70)
    print()

    results = []
    total_start = time.time()

    for filename, manual_count in sorted(expected.items()):
        video_path = os.path.join(PRUEBA_DIR, filename)

        if not os.path.isfile(video_path):
            print(f'[!] {filename}: archivo no encontrado, saltando...')
            continue

        print(f'>>  Procesando: {filename}  (conteo manual: ~{manual_count})')
        start = time.time()
        result = run_egg_count(video_path)
        elapsed = round(time.time() - start, 2)

        if result is None:
            print(f'   X Error al procesar\n')
            results.append((filename, manual_count, None, None, None))
            continue

        counted = result['eggs']
        diff = counted - manual_count
        pct_diff = (diff / manual_count * 100) if manual_count > 0 else 0

        status = 'OK' if abs(pct_diff) <= 20 else '!!'
        print(f'   {status} Resultado: {counted} huevos  (manual: ~{manual_count}  diff: {diff:+d}  {pct_diff:+.1f}%)  [{elapsed}s]')
        print()

        results.append((filename, manual_count, counted, diff, pct_diff))

    total_elapsed = round(time.time() - total_start, 2)

    # ─── Resumen ──────────────────────────────────────────────────────────
    print()
    print('=' * 70)
    print('  RESUMEN')
    print('=' * 70)
    print(f'  {"Video":<35} {"Manual":>7} {"Contado":>8} {"Diff":>6} {"Diff%":>7}')
    print('  ' + '-' * 63)

    ok_count = 0
    for filename, manual, counted, diff, pct_diff in results:
        if counted is None:
            print(f'  {filename:<35} {manual:>7}   {"ERROR":>8}')
        else:
            marker = 'OK' if abs(pct_diff) <= 20 else '!!'
            print(f'  {filename:<35} {manual:>7} {counted:>8} {diff:>+6d} {pct_diff:>+6.1f}%  {marker}')
            if abs(pct_diff) <= 20:
                ok_count += 1

    valid = [r for r in results if r[2] is not None]
    total_manual  = sum(r[1] for r in valid)
    total_counted = sum(r[2] for r in valid)

    print()
    print(f'  Total manual:  {total_manual}')
    print(f'  Total contado: {total_counted}')
    if total_manual > 0:
        global_pct = (total_counted - total_manual) / total_manual * 100
        print(f'  Diferencia:    {total_counted - total_manual:+d} ({global_pct:+.1f}%)')
    print(f'  Videos OK (±20%): {ok_count}/{len(valid)}')
    print(f'  Tiempo total: {total_elapsed}s')
    print('=' * 70)


if __name__ == '__main__':
    main()
