#!/usr/bin/env python3
"""
Parameter grid search: test multiple parameter combinations on all videos
to find the best settings for the egg counter.
"""
import os, sys, subprocess, json, time, itertools

PRUEBA_DIR  = os.path.join(os.path.dirname(__file__), '..', 'prueba')
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'egg_count.py')
PYTHON_BIN  = os.environ.get('PYTHON_BIN', 'python')

EXPECTED = {
    '2026-08-02_09-00-18.mp4': 48,
    '2026-08-02_09-05-26.mp4': 250,
    '2026-08-02_09-10-26.mp4': 84,
    '2026-08-02_09-15-26.mp4': 3,
    '2026-08-02_09-20-26.mp4': 281,
}

# Parameter grid
PARAMS = {
    'min_peak_dist': [12, 13, 14],
    'min_travel':    [40, 60, 80, 100],
    'min_track_frames': [3, 5, 8],
    'max_dist':      [30, 45],
    'x_margin':      [25, 35],
    'warmup_frames': [45],
}


def run_one(video_path, params):
    cmd = [
        PYTHON_BIN, SCRIPT_PATH, video_path,
        '--direction', 'up',
        '--line-ratio', '0.50',
        '--skip-frames', '2',
        '--min-peak-dist', str(params['min_peak_dist']),
        '--min-travel', str(params['min_travel']),
        '--min-track-frames', str(params['min_track_frames']),
        '--max-dist', str(params['max_dist']),
        '--x-margin', str(params['x_margin']),
        '--warmup-frames', str(params['warmup_frames']),
        '--peak-window', '19',
        '--max-lost-frames', '6',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout.strip())
    except:
        return None


def score_results(results):
    """Lower score = better. Weighted sum of absolute percentage errors."""
    total_score = 0
    for vname, expected in EXPECTED.items():
        if vname not in results or results[vname] is None:
            total_score += 200  # penalty for failure
            continue
        counted = results[vname]
        if expected == 0:
            total_score += counted * 100
        else:
            pct_err = abs(counted - expected) / expected * 100
            total_score += pct_err
    return total_score


def main():
    # Generate all parameter combinations
    keys = sorted(PARAMS.keys())
    values = [PARAMS[k] for k in keys]
    combos = list(itertools.product(*values))
    
    print(f'Testing {len(combos)} parameter combinations on {len(EXPECTED)} videos...')
    print(f'Total runs: {len(combos) * len(EXPECTED)}')
    print()
    
    best_score = float('inf')
    best_params = None
    best_results = None
    all_results = []
    
    for i, vals in enumerate(combos):
        params = dict(zip(keys, vals))
        results = {}
        
        for vname, expected in EXPECTED.items():
            vpath = os.path.join(PRUEBA_DIR, vname)
            r = run_one(vpath, params)
            if r:
                results[vname] = r['eggs']
            else:
                results[vname] = None
        
        score = score_results(results)
        all_results.append((score, params, results))
        
        if score < best_score:
            best_score = score
            best_params = params.copy()
            best_results = results.copy()
            
        # Progress
        if (i + 1) % 10 == 0 or i == 0:
            print(f'  [{i+1}/{len(combos)}] Current best score: {best_score:.1f}')
    
    # Sort by score
    all_results.sort(key=lambda x: x[0])
    
    print()
    print('=' * 80)
    print('  TOP 10 PARAMETER COMBINATIONS')
    print('=' * 80)
    
    for rank, (score, params, results) in enumerate(all_results[:10], 1):
        print(f'\n--- #{rank} (score={score:.1f}) ---')
        print(f'  Params: {params}')
        for vname in sorted(EXPECTED.keys()):
            exp = EXPECTED[vname]
            got = results.get(vname, 'ERR')
            if got is not None and got != 'ERR':
                diff = got - exp
                pct = (diff / exp * 100) if exp > 0 else 0
                ok = 'OK' if abs(pct) <= 20 else '!!'
                print(f'  {vname}: {got:>4} vs {exp:>4} ({diff:+4d}, {pct:+.0f}%) {ok}')
            else:
                print(f'  {vname}: ERROR')
    
    print()
    print('=' * 80)
    print(f'  BEST: score={best_score:.1f}')
    print(f'  Params: {best_params}')
    print('=' * 80)


if __name__ == '__main__':
    main()
