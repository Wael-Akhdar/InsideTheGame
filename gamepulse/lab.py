"""Tactic Lab: stress-test a coach's tactic against many opponent tactics over many simulated matches."""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from .simulator.match import MatchSimulator
from .tactics import PRESETS, Tactic, resolve_tactic

HOME, AWAY = "RVR", "NTH"


def play_one(args: tuple[dict, dict, int, bool]) -> dict[str, Any]:
    """Simulate one match headlessly. `mine_home` says which side the coach's tactic plays on."""
    mine, other, seed, mine_home = args
    h, a = (mine, other) if mine_home else (other, mine)
    sim = MatchSimulator(seed=seed, home_tactic=h, away_tactic=a, record_frames=False)
    me, op = (HOME, AWAY) if mine_home else (AWAY, HOME)
    m = {k: 0.0 for k in ("gf", "ga", "xgf", "xga", "shf", "sha", "pass_f", "pass_ok_f", "pass_a", "tackles_f", "press_f",
                          "fouls_f", "late_ga", "late_gf", "red_f")}
    for e in sim.events():
        mine_ev = e.team == me
        if e.type == "shot":
            m["shf" if mine_ev else "sha"] += 1
            m["xgf" if mine_ev else "xga"] += e.xg or 0
        elif e.type == "goal":
            m["gf" if mine_ev else "ga"] += 1
            if e.minute >= 60:
                m["late_gf" if mine_ev else "late_ga"] += 1
        elif e.type == "pass":
            if mine_ev:
                m["pass_f"] += 1
                m["pass_ok_f"] += e.outcome == "success"
            else:
                m["pass_a"] += 1
        elif e.type == "tackle" and mine_ev:
            m["tackles_f"] += 1
        elif e.type == "pressure" and mine_ev:
            m["press_f"] += 1
        elif e.type == "foul" and mine_ev:
            m["fouls_f"] += 1
        elif e.type == "card" and mine_ev:
            m["red_f"] += 1
    tot = sim.poss_time[me] + sim.poss_time[op]
    m["poss"] = 100 * sim.poss_time[me] / tot
    return m


def _aggregate(name: str, rows: list[dict[str, float]]) -> dict[str, Any]:
    n = len(rows)
    avg = lambda k: sum(r[k] for r in rows) / n
    w = sum(r["gf"] > r["ga"] for r in rows)
    d = sum(r["gf"] == r["ga"] for r in rows)
    ga_tot, gf_tot = sum(r["ga"] for r in rows), sum(r["gf"] for r in rows)
    return {
        "opponent": name, "matches": n,
        "win": round(100 * w / n), "draw": round(100 * d / n), "loss": round(100 * (n - w - d) / n),
        "ppg": round((3 * w + d) / n, 2),
        "gf": round(avg("gf"), 2), "ga": round(avg("ga"), 2),
        "xgf": round(avg("xgf"), 2), "xga": round(avg("xga"), 2),
        "shots_for": round(avg("shf"), 1), "shots_against": round(avg("sha"), 1),
        "possession": round(avg("poss"), 1),
        "pass_acc": round(100 * sum(r["pass_ok_f"] for r in rows) / max(1, sum(r["pass_f"] for r in rows)), 1),
        "ppda": round(avg("pass_a") / max(1.0, avg("tackles_f") + avg("press_f") + avg("fouls_f")), 1),
        "late_ga_share": round(100 * sum(r["late_ga"] for r in rows) / ga_tot) if ga_tot else 0,
        "late_gf_share": round(100 * sum(r["late_gf"] for r in rows) / gf_tot) if gf_tot else 0,
        "red_cards": round(avg("red_f"), 2),
    }


def evaluate(tactic: Any, opponents: list[Any] | None = None, n: int = 20, base_seed: int = 1000,
             workers: int | None = None) -> dict[str, Any]:
    """Play `n` matches (half at home, half away) against each opponent and summarise."""
    mine: Tactic = resolve_tactic(tactic)
    opps = [resolve_tactic(o) for o in (opponents or [p for p in PRESETS.values() if p.name != mine.name])]
    jobs, owners = [], []
    for oi, o in enumerate(opps):
        for k in range(n):
            jobs.append((mine.to_dict(), o.to_dict(), base_seed + oi * 10_000 + k, k % 2 == 0))
            owners.append(oi)
    workers = workers or min(os.cpu_count() or 2, 8)
    if workers > 1 and len(jobs) > 8:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(play_one, jobs, chunksize=4))
    else:
        results = [play_one(j) for j in jobs]
    per = [_aggregate(o.name, [r for r, ow in zip(results, owners) if ow == oi]) for oi, o in enumerate(opps)]
    overall_ppg = round(sum(p["ppg"] for p in per) / len(per), 2)
    worst = min(per, key=lambda p: p["ppg"])
    best = max(per, key=lambda p: p["ppg"])
    return {
        "tactic": mine.to_dict(), "n": n, "overall_ppg": overall_ppg,
        "robustness": round(100 * overall_ppg / 3),  # 0-100: share of the maximum points per game
        "worst": worst["opponent"], "best": best["opponent"], "matchups": per,
        "insights": insights(mine, per),
    }


def insights(t: Tactic, per: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Rule-based explanations of *why* the tactic holds or breaks (an LLM analyst can rephrase these)."""
    out: list[dict[str, str]] = []
    opp_by_name = {p.name: p for p in PRESETS.values()}
    worst = min(per, key=lambda p: p["ppg"])
    if worst["ppg"] < 1.2:
        out.append({"level": "bad", "text": f"Weakest matchup: {worst['opponent']} ({worst['ppg']} pts/game, "
                                             f"xG {worst['xgf']} for vs {worst['xga']} against)."})
    for p in per:
        o = opp_by_name.get(p["opponent"])
        if o and t.line_height > 0.65 and o.directness > 0.7 and p["xga"] - p["xgf"] > 0.4:
            out.append({"level": "bad", "text": f"Your high line is exposed by {p['opponent']}'s direct play "
                                                 f"(conceding {p['xga']} xG). Drop the line or use cover / ball-playing centre-backs."})
            break
    avg_late = sum(p["late_ga_share"] for p in per) / len(per)
    if t.pressing > 0.7 and avg_late > 50:
        out.append({"level": "warn", "text": f"{round(avg_late)}% of goals conceded come after the 60th minute: heavy pressing burns "
                                              f"stamina. Lower pressing intensity or press in waves."})
    avg_poss = sum(p["possession"] for p in per) / len(per)
    avg_xgf = sum(p["xgf"] for p in per) / len(per)
    if avg_poss > 55 and avg_xgf < 1.0:
        out.append({"level": "warn", "text": f"Sterile possession ({round(avg_poss)}% of the ball, only {avg_xgf:.2f} xG per match). "
                                              f"Raise directness or add a shadow striker / inside forwards."})
    if t.pressing < 0.35 and any(p["ppda"] > 14 for p in per):
        out.append({"level": "warn", "text": "Opponents build up almost untouched (very high PPDA). A medium press from the forwards would force errors."})
    if sum(p["red_cards"] for p in per) / len(per) > 0.06:
        out.append({"level": "warn", "text": "Aggressive pressing is costing red cards; consider a calmer defensive line."})
    best = max(per, key=lambda p: p["ppg"])
    out.append({"level": "good", "text": f"Best matchup: {best['opponent']} ({best['ppg']} pts/game)."})
    return out
