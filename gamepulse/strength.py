"""Team strength: how a gap in level changes a match, in real football and in the simulator.

Real side: a Maher / Dixon-Coles style Poisson model (goals ~ Poisson(exp(mu + home + attack_i - defence_j))) fitted on each league season
of the Wyscout public dataset (CC BY 4.0, Pappalardo et al. 2019). A team's strength is attack + defence, in log-goal units, so the gap
between two teams is the log of the ratio of the goals each is expected to score: a gap of 0.5 means scoring exp(0.5) = 1.65 times as many.
Team-matches are grouped by gap and we record what happens: results, goals, share of the passes, share of the shots, pass accuracy.

Simulator side: squads differ by `quality` (all attributes scaled). The scale between quality and gap is set from goals only; possession,
shots and accuracy are then checked against the real curves (they are not fitted).

    python -m gamepulse.strength            # real curves vs simulated curves
"""
from __future__ import annotations

import argparse
import json
import math
import zipfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from .calibration import DATA, LEAGUES

CACHE = DATA / "real_strength.json"

# Team levels a coach can pick, as strength in log-goal units (attack + defence of the Poisson model). Values are the average fitted
# strength of the team at that league position in the four leagues (2017/18): champion +1.2, 2nd +0.74, 4th +0.54, 6th +0.19, 10th -0.07,
# 15th -0.31, 18th -0.62, 20th -0.89.
LEVELS = {"title": (0.9, "Title contender (1st-2nd)"), "europe": (0.5, "European places (3rd-5th)"), "upper": (0.2, "Upper half (6th-8th)"),
          "mid": (0.0, "Mid-table (9th-12th)"), "lower": (-0.3, "Lower half (13th-16th)"), "relegation": (-0.7, "Relegation battle (17th-20th)")}


def quality_for(level) -> float:
    """Squad quality multiplier for a level name, a strength value (float) or None (mid-table)."""
    from .simulator.match import QUALITY_PER_GAP

    if level is None or level == "":
        s = 0.0
    elif isinstance(level, str) and level in LEVELS:
        s = LEVELS[level][0]
    else:
        try:
            s = max(-1.5, min(1.5, float(level)))
        except (TypeError, ValueError):
            s = 0.0
    return 1.0 + QUALITY_PER_GAP * s
EDGES = [-9, -0.6, -0.3, -0.1, 0.1, 0.3, 0.6, 9]  # gap bins (log-goal units)


def fit_poisson(matches: list[tuple[int, int, int, int]]) -> tuple[dict[int, float], dict[int, float], float, float]:
    """matches: (home, away, home goals, away goals). Returns attack, defence, mu, home advantage (maximum likelihood)."""
    from scipy.optimize import minimize

    teams = sorted({m[0] for m in matches} | {m[1] for m in matches})
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    H = np.array([idx[m[0]] for m in matches])
    A = np.array([idx[m[1]] for m in matches])
    hg = np.array([m[2] for m in matches], float)
    ag = np.array([m[3] for m in matches], float)

    def nll(v):
        att, de, mu, h = v[:n], v[n:2 * n], v[-2], v[-1]
        att = att - att.mean()
        de = de - de.mean()
        lh = mu + h + att[H] - de[A]
        la = mu + att[A] - de[H]
        return float(np.sum(np.exp(lh) - hg * lh) + np.sum(np.exp(la) - ag * la)) + 1e-3 * float(np.sum(v[:2 * n] ** 2))

    r = minimize(nll, np.zeros(2 * n + 2), method="L-BFGS-B")
    att, de = r.x[:n] - r.x[:n].mean(), r.x[n:2 * n] - r.x[n:2 * n].mean()
    return {t: float(att[i]) for t, i in idx.items()}, {t: float(de[i]) for t, i in idx.items()}, float(r.x[-2]), float(r.x[-1])


def _new():
    return defaultdict(float)


def _summ(rows: list[dict]) -> dict[str, float]:
    n = len(rows)
    g = lambda k: float(np.mean([r[k] for r in rows]))
    return {"n": n, "gap": g("gap"), "win": 100 * g("win"), "draw": 100 * g("draw"), "gf": g("gf"), "ga": g("ga"), "pass_share": g("pass_share"),
            "shot_share": g("shot_share"), "pass_acc": g("pass_acc")}


def curves(rows: list[dict]) -> list[dict[str, float]]:
    out = []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        b = [r for r in rows if lo <= r["gap"] < hi]
        if len(b) >= 5:
            out.append(_summ(b))
    return out


def real_rows(use_cache: bool = True) -> dict:
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text())
    mz, ez = zipfile.ZipFile(DATA / "matches.zip"), zipfile.ZipFile(DATA / "events.zip")
    rows, home_adv, spreads = [], {}, {}
    for lg in LEAGUES:
        ms = json.loads(mz.read(f"matches_{lg}.json"))
        res = []
        for m in ms:
            td = m["teamsData"]
            h = next(v for v in td.values() if v["side"] == "home")
            a = next(v for v in td.values() if v["side"] == "away")
            res.append((h["teamId"], a["teamId"], int(h["score"]), int(a["score"]), m["wyId"]))
        att, de, mu, hadv = fit_poisson([r[:4] for r in res])
        home_adv[lg] = hadv
        s = {t: att[t] + de[t] for t in att}
        spreads[lg] = float(np.std(list(s.values())))
        st: dict[tuple, dict] = defaultdict(_new)
        for e in json.loads(ez.read(f"events_{lg}.json")):
            c = st[(e["matchId"], e["teamId"])]
            if e["eventName"] == "Pass":
                c["p"] += 1
                c["ok"] += any(t["id"] == 1801 for t in e["tags"])
            elif e["eventName"] == "Shot":
                c["s"] += 1
        for ht, at, hg, ag, mid in res:
            for me, op, gf, ga, home in ((ht, at, hg, ag, True), (at, ht, ag, hg, False)):
                c, o = st[(mid, me)], st[(mid, op)]
                gap = s[me] - s[op] + (hadv if home else -hadv)  # log ratio of expected goals in this match
                rows.append({"gap": gap, "win": gf > ga, "draw": gf == ga, "gf": gf, "ga": ga,
                             "pass_share": 100 * c["p"] / max(1, c["p"] + o["p"]), "shot_share": 100 * c["s"] / max(1, c["s"] + o["s"]),
                             "pass_acc": 100 * c["ok"] / max(1, c["p"])})
    out = {"rows": rows, "home_adv": home_adv, "strength_sd": spreads}
    CACHE.write_text(json.dumps(out))
    return out


def _sim_job(args):
    from .simulator.match import MatchSimulator

    qh, qa, seeds, home, away = args
    rows = []
    for s in seeds:
        sim = MatchSimulator(seed=s, home_tactic=home, away_tactic=away, record_frames=False, home_quality=qh, away_quality=qa)
        c = {sim.home.id: _new(), sim.away.id: _new()}
        for e in sim.events():
            if e.type == "pass":
                c[e.team]["p"] += 1
                c[e.team]["ok"] += e.outcome == "success"
            elif e.type == "shot":
                c[e.team]["s"] += 1
        h, a = c[sim.home.id], c[sim.away.id]
        gf, ga = sim.score[sim.home.id], sim.score[sim.away.id]
        rows.append({"win": gf > ga, "draw": gf == ga, "gf": gf, "ga": ga, "pass_share": 100 * h["p"] / max(1, h["p"] + a["p"]),
                     "shot_share": 100 * h["s"] / max(1, h["s"] + a["s"]), "pass_acc": 100 * h["ok"] / max(1, h["p"])})
    return rows


def sim_gap_rows(gaps_q: list[float], n: int = 60, home: str = "Balanced 4-3-3", away: str = "Balanced 4-3-3", workers: int = 14) -> dict[float, list[dict]]:
    """Quality gap g: home plays with quality 1 + g/2, away with 1 - g/2. Returns rows per g."""
    jobs, keys = [], []
    for g in gaps_q:
        for k in range(0, n, 10):
            jobs.append((1 + g / 2, 1 - g / 2, list(range(5000 + k, 5000 + min(n, k + 10))), home, away))
            keys.append(g)
    out: dict[float, list[dict]] = defaultdict(list)
    with ProcessPoolExecutor(workers) as ex:
        for g, rows in zip(keys, ex.map(_sim_job, jobs)):
            out[g].extend(rows)
    return out


def report(n: int = 60) -> str:
    from .simulator.match import QUALITY_PER_GAP

    R = real_rows()
    real = curves(R["rows"])
    gaps = [b["gap"] for b in real]
    sim = sim_gap_rows([g * QUALITY_PER_GAP for g in gaps], n)
    lines = [f"Real: {len(R['rows'])} team-matches, gap = expected log-goal ratio from a Poisson model fitted per league "
             f"(home advantage {np.mean(list(R['home_adv'].values())):.2f}, spread of team strengths {np.mean(list(R['strength_sd'].values())):.2f}).",
             f"Simulator: quality gap = {QUALITY_PER_GAP:.3f} x gap, {n} matches per row, Balanced vs Balanced.", "",
             f"{'gap':>6} | {'win %':>11} | {'draw %':>11} | {'goals for':>11} | {'goals ag.':>11} | {'pass share':>11} | {'shot share':>11} | {'pass acc':>11}",
             f"{'':>6} | {'real   sim':>11} | {'real   sim':>11} | {'real   sim':>11} | {'real   sim':>11} | {'real   sim':>11} | {'real   sim':>11} | {'real   sim':>11}"]
    for b, g in zip(real, gaps):
        s = _summ([dict(r, gap=g) for r in sim[g * QUALITY_PER_GAP]])
        cells = [f"{b[k]:>5.1f}{s[k]:>6.1f}" if k not in ("gf", "ga") else f"{b[k]:>5.2f}{s[k]:>6.2f}"
                 for k in ("win", "draw", "gf", "ga", "pass_share", "shot_share", "pass_acc")]
        lines.append(f"{g:>6.2f} | " + " | ".join(cells))
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=60)
    print(report(ap.parse_args().n))
