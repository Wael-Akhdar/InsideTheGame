"""Compare the simulator with real match statistics (Wyscout public dataset, CC BY 4.0).

    python tools/fetch_wyscout.py          # once: download the data into data/external/ (git-ignored)
    python -m gamepulse.calibration        # print real vs simulated aggregates
    python -m gamepulse.calibration --write-doc   # also write docs/CALIBRATION.md (aggregates only)

Only aggregated numbers leave this module: no raw event, player or club name is stored or published.
Cite: Pappalardo et al. (2019), "A public data set of spatio-temporal match events in soccer competitions",
Scientific Data 6:236.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "external" / "wyscout"
CACHE = DATA / "real_stats.json"
LEAGUES = ("France", "Germany", "Italy", "Spain")  # Premier League is left out on purpose
KX, KY = 1.05, 0.68  # pitch coordinates (0-100) -> metres
BINS = ["0-10m", "10-20m", "20-30m", "30-40m", "40-50m", "50m+"]
KEYS = ("passes", "pass_acc", "pass_len", "fwd_share", "shots", "goals", "conv", "fouls")


def _bin(d: float) -> int:
    return min(int(d // 10), 5)


def _summarise(rows: list[dict[str, float]], lens: list[float], bins: dict[int, list[int]]) -> dict[str, Any]:
    n = len(rows)
    tot = lambda k: sum(r[k] for r in rows)
    return {
        "team_matches": n,
        "passes": tot("pass") / n,
        "pass_acc": 100 * tot("pass_ok") / max(1, tot("pass")),
        "pass_len": st.mean(lens) if lens else 0.0,
        "fwd_share": 100 * tot("fwd") / max(1, tot("pass")),
        "shots": tot("shot") / n,
        "goals": tot("goal") / n,
        "conv": 100 * tot("goal") / max(1, tot("shot")),
        "fouls": tot("foul") / n,
        "acc_by_len": {BINS[b]: round(100 * v[1] / v[0]) for b, v in sorted(bins.items()) if v[0]},
    }


def real_stats(use_cache: bool = True) -> dict[str, Any]:
    """Aggregates over the real league matches, overall and for possession-heavy / direct teams."""
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text())
    zf = zipfile.ZipFile(DATA / "events.zip")
    per: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    team_lens: dict[tuple, list[float]] = defaultdict(list)
    lens: list[float] = []
    bins: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for lg in LEAGUES:
        for e in json.loads(zf.read(f"events_{lg}.json")):
            key, c, n = (lg, e["matchId"], e["teamId"]), None, e["eventName"]
            c = per[key]
            if n == "Pass":
                ok = 1801 in {t["id"] for t in e["tags"]}
                c["pass"] += 1
                c["pass_ok"] += ok
                pos = e["positions"]
                if len(pos) == 2 and pos[1]:
                    a, b = pos
                    d = math.hypot((b["x"] - a["x"]) * KX, (b["y"] - a["y"]) * KY)
                    lens.append(d)
                    team_lens[key].append(d)
                    bins[_bin(d)][0] += 1
                    bins[_bin(d)][1] += ok
                    c["fwd"] += (b["x"] - a["x"]) > 5
            elif n == "Shot":
                c["shot"] += 1
                c["goal"] += 101 in {t["id"] for t in e["tags"]}
            elif n == "Foul":
                c["foul"] += 1
    rows = list(per.values())
    out = _summarise(rows, lens, bins)
    # style bands: rank teams (per league season) by their average share of the passes in their matches
    match_total: dict[tuple, float] = defaultdict(float)
    for (lg, m, t), c in per.items():
        match_total[(lg, m)] += c["pass"]
    share: dict[tuple, list[float]] = defaultdict(list)
    for (lg, m, t), c in per.items():
        share[(lg, t)].append(c["pass"] / match_total[(lg, m)])
    ranked = sorted(share, key=lambda k: st.mean(share[k]))
    q = max(1, len(ranked) // 4)
    for label, teams in (("low_possession", ranked[:q]), ("high_possession", ranked[-q:])):
        keys = [k for k in per if (k[0], k[2]) in set(teams)]
        sub_bins: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        sub_lens = [d for k in keys for d in team_lens[k]]
        out[label] = _summarise([per[k] for k in keys], sub_lens, sub_bins)
        out[label]["pass_share"] = 100 * st.mean(st.mean(share[t]) for t in teams)
    CACHE.write_text(json.dumps(out))
    return out


def sim_stats(home: str = "Balanced 4-3-3", away: str = "Balanced 4-3-3", n: int = 100, seed0: int = 0) -> dict[str, Any]:
    """Same aggregates for simulated matches. Returns both teams' rows pooled, plus the home team's pass share."""
    from .simulator.match import MatchSimulator

    rows, lens, shares = [], [], []
    bins: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    home_rows = []
    for s in range(seed0, seed0 + n):
        sim = MatchSimulator(seed=s, home_tactic=home, away_tactic=away, record_frames=False)
        per: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for e in sim.events():
            c = per[e.team]
            if e.type == "pass":
                ok = e.outcome == "success"
                c["pass"] += 1
                c["pass_ok"] += ok
                d = e.meta["distance_m"]
                lens.append(d)
                bins[_bin(d)][0] += 1
                bins[_bin(d)][1] += ok
                c["fwd"] += (e.end_x - e.x) > 5
            elif e.type == "shot":
                c["shot"] += 1
                c["goal"] += e.outcome == "goal"
            elif e.type == "foul":
                c["foul"] += 1
        rows += [per["RVR"], per["NTH"]]
        home_rows.append(per["RVR"])
        shares.append(per["RVR"]["pass"] / max(1, per["RVR"]["pass"] + per["NTH"]["pass"]))
    out = _summarise(rows, lens, bins)
    out["home_pass_share"] = 100 * st.mean(shares)
    out["home"] = _summarise(home_rows, [], defaultdict(lambda: [0, 0]))
    return out


def style_check(n: int = 60) -> dict[str, dict[str, float]]:
    """Possession / balanced / direct style vs a balanced opponent, measured like the real style bands."""
    res = {}
    for label, tactic in (("possession", "Possession 4-3-3"), ("direct", "Direct 4-4-2")):
        s = sim_stats(tactic, "Balanced 4-3-3", n)
        h = s["home"]
        res[label] = {"pass_share": s["home_pass_share"], "pass_acc": h["pass_acc"], "fwd_share": h["fwd_share"],
                      "shots": h["shots"], "passes": h["passes"]}
    return res


TOL = {"pass_acc": 0.04, "pass_len": 0.10, "fwd_share": 0.08, "passes": 0.10, "shots": 0.10, "goals": 0.12, "conv": 0.15, "fouls": 0.12}


def _row(name: str, real: float, sim: float, tol: float) -> str:
    flag = "ok" if abs(sim - real) <= tol * abs(real) else "OFF"
    return f"{name:<22}{real:>10.1f}{sim:>10.1f}   {flag}"


def report(n: int = 100) -> str:
    R, S = real_stats(), sim_stats(n=n)
    lines = [f"Real: {R['team_matches']} team-matches in {', '.join(LEAGUES)} (2017/18).  Simulated: {2 * n} team-matches (Balanced vs Balanced).",
             f"{'metric':<22}{'real':>10}{'sim':>10}", "-" * 46]
    labels = {"passes": "passes / team-match", "pass_acc": "pass accuracy %", "pass_len": "mean pass length (m)",
              "fwd_share": "forward passes %", "shots": "shots", "goals": "goals", "conv": "shot conversion %", "fouls": "fouls"}
    for k in KEYS:
        lines.append(_row(labels[k], R[k], S[k], TOL[k]))
    lines += ["", "pass accuracy by length (%):"]
    lines.append(f"  {'':<8}" + "".join(f"{b:>8}" for b in BINS))
    lines.append(f"  {'real':<8}" + "".join(f"{R['acc_by_len'].get(b, 0):>8}" for b in BINS))
    lines.append(f"  {'sim':<8}" + "".join(f"{S['acc_by_len'].get(b, 0):>8}" for b in BINS))
    hi, lo, sc = R["high_possession"], R["low_possession"], style_check(max(30, n // 2))
    lines += ["", "style bands (real top / bottom quartile of teams by pass share  vs  simulated Possession / Direct preset):",
              f"  {'':<14}{'pass share':>11}{'pass acc':>10}{'fwd %':>8}{'shots':>8}",
              f"  {'real high':<14}{hi['pass_share']:>11.1f}{hi['pass_acc']:>10.1f}{hi['fwd_share']:>8.1f}{hi['shots']:>8.1f}",
              f"  {'sim possession':<14}{sc['possession']['pass_share']:>11.1f}{sc['possession']['pass_acc']:>10.1f}{sc['possession']['fwd_share']:>8.1f}{sc['possession']['shots']:>8.1f}",
              f"  {'real low':<14}{lo['pass_share']:>11.1f}{lo['pass_acc']:>10.1f}{lo['fwd_share']:>8.1f}{lo['shots']:>8.1f}",
              f"  {'sim direct':<14}{sc['direct']['pass_share']:>11.1f}{sc['direct']['pass_acc']:>10.1f}{sc['direct']['fwd_share']:>8.1f}{sc['direct']['shots']:>8.1f}"]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=100, help="simulated matches")
    ap.add_argument("--write-doc", action="store_true")
    args = ap.parse_args()
    text = report(args.n)
    print(text)
    if args.write_doc:
        doc = ROOT / "docs" / "CALIBRATION.md"
        doc.write_text(
            "# Simulator calibration against real match statistics\n\n"
            "Source: Wyscout public soccer match event dataset, licence CC BY 4.0. Pappalardo et al. (2019), "
            "\"A public data set of spatio-temporal match events in soccer competitions\", Scientific Data 6:236, "
            "https://www.nature.com/articles/s41597-019-0247-7. Only aggregated statistics are shown; the raw data is "
            "not part of this repository. Leagues used: " + ", ".join(LEAGUES) + " (2017/18).\n\n"
            "Regenerate with `python tools/fetch_wyscout.py && python -m gamepulse.calibration --write-doc`.\n\n"
            "```\n" + text + "\n```\n")
        print(f"\nwrote {doc}")


if __name__ == "__main__":
    main()
