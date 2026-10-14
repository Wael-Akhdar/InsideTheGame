"""Where on the pitch things happen: real matches vs the simulator (the gaps listed in docs/REALISM_FINDINGS.md).

    python -m gamepulse.spatial            # table real vs simulated, with a flag per row
    python -m gamepulse.spatial -n 60      # more simulated matches

Real side: Wyscout public dataset (CC BY 4.0, Pappalardo et al. 2019), aggregates only, cached in data/external/.
Coordinates are in the team frame (own goal at x = 0, attacking towards x = 100).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import zipfile
from collections import defaultdict
from typing import Any

from .calibration import DATA, KX, KY, LEAGUES

CACHE = DATA / "real_spatial.json"
ROLE = {"GK": "GK", "DF": "DF", "MD": "MF", "FW": "FW"}


class Acc:
    """Collects the spatial statistics from a stream of (kind, line, x, y, end_x, end_y, ok, extra) records."""

    def __init__(self):
        self.ys, self.n, self.third_n, self.third_ok = [], 0, [0, 0, 0], [0, 0, 0]
        self.dirs = [0, 0, 0]  # forward, backward, lateral
        self.line = defaultdict(int)
        self.shots = 0
        self.box = 0
        self.shot_d = []
        self.own_third = self.wide = 0

    def add_pass(self, line: str, x: float, y: float, ex: float, ok: bool):
        self.n += 1
        self.ys.append(y)
        self.own_third += x < 33.3
        self.wide += abs(y - 50) > 25
        t = 0 if x < 33.3 else 1 if x < 66.7 else 2
        self.third_n[t] += 1
        self.third_ok[t] += ok
        dx = ex - x
        self.dirs[0 if dx > 5 else 1 if dx < -5 else 2] += 1
        self.line[line] += 1

    def add_shot(self, x: float, y: float):
        self.shots += 1
        d = math.hypot((100 - x) * KX, (50 - y) * KY)
        self.shot_d.append(d)
        self.box += x > 84 and abs(y - 50) < 24

    def summary(self) -> dict[str, float]:
        n = max(1, self.n)
        field = max(1, sum(self.line[k] for k in ("DF", "MF", "FW")))
        return {
            "own_third": 100 * self.own_third / n,
            "y_std": st.pstdev(self.ys) if self.ys else 0.0,
            "wide": 100 * self.wide / n,
            "fwd": 100 * self.dirs[0] / n, "back": 100 * self.dirs[1] / n, "lat": 100 * self.dirs[2] / n,
            "by_DF": 100 * self.line["DF"] / field, "by_MF": 100 * self.line["MF"] / field, "by_FW": 100 * self.line["FW"] / field,
            "acc_own": 100 * self.third_ok[0] / max(1, self.third_n[0]),
            "acc_mid": 100 * self.third_ok[1] / max(1, self.third_n[1]),
            "acc_final": 100 * self.third_ok[2] / max(1, self.third_n[2]),
            "shot_dist": st.mean(self.shot_d) if self.shot_d else 0.0,
            "shots_in_box": 100 * self.box / max(1, self.shots),
        }


def real_spatial(use_cache: bool = True) -> dict[str, float]:
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text())
    roles = {p["wyId"]: ROLE.get(p["role"]["code2"], "MF") for p in json.loads((DATA / "players.json").read_text(encoding="utf-8"))}
    acc = Acc()
    zf = zipfile.ZipFile(DATA / "events.zip")
    for lg in LEAGUES:
        for e in json.loads(zf.read(f"events_{lg}.json")):
            pos, name = e["positions"], e["eventName"]
            if name == "Pass" and len(pos) == 2 and pos[1]:
                ok = any(t["id"] == 1801 for t in e["tags"])
                acc.add_pass(roles.get(e["playerId"], "MF"), pos[0]["x"], pos[0]["y"], pos[1]["x"], ok)
            elif name == "Shot" and pos:
                acc.add_shot(pos[0]["x"], pos[0]["y"])
    out = acc.summary()
    CACHE.write_text(json.dumps(out))
    return out


def sim_spatial(home: str = "Balanced 4-3-3", away: str = "Balanced 4-3-3", n: int = 40, seed0: int = 0) -> dict[str, float]:
    from .simulator.match import MatchSimulator

    acc = Acc()
    for s in range(seed0, seed0 + n):
        sim = MatchSimulator(seed=s, home_tactic=home, away_tactic=away, record_frames=False)
        line = {p.id: p.position for t in sim.teams.values() for p in t.players}
        for e in sim.events():
            if e.type == "pass" and e.end_x is not None:
                acc.add_pass(line.get(e.player, "MF"), e.x, e.y, e.end_x, e.outcome == "success")
            elif e.type == "shot":
                acc.add_shot(e.x, e.y)
    return acc.summary()


ROWS = [  # key, label, tolerance (absolute, in the unit of the row)
    ("own_third", "passes starting in own third %", 4.0), ("y_std", "spread of pass start y (std)", 2.0), ("wide", "passes starting wide %", 5.0),
    ("fwd", "forward passes %", 4.0), ("back", "backward passes %", 4.0), ("lat", "lateral passes %", 4.0),
    ("by_DF", "passes by defenders %", 4.0), ("by_MF", "passes by midfielders %", 4.0), ("by_FW", "passes by forwards %", 3.0),
    ("acc_own", "accuracy, own third %", 3.0), ("acc_mid", "accuracy, middle third %", 3.0), ("acc_final", "accuracy, final third %", 3.0),
    ("shot_dist", "mean shot distance (m)", 1.5), ("shots_in_box", "shots from inside the box %", 6.0)]


def report(n: int = 40) -> str:
    R, S = real_spatial(), sim_spatial(n=n)
    lines = [f"{'metric':<34}{'real':>8}{'sim':>8}", "-" * 56]
    bad = 0
    for k, label, tol in ROWS:
        ok = abs(S[k] - R[k]) <= tol
        bad += not ok
        lines.append(f"{label:<34}{R[k]:>8.1f}{S[k]:>8.1f}   {'ok' if ok else 'OFF'}")
    lines.append(f"\n{len(ROWS) - bad}/{len(ROWS)} within tolerance")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=40)
    print(report(ap.parse_args().n))
