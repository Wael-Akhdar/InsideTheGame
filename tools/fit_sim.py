"""Tune the passing and shooting behaviour of the simulator against real match statistics (Wyscout public dataset, CC BY 4.0).

Targets: where passes start and which way they go (forward / backward / lateral, own third / final third, how wide), plus the
headline statistics already used by gamepulse/calibration.py (passes, accuracy, pass length, shots, goals, fouls).
Only aggregated numbers are kept. Run:  python tools/fit_sim.py [--fit] [-n 24]
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamepulse import calibration  # noqa: E402
from gamepulse.simulator import match as M  # noqa: E402
from gamepulse.simulator.match import MatchSimulator  # noqa: E402

CACHE = calibration.DATA / "sim_targets.json"
KEYS = ["fwd", "back", "lat", "x10", "x50", "x90", "y_std", "wide", "own3", "final3", "sh_gk", "sh_df", "sh_mf", "sh_fw", "passes", "pass_acc", "pass_len", "shots", "goals", "conv", "fouls"]
TOL = dict(sh_gk=2.5, sh_df=7, sh_mf=7, sh_fw=8, fwd=3, back=3, lat=2, x10=3, x50=3, x90=3, y_std=2, wide=3, own3=3, final3=3, passes=25, pass_acc=2, pass_len=1.2, shots=0.8, goals=0.15, conv=1.5, fouls=1.5)


def real_targets() -> dict[str, float]:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    z = zipfile.ZipFile(calibration.DATA / "events.zip")
    rows = []
    for lg in calibration.LEAGUES:
        for e in json.loads(z.read(f"events_{lg}.json")):
            if e["eventName"] == "Pass" and len(e["positions"]) == 2 and e["positions"][1]:
                a, b = e["positions"]
                rows.append((a["x"], a["y"], b["x"] - a["x"], b["y"] - a["y"]))
    R = np.array(rows)
    base = calibration.real_stats()
    roles = {p["wyId"]: p["role"]["code2"] for p in json.loads((calibration.DATA / "players.json").read_text(encoding="utf-8"))}
    line_n = {"GK": 0, "DF": 0, "MD": 0, "FW": 0}
    for lg in calibration.LEAGUES:
        for e in json.loads(z.read(f"events_{lg}.json")):
            if e["eventName"] == "Pass" and roles.get(e["playerId"]) in line_n:
                line_n[roles[e["playerId"]]] += 1
    tot = sum(line_n.values())
    shares = {"sh_gk": 100 * line_n["GK"] / tot, "sh_df": 100 * line_n["DF"] / tot, "sh_mf": 100 * line_n["MD"] / tot, "sh_fw": 100 * line_n["FW"] / tot}
    out = path_stats(R[:, 0], R[:, 1], R[:, 2] * 1.05) | shares | {k: base[k] for k in ("passes", "pass_acc", "pass_len", "shots", "goals", "conv", "fouls")}
    CACHE.write_text(json.dumps(out))
    return out


def path_stats(x, y, dx_m) -> dict[str, float]:
    return {"fwd": 100 * float((dx_m > 3).mean()), "back": 100 * float((dx_m < -3).mean()), "lat": 100 * float((abs(dx_m) <= 3).mean()),
            "x10": float(np.percentile(x, 10)), "x50": float(np.percentile(x, 50)), "x90": float(np.percentile(x, 90)), "y_std": float(np.std(y)),
            "wide": 100 * float((abs(y - 50) > 25).mean()), "own3": 100 * float((x < 33).mean()), "final3": 100 * float((x > 66).mean())}


def sim_metrics(n: int = 24, seed0: int = 0) -> dict[str, float]:
    xs, ys, dxs = [], [], []
    tot = dict(passes=0, ok=0, length=0.0, shots=0, goals=0, fouls=0)
    lines = {"GK": 0, "DF": 0, "MF": 0, "FW": 0}
    for s in range(seed0, seed0 + n):
        sim = MatchSimulator(seed=s, home_tactic="Balanced 4-3-3", away_tactic="Balanced 4-3-3", record_frames=False)
        line_of = {p.id: p.position for t in (sim.home, sim.away) for p in t.players}
        for e in sim.events():
            if e.type == "pass":
                lines[line_of[e.player]] += 1
                tot["passes"] += 1
                tot["ok"] += e.outcome == "success"
                tot["length"] += e.meta["distance_m"]
                xs.append(e.x)
                ys.append(e.y)
                dxs.append((e.end_x - e.x) * 1.05)
            elif e.type == "shot":
                tot["shots"] += 1
            elif e.type == "goal":
                tot["goals"] += 1
            elif e.type == "foul":
                tot["fouls"] += 1
    tm = 2 * n
    out = path_stats(np.array(xs), np.array(ys), np.array(dxs))
    out.update(sh_gk=100 * lines["GK"] / tot["passes"], sh_df=100 * lines["DF"] / tot["passes"], sh_mf=100 * lines["MF"] / tot["passes"],
               sh_fw=100 * lines["FW"] / tot["passes"])
    out.update(passes=tot["passes"] / tm, pass_acc=100 * tot["ok"] / tot["passes"], pass_len=tot["length"] / tot["passes"],
               shots=tot["shots"] / tm, goals=tot["goals"] / tm, conv=100 * tot["goals"] / max(1, tot["shots"]), fouls=tot["fouls"] / tm)
    return out


PARAMS = [("PASS", "prior", 0.0, 3.0), ("PASS", "fwd_base", 0.0, 3.0), ("PASS", "fwd_dir", 0.0, 2.5), ("PASS", "recycle", 0.0, 4.0),
          ("PASS", "wide", 0.0, 2.0), ("PASS", "flat", 0.4, 1.0), ("PASS", "dist_base", 2.0, 12.0), ("SHOT", "p", 0.1, 3.0),
          ("SHOT", "finish", 0.6, 1.8), ("PASS", "rw_gk", 0.2, 2.5), ("PASS", "rw_df", 0.4, 2.5), ("PASS", "rw_fw", 0.2, 1.5),
          ("PASS", "acc_zone", 0.0, 3.0), ("DYN", "drift", 0.0, 2.5), ("PASS", "long_base", 0.0, 0.25), ("PASS", "long_dir", 0.0, 0.5),
          ("PASS", "dist_dir", 4.0, 30.0), ("SHAPE", "support", 0.0, 0.6)]


def loss(sim: dict[str, float], real: dict[str, float]) -> float:
    return float(sum(((sim[k] - real[k]) / TOL[k]) ** 2 for k in KEYS))


def show(sim, real):
    print(f"{'metric':<10}{'real':>9}{'sim':>9}")
    for k in KEYS:
        flag = "" if abs(sim[k] - real[k]) <= TOL[k] else "  <-- off"
        print(f"{k:<10}{real[k]:>9.1f}{sim[k]:>9.1f}{flag}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("-n", type=int, default=24)
    args = ap.parse_args()
    real = real_targets()
    if args.fit:
        from scipy.optimize import minimize

        def apply(v):
            for (d, k, lo, hi), x in zip(PARAMS, v):
                getattr(M, d)[k] = float(np.clip(x, lo, hi))

        def f(v):
            apply(v)
            return loss(sim_metrics(args.n), real)

        x0 = [getattr(M, d)[k] for d, k, _, _ in PARAMS]
        print("start loss", round(f(x0), 1), flush=True)
        simplex = [np.array(x0, float)]
        for i, (_, _, lo, hi) in enumerate(PARAMS):  # a wide initial simplex: each parameter moves by 25% of its range
            v = np.array(x0, float)
            v[i] = np.clip(v[i] + 0.25 * (hi - lo), lo, hi) if v[i] + 0.25 * (hi - lo) <= hi else v[i] - 0.25 * (hi - lo)
            simplex.append(v)
        r = minimize(f, x0, method="Nelder-Mead", options={"maxfev": 220, "xatol": 0.01, "fatol": 0.5, "initial_simplex": np.array(simplex)})
        apply(r.x)
        print("final loss", round(r.fun, 1))
        print("PASS =", {k: round(v, 3) for k, v in M.PASS.items()})
        print("SHOT =", {k: round(v, 4) for k, v in M.SHOT.items()})
    show(sim_metrics(max(args.n, 40), seed0=500), real)


if __name__ == "__main__":
    main()
