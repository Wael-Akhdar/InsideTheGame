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

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SPEC_ES = [("PASS", "dir_base", 0.8, 3.0), ("PASS", "lateral", 0.5, 2.5), ("PASS", "fw_back", 0.1, 1.5), ("PASS", "back", 0.15, 1.2),
           ("PASS", "dist_scale", 0.3, 1.2), ("PASS", "rw_df", 0.8, 3.0), ("PASS", "rw_mf", 0.5, 2.0), ("PASS", "rw_fw", 0.05, 1.0),
           ("PASS", "wide", 2.0, 30.0), ("PASS", "own_keep", 1.0, 12.0), ("PASS", "fin_back", 0.2, 2.0), ("PASS", "carry", 0.1, 1.5),
           ("WANDER", "sx", 4.0, 30.0), ("WANDER", "sy", 4.0, 25.0), ("SHOT", "p", 0.04, 0.16), ("SHOT", "box_near", 1.0, 6.0),
           ("SHOT", "finish", 0.8, 1.6), ("CLEAR", "p", 0.05, 0.5), ("DUEL", "win", 0.05, 0.6), ("QUALITY", "pass", 0.001, 0.02),
           ("QUALITY", "def", 0.001, 0.03), ("QUALITY", "keep", 0.0005, 0.03), ("QUALITY", "fin", 0.1, 1.5)]
# Real targets for a strong side against a weak one (strength gap about 1.07, gamepulse/strength.py): share of the passes, of the shots,
# and log ratio of goals. The simulator plays them with squad qualities 1 +/- QUALITY_PER_GAP * 1.07 / 2.
GAP_TARGETS = {"s_share": (58.5, 1.5), "s_shot": (61.5, 2.5), "s_logr": (1.07, 0.15)}
SPEC = [("PASS", "dir_base", 0.8, 2.6), ("PASS", "lateral", 0.7, 2.5), ("PASS", "fw_back", 0.1, 1.0), ("PASS", "back", 0.15, 1.2),
        ("PASS", "dist_scale", 0.4, 1.2), ("PASS", "rw_df", 0.8, 3.0), ("PASS", "rw_fw", 0.05, 1.0), ("PASS", "fwd_cap", 8.0, 100.0), ("PASS", "wide", 0.5, 8.0),
        ("PASS", "own_keep", 1.0, 12.0), ("PASS", "fin_back", 0.2, 1.5), ("PASS", "carry", 0.2, 1.5), ("WANDER", "sx", 6.0, 32.0), ("WANDER", "sy", 3.0, 20.0), ("SHOT", "p", 0.04, 0.12), ("SHOT", "box_near", 1.0, 5.0)]


def evaluate(params: dict[str, float], n: int = 40, seed0: int = 1000) -> tuple[float, dict]:
    from gamepulse import calibration as cal
    from gamepulse import spatial
    from gamepulse.simulator import match

    for name, v in params.items():
        d, k = name.split(".")
        getattr(match, d)[k] = v
    if any(k.startswith("QUALITY") for k in params):  # strength term: possession, shots and goals of a much stronger side
        import math

        from gamepulse import strength

        g = match.QUALITY_PER_GAP * 1.07
        rows = strength._sim_job((1 + g / 2, 1 - g / 2, list(range(seed0, seed0 + n)), "Balanced 4-3-3", "Balanced 4-3-3"))
        gf, ga = sum(r["gf"] for r in rows) + 0.5, sum(r["ga"] for r in rows) + 0.5
        got = {"s_share": float(np.mean([r["pass_share"] for r in rows])), "s_shot": float(np.mean([r["shot_share"] for r in rows])),
               "s_logr": math.log(gf / ga)}
        gap_loss = sum(min(((got[k] - t) / tol) ** 2, 9.0) for k, (t, tol) in GAP_TARGETS.items())
    else:
        got, gap_loss = {}, 0.0
    R, S = spatial.real_spatial(), spatial.sim_spatial(n=n, seed0=seed0)
    Rc, C = cal.real_stats(), cal.sim_stats(n=n, seed0=seed0)
    loss, detail = 1.5 * gap_loss, {k: round(v, 2) for k, v in got.items()}
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


def evolve(gens: int, n: int, pop: int = 14, sigma: float = 0.15) -> dict[str, float]:
    """Simple evolution strategy in log-parameter space: sample around the mean, move the mean towards the best samples."""
    import numpy as np

    from gamepulse.simulator import match

    names = [f"{d}.{k}" for d, k, _, _ in SPEC_ES]
    lo = np.log([s[2] for s in SPEC_ES])
    hi = np.log([s[3] for s in SPEC_ES])
    mean = np.clip(np.log([getattr(match, d)[k] for d, k, _, _ in SPEC_ES]), lo, hi)
    rng = np.random.default_rng(0)
    to_params = lambda v: {nm: float(np.exp(x)) for nm, x in zip(names, v)}
    best_v, (best_l, best_d) = mean.copy(), evaluate(to_params(mean), n)
    print(f"start loss {best_l:.1f}", flush=True)
    with ProcessPoolExecutor(pop) as ex:
        for g in range(gens):
            cands = [np.clip(mean + sigma * rng.standard_normal(len(names)), lo, hi) for _ in range(pop)]
            res = list(ex.map(_job, [(to_params(c), n) for c in cands]))
            order = np.argsort([r[0] for r in res])
            elite = [cands[i] for i in order[:4]]
            w = np.array([4.0, 3.0, 2.0, 1.0]) / 10
            mean = np.clip(sum(wi * e for wi, e in zip(w, elite)), lo, hi)
            if res[order[0]][0] < best_l:
                best_l, best_d, best_v = res[order[0]][0], res[order[0]][1], cands[order[0]]
                sigma = min(0.3, sigma * 1.1)
            else:
                sigma *= 0.85
            print(f"gen {g + 1}: best {best_l:.1f} (this gen {res[order[0]][0]:.1f}) sigma {sigma:.3f}", flush=True)
    out = to_params(best_v)
    print(json.dumps({k: round(v, 4) for k, v in out.items()}))
    print(json.dumps(best_d))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--start", default=None, help="JSON of starting values")
    ap.add_argument("--es", type=int, default=0, help="run an evolution strategy for this many generations instead")
    a = ap.parse_args()
    if a.es:
        evolve(a.es, a.n)
        return
    from gamepulse.simulator import match

    cur = {f"{d}.{k}": getattr(match, d)[k] for d, k, _, _ in SPEC}  # coordinate search
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
