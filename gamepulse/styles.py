"""Do different tactics produce different games? Real teams' style spread vs the spread across simulated tactics.

    python -m gamepulse.styles            # table: real teams p10/p90 vs simulated tactics p10/p90, per metric

Real side: Wyscout public dataset (CC BY 4.0, Pappalardo et al. 2019): 78 teams of four leagues, each team's season average over
its matches (aggregates only, cached in data/external/). Simulated side: random tactics (all five instructions drawn between
0.05 and 0.95) against a balanced opponent. A style space that is too narrow shows as a simulated range smaller than the real one.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics as st
import zipfile
from collections import defaultdict

import numpy as np

from .calibration import DATA, KX, KY, LEAGUES

CACHE = DATA / "real_styles.json"
METRICS = [("pass_share", "share of all passes %"), ("passes", "passes per match"), ("pass_acc", "pass accuracy %"), ("fwd", "forward passes %"),
           ("own_third", "passes starting in own third %"), ("start_x", "mean pass start x (0-100)"), ("pass_len", "mean pass length (m)"),
           ("shots", "shots per match")]


def _row(c: dict) -> dict:
    n = max(1, c["passes"])
    return {"passes": c["passes"], "pass_acc": 100 * c["ok"] / n, "fwd": 100 * c["fwd"] / n, "own_third": 100 * c["own"] / n,
            "start_x": c["sx"] / n, "pass_len": c["len"] / n, "shots": c["shots"]}


def _new() -> dict:
    return defaultdict(float)


def real_styles(use_cache: bool = True) -> dict[str, list[float]]:
    """metric -> season averages of every team (one value per team)."""
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text())
    zf = zipfile.ZipFile(DATA / "events.zip")
    per: dict[tuple, dict] = defaultdict(_new)
    for lg in LEAGUES:
        for e in json.loads(zf.read(f"events_{lg}.json")):
            key, name, pos = (lg, e["matchId"], e["teamId"]), e["eventName"], e["positions"]
            c = per[key]
            if name == "Pass" and len(pos) == 2 and pos[1]:
                a, b = pos
                c["passes"] += 1
                c["ok"] += any(t["id"] == 1801 for t in e["tags"])
                c["fwd"] += (b["x"] - a["x"]) > 5
                c["own"] += a["x"] < 33.3
                c["sx"] += a["x"]
                c["len"] += math.hypot((b["x"] - a["x"]) * KX, (b["y"] - a["y"]) * KY)
            elif name == "Shot":
                c["shots"] += 1
    tot: dict[tuple, float] = defaultdict(float)
    for (lg, m, t), c in per.items():
        tot[(lg, m)] += c["passes"]
    team: dict[tuple, list[dict]] = defaultdict(list)
    for (lg, m, t), c in per.items():
        r = _row(c)
        r["pass_share"] = 100 * c["passes"] / max(1.0, tot[(lg, m)])
        team[(lg, t)].append(r)
    out = {k: [st.mean(r[k] for r in rows) for rows in team.values() if len(rows) >= 20] for k, _ in METRICS}
    CACHE.write_text(json.dumps(out))
    return out


def random_tactic(rng: random.Random):
    from .tactics import Tactic

    return Tactic(name="rnd", formation=rng.choice(["4-3-3", "4-4-2", "4-2-3-1", "3-5-2", "5-3-2"]),
                  **{k: rng.uniform(0.05, 0.95) for k in ("line_height", "pressing", "width", "tempo", "directness")})


def sim_styles(n_tactics: int = 40, matches: int = 6, seed: int = 0) -> dict[str, list[float]]:
    """metric -> value for each random tactic (average over `matches` matches against a balanced opponent)."""
    from .simulator.match import MatchSimulator

    rng = random.Random(seed)
    out: dict[str, list[float]] = {k: [] for k, _ in METRICS}
    for i in range(n_tactics):
        tac = random_tactic(rng)
        rows, shares = [], []
        for s in range(matches):
            sim = MatchSimulator(seed=1000 + i * 17 + s, home_tactic=tac, away_tactic="Balanced 4-3-3", record_frames=False)
            c = {sim.home.id: _new(), sim.away.id: _new()}
            for e in sim.events():
                if e.type == "pass" and e.end_x is not None:
                    k = c[e.team]
                    k["passes"] += 1
                    k["ok"] += e.outcome == "success"
                    k["fwd"] += (e.end_x - e.x) > 5
                    k["own"] += e.x < 33.3
                    k["sx"] += e.x
                    k["len"] += e.meta["distance_m"]
                elif e.type == "shot":
                    c[e.team]["shots"] += 1
            h = c[sim.home.id]
            rows.append(_row(h))
            shares.append(100 * h["passes"] / max(1.0, h["passes"] + c[sim.away.id]["passes"]))
        for k, _ in METRICS:
            out[k].append(float(np.mean(shares if k == "pass_share" else [r[k] for r in rows])))
    return out


def report(n_tactics: int = 40, matches: int = 6) -> str:
    R, S = real_styles(), sim_styles(n_tactics, matches)
    lines = [f"Real: {len(R['passes'])} teams (season averages). Simulated: {n_tactics} random tactics x {matches} matches vs a balanced opponent.",
             f"{'metric':<32}{'real p10':>9}{'p90':>8}{'sim p10':>10}{'p90':>8}  {'range ratio':>11}", "-" * 82]
    for k, label in METRICS:
        r10, r90 = np.percentile(R[k], [10, 90])
        s10, s90 = np.percentile(S[k], [10, 90])
        ratio = (s90 - s10) / max(1e-9, r90 - r10)
        lines.append(f"{label:<32}{r10:>9.1f}{r90:>8.1f}{s10:>10.1f}{s90:>8.1f}  {ratio:>10.2f}x {'ok' if ratio >= 0.8 else 'TOO NARROW'}")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tactics", type=int, default=40)
    ap.add_argument("--matches", type=int, default=6)
    a = ap.parse_args()
    print(report(a.tactics, a.matches))
