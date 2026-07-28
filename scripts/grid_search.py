import subprocess, json, sys

configs = [
    {'line': 0.45, 'min_area': 200, 'max_dist': 90,  'min_track': 1},
    {'line': 0.50, 'min_area': 200, 'max_dist': 90,  'min_track': 1},
    {'line': 0.55, 'min_area': 200, 'max_dist': 90,  'min_track': 1},
    {'line': 0.60, 'min_area': 200, 'max_dist': 90,  'min_track': 1},
    {'line': 0.65, 'min_area': 200, 'max_dist': 90,  'min_track': 1},
    {'line': 0.70, 'min_area': 200, 'max_dist': 90,  'min_track': 1},
    {'line': 0.65, 'min_area': 100, 'max_dist': 90,  'min_track': 1},
    {'line': 0.65, 'min_area': 150, 'max_dist': 90,  'min_track': 1},
    {'line': 0.65, 'min_area': 200, 'max_dist': 120, 'min_track': 1},
    {'line': 0.55, 'min_area': 150, 'max_dist': 90,  'min_track': 1},
    {'line': 0.60, 'min_area': 150, 'max_dist': 90,  'min_track': 1},
]

print('line  | min_area | max_dist | eggs (real=82)')
print('-' * 45)
for cfg in configs:
    r = subprocess.run([
        'python', 'scripts/egg_count.py', 'prueba/nuevaPrueba.mp4',
        '--line-ratio',       str(cfg['line']),
        '--min-area',         str(cfg['min_area']),
        '--max-dist',         str(cfg['max_dist']),
        '--min-track-frames', str(cfg['min_track']),
    ], capture_output=True, text=True)
    try:
        result = json.loads(r.stdout.strip())
        eggs = result['eggs']
    except Exception as e:
        eggs = f'ERR:{r.stderr[:40]}'
    tag = ''
    if isinstance(eggs, int):
        if eggs == 82:
            tag = ' <-- PERFECTO'
        elif eggs >= 78:
            tag = ' <-- MUY BUENO'
        elif eggs >= 72:
            tag = ' <== bueno'
    print(f'{cfg["line"]:.2f}  | {cfg["min_area"]:8d} | {cfg["max_dist"]:8.0f} | {eggs}{tag}')
