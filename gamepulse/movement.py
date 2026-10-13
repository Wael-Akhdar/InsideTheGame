"""Compare team shape and movement with real tracking data (Sportec Open DFL dataset, CC BY 4.0).

    python tools/fetch_sportec.py          # once: one match into data/external/sportec/ (git-ignored)
    python -m gamepulse.movement           # real vs simulated team shape

Only aggregated numbers are printed or stored. The raw files contain real player and team names: they never leave data/external/.
Cite: Bassek, Rein, Weber, Memmert (2025), "An integrated dataset of spatiotemporal and event data in elite soccer",
Scientific Data; released under CC BY 4.0 with the authorization of the DFL.
"""
from __future__ import annotations

import argparse
import re
import statistics as st
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "external" / "sportec"
STEP = 25  # real data is 25 Hz: keep one frame per second
FRAME = re.compile(r'<Frame N="(\d+)"[^>]*? X="(-?[\d.]+)" Y="(-?[\d.]+)"[^>]*? S="(-?[\d.]+)"(?:[^>]*BallPossession="(\d)" BallStatus="(\d)")?')
FSET = re.compile(r'<FrameSet GameSection="(\w+)"[^>]*TeamId="([^"]+)" PersonId="([^"]+)"')
METRICS = ("depth", "width", "compactness", "nearest_mate", "support", "centroid_to_ball")


def _shape(x_att: np.ndarray, y: np.ndarray, ball_att: tuple[float, float], with_ball: bool) -> dict[str, float]:
    """Shape of the 10 outfield players of one team (x along the attack direction, metres)."""
    cx, cy = x_att.mean(), y.mean()
    d = np.hypot(x_att[:, None] - x_att[None, :], y[:, None] - y[None, :])
    np.fill_diagonal(d, 1e9)
    to_ball = np.hypot(x_att - ball_att[0], y - ball_att[1])
    return {"depth": float(x_att.max() - x_att.min()), "width": float(y.max() - y.min()),
            "compactness": float(np.hypot(x_att - cx, y - cy).mean()), "nearest_mate": float(d.min(axis=1).mean()),
            "support": float(np.sort(to_ball)[:3].mean()),  # ball to its 3 nearest teammates (passing options)
            "centroid_to_ball": float(np.hypot(cx - ball_att[0], cy - ball_att[1]))}


def _mean(rows: list[dict[str, float]]) -> dict[str, float]:
    return {k: round(st.mean(r[k] for r in rows), 1) for k in METRICS} | {"n_frames": len(rows)}


def real_movement(folder: Path = DATA) -> dict[str, Any]:
    info = ET.parse(next(folder.glob("DFL_02_01_*"))).getroot()
    team_role = {t.attrib["TeamId"]: t.attrib["Role"] for t in info.iter("Team")}
    gk = {p.attrib["PersonId"] for p in info.iter("Player") if p.attrib.get("PlayingPosition") == "TW"}
    pos: dict[tuple, dict[int, tuple[float, float]]] = defaultdict(dict)  # (section, team, person) -> frame -> (x, y)
    ball: dict[str, dict[int, tuple]] = defaultdict(dict)
    dist_m: dict[str, float] = defaultdict(float)
    section = team = person = ""
    with open(next(folder.glob("DFL_04_03_*")), encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("<FrameSet"):
                m = FSET.search(line)
                section, team, person = m.groups()
            elif line.startswith("<Frame "):
                m = FRAME.match(line)
                n, x, y, s = int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
                if team in team_role:
                    dist_m[person] += s / 3.6 / 25.0  # S is in km/h
                if n % STEP:
                    continue
                if team == "BALL":
                    ball[section][n] = (x, y, m.group(5), m.group(6))
                elif team in team_role:
                    pos[(section, team, person)][n] = (x, y)
    rows: dict[str, list] = {"in": [], "out": []}
    for sec, frames in ball.items():
        teams = {t: [p for (s, tt, p) in pos if s == sec and tt == t] for t in team_role}
        direction = {}
        for t, persons in teams.items():
            g = [np.mean([v[0] for v in pos[(sec, t, p)].values()]) for p in persons if p in gk]
            direction[t] = 1 if g and min(g) < 0 else -1  # a keeper in the negative half attacks towards +x
        for n, (bx, by, poss, status) in frames.items():
            if status != "1" or poss not in ("1", "2"):
                continue
            for t, role in team_role.items():
                pts = [pos[(sec, t, p)][n] for p in teams[t] if p not in gk and n in pos[(sec, t, p)]]
                if len(pts) != 10:
                    continue
                arr = np.array(pts)
                d = direction[t]
                has = (poss == "1") == (role == "home")
                rows["in" if has else "out"].append(_shape(arr[:, 0] * d, arr[:, 1], (bx * d, by), has))
    starters = [p for p, km in dist_m.items() if p not in gk and km / 1000 > 6]
    return {"in_possession": _mean(rows["in"]), "out_of_possession": _mean(rows["out"]),
            "km_per_outfield_player": round(st.mean(dist_m[p] / 1000 for p in starters), 1) if starters else None}


def sim_movement(n: int = 20, tactic_name: str = "Balanced 4-2-3-1") -> dict[str, Any]:
    from .simulator.match import MatchSimulator
    from .tactics import Tactic

    tac = Tactic(name=tactic_name, formation="4-2-3-1")
    rows: dict[str, list] = {"in": [], "out": []}
    for s in range(n):
        sim = MatchSimulator(seed=s, home_tactic=tac, away_tactic=tac)
        for tk in sim.ticks():
            f = tk.frame
            if not f or f["off"]:
                continue
            p = np.array(f["p"])
            xm, ym = (p[:, 0] - 50) * 1.05, (p[:, 1] - 50) * 0.68
            bx, by = (f["ball"][0] - 50) * 1.05, (f["ball"][1] - 50) * 0.68
            for side, idx, d in (("RVR", range(1, 11), 1), ("NTH", range(12, 22), -1)):
                ii = list(idx)
                has = f["poss"] == side
                rows["in" if has else "out"].append(_shape(xm[ii] * d, ym[ii], (bx * d, by), has))
    return {"in_possession": _mean(rows["in"]), "out_of_possession": _mean(rows["out"])}


def report(n: int = 20) -> str:
    R, S = real_movement(), sim_movement(n)
    lab = {"depth": "team depth (m)", "width": "team width (m)", "compactness": "mean dist. to centroid (m)",
           "nearest_mate": "nearest teammate (m)", "support": "ball to 3 nearest mates (m)", "centroid_to_ball": "centroid to ball (m)"}
    out = [f"Real: 1 Bundesliga match, 4-2-3-1 vs 4-2-3-1, {R['in_possession']['n_frames'] + R['out_of_possession']['n_frames']} team-frames at 1 Hz.  "
           f"Simulated: {n} matches, Balanced 4-2-3-1 vs itself.",
           f"Real outfield players covered {R['km_per_outfield_player']} km per match (sanity check of the tracking data).", ""]
    for phase in ("in_possession", "out_of_possession"):
        out += [f"{phase.replace('_', ' ')}", f"  {'metric':<30}{'real':>8}{'sim':>8}"]
        for k in METRICS:
            out.append(f"  {lab[k]:<30}{R[phase][k]:>8.1f}{S[phase][k]:>8.1f}")
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=20)
    ap.add_argument("--write-doc", action="store_true")
    args = ap.parse_args()
    text = report(args.n)
    print(text)
    if args.write_doc:
        doc = ROOT / "docs" / "MOVEMENT.md"
        doc.write_text(
            "# Team shape: simulator vs real tracking data\n\n"
            "Source: Sportec Open DFL dataset, Bassek, Rein, Weber, Memmert (2025), \"An integrated dataset of spatiotemporal and event "
            "data in elite soccer\", Scientific Data; CC BY 4.0, released with the authorization of the DFL. One Bundesliga match "
            "(positions of every player at 25 Hz, sampled at 1 Hz). Only aggregated numbers are shown; the raw data and all names stay "
            "outside the repository.\n\n"
            "Caveat: a single match (4-2-3-1 against 4-2-3-1) is a sanity check on orders of magnitude, not a statistical benchmark. "
            "Regenerate with `python tools/fetch_sportec.py && python -m gamepulse.movement --write-doc`.\n\n"
            "```\n" + text + "\n```\n")
        print(f"wrote {doc}")


if __name__ == "__main__":
    main()
