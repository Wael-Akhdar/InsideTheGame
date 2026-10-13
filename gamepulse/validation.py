"""Validate the positioning model of the simulator frame by frame against real tracking data (Sportec Open DFL, CC BY 4.0).

How it works (this is "replaying a real match" at the level where ground truth exists):
  1. Take a real frame: where the ball is, which team has it, and where the 22 players really stand.
  2. Give our positioning model ONLY what it is allowed to know: the team's formation (from the line-up), the ball and who has it.
  3. It predicts where the 11 players should stand. Each real player is matched to the closest predicted slot (optimal assignment,
     so shirt numbers and roles do not matter) and we measure the distance in metres.
  4. Repeat over thousands of frames, with teams, formations and matches that were NOT used to fit the model's few parameters.
A model that ignores the ball (a fixed formation shape) is the baseline: the model must beat it.

    python -m gamepulse.validation            # error of the current model on every downloaded match
    python -m gamepulse.validation --fit      # fit the shape parameters on some matches, test on the others
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.optimize import linear_sum_assignment

from .feed.sportec import SportecFeed, available_matches
from .simulator.match import SHAPE, _Side, shape_targets
from .simulator.teams import build_team
from .tactics import Tactic, get_formation

KXY = np.array([1.05, 0.68])


@dataclass
class TeamTrack:
    match: str
    side: str
    formation: str
    real: list[np.ndarray]  # per frame: (n, 2) positions in the team frame
    ball: np.ndarray  # (frames, 2) team frame
    has_ball: np.ndarray  # (frames,) bool
    n_frames: int


def load_tracks(step_frames: int = 3) -> list[TeamTrack]:
    """One TeamTrack per team and downloaded match (every `step_frames`-th 2-second frame)."""
    tracks: list[TeamTrack] = []
    for mid in available_matches():
        feed = SportecFeed(match=mid)
        for k, side in enumerate(("HOM", "AWY")):
            formation = feed.lineups.get(side, "")
            if get_formation(formation) is None:
                continue
            real, ball, has = [], [], []
            for fr in feed.frames[::step_frames]:
                pts = np.array(fr["p"][k * 11:(k + 1) * 11])
                ids = fr["ids"][k * 11:(k + 1) * 11]
                pts = pts[[bool(i) for i in ids]]
                b = np.array(fr["ball"])
                if side == "AWY":
                    pts, b = 100 - pts, 100 - b
                real.append(pts)
                ball.append(b)
                has.append(fr["poss"] == side)
            tracks.append(TeamTrack(mid, side, formation, real, np.array(ball), np.array(has), len(real)))
    return tracks


_SIDES: dict[tuple, _Side] = {}


def _side(formation: str, line_height: float = 0.5, width: float = 0.5) -> _Side:
    key = (formation, round(line_height, 3), round(width, 3))
    if key not in _SIDES:
        _SIDES[key] = _Side(build_team("RVR", Tactic(formation=formation, line_height=line_height, width=width)))
    return _SIDES[key]


def _shape_stats(pts_m: np.ndarray, ball_m: np.ndarray) -> tuple[float, float, float, float, float]:
    """Depth, width, mean distance to the centroid, ball to its 3 nearest outfield players, centroid to ball (metres)."""
    c = pts_m.mean(0)
    to_ball = np.hypot(*(pts_m - ball_m).T)
    return (float(np.ptp(pts_m[:, 0])), float(np.ptp(pts_m[:, 1])), float(np.hypot(*(pts_m - c).T).mean()),
            float(np.sort(to_ball)[:3].mean()), float(np.hypot(*(c - ball_m))))


def frame_errors(track: TeamTrack, params: dict, line_height: float = 0.5, width: float = 0.5, use_ball: bool = True) -> dict[str, float]:
    """Placement error (m) between real and predicted positions, plus how well the team SHAPE matches on average.

    Placement error alone rewards shrinking every prediction towards the ball (a safe average), so the model is also judged on
    team depth, width and compactness: |mean predicted - mean real| over the frames of each phase."""
    S = _side(track.formation, line_height, width)
    err = {True: [], False: []}
    shape = {True: ([], []), False: ([], [])}  # per phase: (real stats, predicted stats)
    for pts, b, has in zip(track.real, track.ball, track.has_ball):
        if len(pts) < 11:
            continue
        bx, by = (b[0], b[1]) if use_ball else (50.0, 50.0)
        pred = shape_targets(S, bool(has), float(bx), float(by), params)
        cost = np.hypot(*((pts[:, None, :] - pred[None, :, :]) * KXY).transpose(2, 0, 1))
        r, c = linear_sum_assignment(cost)
        err[bool(has)].append(float(cost[r, c].mean()))
        out = c != 0  # slot 0 is the goalkeeper
        shape[bool(has)][0].append(_shape_stats(pts[r[out]] * KXY, np.array([bx, by]) * KXY))
        shape[bool(has)][1].append(_shape_stats(pred[c[out]] * KXY, np.array([bx, by]) * KXY))
    gaps = []
    for ph in (True, False):
        if shape[ph][0]:
            gaps += list(np.abs(np.mean(shape[ph][0], axis=0) - np.mean(shape[ph][1], axis=0)))
    return {"in": float(np.mean(err[True])) if err[True] else float("nan"), "out": float(np.mean(err[False])) if err[False] else float("nan"),
            "all": float(np.mean(err[True] + err[False])), "shape_gap": float(np.mean(gaps)) if gaps else float("nan")}


def evaluate(tracks: list[TeamTrack], params: dict, use_ball: bool = True, fit_instructions: bool = False) -> dict[str, float]:
    res = []
    for t in tracks:
        if fit_instructions:  # best line height and width for this team in this match (what a coach would set)
            best = min(((lh, w) for lh in (0.1, 0.3, 0.5, 0.7, 0.9) for w in (0.1, 0.3, 0.5, 0.7, 0.9)),
                       key=lambda p: frame_errors(t, params, p[0], p[1], use_ball)["all"])
            res.append(frame_errors(t, params, best[0], best[1], use_ball))
        else:
            res.append(frame_errors(t, params, use_ball=use_ball))
    return {k: float(np.nanmean([r[k] for r in res])) for k in ("in", "out", "all", "shape_gap")}


FIXED = {"lh_in", "lh_out", "width_gain", "support"}  # coach-facing instructions keep their meaning: not fitted


def _bounds(name: str) -> tuple[float, float]:
    if name.startswith(("kx_", "ky_")):
        return 0.2, 1.4
    if name.startswith(("follow_", "gy_")):
        return 0.0, 1.0
    if name.startswith("off_"):
        return -15.0, 15.0
    return {"gk_base": (2.0, 30.0), "gk_ball": (0.0, 0.8), "ax_scale": (0.0, 2.0), "width_base": (0.5, 1.3)}[name]


def fit(train: list[TeamTrack], start: Optional[dict] = None, maxiter: int = 25) -> dict:
    """Fit the shape parameters by minimising the mean placement error on the training teams (L-BFGS-B, bounded)."""
    from scipy.optimize import minimize

    base = dict(start or SHAPE)
    names = [n for n in base if n not in FIXED]
    lo, hi = zip(*(_bounds(n) for n in names))

    def objective(v):
        p = dict(base)
        p.update({n: float(x) for n, x in zip(names, v)})
        r = evaluate(train, p)
        return r["all"] + r["shape_gap"]  # placement error and shape fidelity count the same

    x0 = np.clip([base[n] for n in names], lo, hi)
    r = minimize(objective, x0, method="L-BFGS-B", bounds=list(zip(lo, hi)), options={"maxiter": maxiter, "eps": 1e-2})
    out = dict(base)
    out.update({n: round(float(x), 3) for n, x in zip(names, r.x)})
    return out


def cross_validate(tracks: list[TeamTrack], folds: int = 3) -> tuple[float, float, dict]:
    """Leave-matches-out: fit on the other matches, measure on the held-out ones. Returns (current, fitted, final fit on everything)."""
    matches = sorted({t.match for t in tracks})
    cur, fit_err, w = [], [], []
    for f in range(folds):
        held = set(matches[f::folds])
        train = [t for t in tracks if t.match not in held]
        test = [t for t in tracks if t.match in held]
        if not train or not test:
            continue
        params = fit(train)
        a, b = evaluate(test, SHAPE), evaluate(test, params)
        cur.append(a["all"] + a["shape_gap"])
        fit_err.append(b["all"] + b["shape_gap"])
        w.append(len(test))
        print(f"  fold {f + 1}: held-out {sorted(m[-6:] for m in held)}  placement {a['all']:.2f} -> {b['all']:.2f} m, shape gap {a['shape_gap']:.2f} -> {b['shape_gap']:.2f} m", flush=True)
    return float(np.average(cur, weights=w)), float(np.average(fit_err, weights=w)), fit(tracks)


# ---------------------------------------------------------------------------------------------------------------- outcomes
def real_team_stats(feed: SportecFeed) -> dict[str, dict[str, float]]:
    """Per-team aggregates of a real match (from the events and the ball-possession flag of the frames)."""
    out = {s: {"passes": 0, "pass_ok": 0, "shots": 0, "xg": 0.0, "goals": 0, "fouls": 0, "tackles": 0, "len_sum": 0.0, "fwd": 0} for s in ("HOM", "AWY")}
    for tk in feed.ticks():
        for e in tk.events:
            o = out[e.team]
            if e.type == "pass":
                o["passes"] += 1
                o["pass_ok"] += e.outcome == "success"
                o["len_sum"] += e.meta.get("distance_m", 0.0)
                o["fwd"] += bool(e.meta.get("forward"))
            elif e.type == "shot":
                o["shots"] += 1
                o["xg"] += e.xg or 0.0
            elif e.type == "goal":
                o["goals"] += 1
            elif e.type == "foul":
                o["fouls"] += 1
            elif e.type == "tackle":
                o["tackles"] += 1
    poss = [fr["poss"] for fr in feed.frames]
    for s in out:
        o = out[s]
        o["pass_acc"] = 100 * o["pass_ok"] / max(1, o["passes"])
        o["pass_len"] = o["len_sum"] / max(1, o["passes"])
        o["fwd_share"] = 100 * o["fwd"] / max(1, o["passes"])
        o["possession"] = 100 * poss.count(s) / max(1, len(poss))
    return out


MACRO = ("passes", "pass_acc", "pass_len", "fwd_share", "shots", "goals", "fouls", "possession")


def macro_check(n: int = 60) -> None:
    """Where does each real team-match fall inside the distribution of simulated matches played with the same formations?

    A stochastic simulator cannot reproduce one particular match, but real matches should look *typical* for it: a real value
    inside the 5th-95th percentile band of `n` simulated matches is a pass. Instructions are neutral (balanced), so a miss can also
    mean that the real team played an extreme style, not only that the simulator is off."""
    from .simulator.match import MatchSimulator

    hits = total = 0
    print(f"{'match':<14}{'team':<5}" + "".join(f"{m:>11}" for m in MACRO))
    for mid in available_matches():
        feed = SportecFeed(match=mid)
        real = real_team_stats(feed)
        ht, at = (Tactic(formation=f if get_formation(f) else "4-3-3") for f in (feed.lineups["HOM"], feed.lineups["AWY"]))
        sims = {"HOM": [], "AWY": []}
        for seed in range(n):
            sim = MatchSimulator(seed=seed, home_tactic=ht, away_tactic=at, record_frames=False)
            c = {s: {"passes": 0, "pass_ok": 0, "shots": 0, "goals": 0, "fouls": 0, "len": 0.0, "fwd": 0} for s in ("RVR", "NTH")}
            for e in sim.events():
                o = c[e.team]
                if e.type == "pass":
                    o["passes"] += 1
                    o["pass_ok"] += e.outcome == "success"
                    o["len"] += e.meta["distance_m"]
                    o["fwd"] += (e.end_x - e.x) > 3
                elif e.type in ("shot", "goal", "foul"):
                    o[{"shot": "shots", "goal": "goals", "foul": "fouls"}[e.type]] += 1
            tot_poss = sum(sim.poss_time.values())
            for k, s in (("RVR", "HOM"), ("NTH", "AWY")):
                o = c[k]
                sims[s].append({"passes": o["passes"], "pass_acc": 100 * o["pass_ok"] / max(1, o["passes"]), "pass_len": o["len"] / max(1, o["passes"]),
                                "fwd_share": 100 * o["fwd"] / max(1, o["passes"]), "shots": o["shots"], "goals": o["goals"], "fouls": o["fouls"],
                                "possession": 100 * sim.poss_time[k] / tot_poss})
        for s in ("HOM", "AWY"):
            row = f"{mid[-6:]:<14}{s:<5}"
            for m in MACRO:
                vals = np.array([x[m] for x in sims[s]])
                pct = 100 * float((vals < real[s][m]).mean() + 0.5 * (vals == real[s][m]).mean())
                ok = 5 <= pct <= 95
                hits += ok
                total += 1
                row += f"{real[s][m]:>7.1f}{'' if ok else '*':<1}{pct:>3.0f}%"
            print(row)
    print(f"\n{hits}/{total} real values inside the 5-95% band of the simulated matches (a calibrated model gives about 90%). "
          "Format: real value, then its percentile among simulated matches; * = outside the band.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit", action="store_true", help="fit on the first matches, test on the others")
    ap.add_argument("--macro", action="store_true", help="place each real team-match inside the distribution of simulated matches")
    args = ap.parse_args()
    if args.macro:
        macro_check()
        return
    tracks = load_tracks(step_frames=6 if args.fit else 3)
    matches = sorted({t.match for t in tracks})
    print(f"{len(matches)} real matches, {len(tracks)} teams, {sum(t.n_frames for t in tracks)} team-frames (formations: "
          f"{sorted({t.formation for t in tracks})})")
    print(f"{'model':<44}{'in poss.':>10}{'out of poss.':>14}{'all':>8}{'shape gap':>11}   (metres)")
    for label, kw in (("fixed formation shape (ignores the ball)", dict(use_ball=False)), ("ball-aware shape, default instructions", {}),
                      ("ball-aware shape, best line height and width", dict(fit_instructions=True))):
        r = evaluate(tracks, SHAPE, **kw)
        print(f"{label:<44}{r['in']:>10.2f}{r['out']:>14.2f}{r['all']:>8.2f}{r['shape_gap']:>11.2f}")
    if args.fit and len(matches) >= 3:
        print("\ncross-validation (each fold: fit on the other matches, test on unseen ones):")
        cur, fitted_err, final = cross_validate(tracks)
        print(f"held-out objective (placement error + shape gap): current {cur:.2f} m -> fitted {fitted_err:.2f} m")
        print("final parameters fitted on all matches:")
        print(json.dumps({k: final[k] for k in sorted(final)}, indent=1))
        fin = evaluate(tracks, final)
        print(f"final parameters on all matches (optimistic, not held out): placement {fin['all']:.2f} m, shape gap {fin['shape_gap']:.2f} m")


if __name__ == "__main__":
    main()
