"""Tune the ball-flow parameters of the simulator against real match statistics (pass direction, thirds, accuracy, shots).

Coordinate search over a few interpretable parameters (module dicts PASS and SHOT in gamepulse/simulator/match.py), with
bounds, a penalty for leaving the starting point, and the loss made of the rows of `gamepulse.spatial` and `gamepulse.calibration`
(each row counts for its squared error in tolerance units, capped). Fixed seeds, so candidates are compared on the same matches.

    python tools/tune_flow.py --rounds 6
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SPEC = [("PASS", "dir_base", 0.8, 2.6), ("PASS", "lateral", 0.7, 2.5), ("PASS", "fw_back", 0.1, 1.0), ("PASS", "back", 0.15, 1.2),
        ("PASS", "dist_scale", 0.4, 1.2), ("PASS", "rw_df", 0.8, 3.0), ("PASS", "rw_fw", 0.15, 1.0), ("PASS", "wide", 0.5, 8.0),
        ("PASS", "own_keep", 1.0, 12.0), ("PASS", "fin_back", 0.2, 1.0), ("SHOT", "p", 0.04, 0.12), ("SHOT", "box_near", 1.0, 5.0)]


def evaluate(params: dict[str, float], n: int = 40, seed0: int = 1000) -> tuple[float, dict]:
    from gamepulse import calibration as cal
    from gamepulse import spatial
    from gamepulse.simulator import match

    for (d, k, _, _), v in zip(SPEC, params.values()):
        getattr(match, d)[k] = v
    R, S = spatial.real_spatial(), spatial.sim_spatial(n=n, seed0=seed0)
    Rc, C = cal.real_stats(), cal.sim_stats(n=n, seed0=seed0)
    loss, detail = 0.0, {}
    for k, _, tol in spatial.ROWS:
        z = (S[k] - R[k]) / tol
        loss += min(z * z, 9.0)
        detail[k] = round(S[k], 1)
    for k in cal.KEYS:
        z = (C[k] - Rc[k]) / (cal.TOL[k] * abs(Rc[k]))
        loss += 1.5 * min(z * z, 9.0)
        detail[k] = round(C[k], 2)
    return loss, detail


def _job(args):
    return evaluate(*args)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--start", default=None, help="JSON of starting values")
    a = ap.parse_args()
    from gamepulse.simulator import match

    cur = {f"{d}.{k}": getattr(match, d)[k] for d, k, _, _ in SPEC}
    if a.start:
        cur.update(json.loads(a.start))
    start = dict(cur)
    keys = list(cur)
    bounds = {f"{d}.{k}": (lo, hi) for d, k, lo, hi in SPEC}
    with ProcessPoolExecutor(14) as ex:
        best, _ = evaluate(cur, a.n)
        print(f"start loss {best:.1f}", flush=True)
        step = 0.25
        for r in range(a.rounds):
            cands = []
            for k in keys:
                for sgn in (+1, -1):
                    c = dict(cur)
                    lo, hi = bounds[k]
                    c[k] = min(hi, max(lo, cur[k] * (1 + sgn * step)))
                    if c[k] != cur[k]:
                        cands.append((k, c))
            res = list(ex.map(_job, [(c, a.n) for _, c in cands]))
            scored = sorted(((l + 0.4 * sum(((c[k] - start[k]) / max(abs(start[k]), 1e-9)) ** 2 for k in keys), l, c, k) for (k, c), (l, _) in zip(cands, res)),
                            key=lambda t: t[0])
            moved = False
            used: set[str] = set()
            for pen, l, c, k in scored[:4]:  # apply the best non-conflicting moves together, keep them only if the whole improves
                if k in used:
                    continue
                used.add(k)
                trial = dict(cur)
                trial[k] = c[k]
                if l < best:
                    cur, best, moved = trial, l, True
                    break
            print(f"round {r + 1}: loss {best:.1f} step {step:.2f}  best move {scored[0][3]}", flush=True)
            if not moved:
                step *= 0.5
    print(json.dumps({k: round(v, 3) for k, v in cur.items()}))
    print(json.dumps(evaluate(cur, a.n)[1]))


if __name__ == "__main__":
    main()
