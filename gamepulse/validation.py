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


def frame_errors(track: TeamTrack, params: dict, line_height: float = 0.5, width: float = 0.5, use_ball: bool = True) -> dict[str, float]:
    """Mean distance (m) between real and predicted positions, in and out of possession."""
    S = _side(track.formation, line_height, width)
    err = {True: [], False: []}
    for pts, b, has in zip(track.real, track.ball, track.has_ball):
        if len(pts) < 8:
            continue
        bx, by = (b[0], b[1]) if use_ball else (50.0, 50.0)
        pred = shape_targets(S, bool(has), float(bx), float(by), params)
        cost = np.hypot(*((pts[:, None, :] - pred[None, :, :]) * KXY).transpose(2, 0, 1))
        r, c = linear_sum_assignment(cost)
        err[bool(has)].append(float(cost[r, c].mean()))
    return {"in": float(np.mean(err[True])) if err[True] else float("nan"), "out": float(np.mean(err[False])) if err[False] else float("nan"),
            "all": float(np.mean(err[True] + err[False]))}


def evaluate(tracks: list[TeamTrack], params: dict, use_ball: bool = True, fit_instructions: bool = False) -> dict[str, float]:
    res = []
    for t in tracks:
        if fit_instructions:  # best line height and width for this team in this match (what a coach would set)
            best = min(((lh, w) for lh in (0.1, 0.3, 0.5, 0.7, 0.9) for w in (0.1, 0.3, 0.5, 0.7, 0.9)),
                       key=lambda p: frame_errors(t, params, p[0], p[1], use_ball)["all"])
            res.append(frame_errors(t, params, best[0], best[1], use_ball))
        else:
            res.append(frame_errors(t, params, use_ball=use_ball))
    return {k: float(np.nanmean([r[k] for r in res])) for k in ("in", "out", "all")}


def fit(train: list[TeamTrack], start: Optional[dict] = None) -> dict:
    """Fit the shape parameters by minimising the mean error on the training teams (Powell, bounded by clipping)."""
    from scipy.optimize import minimize

    names = ["ball_shift_x", "ball_shift_y", "kx_in", "ky_in", "kx_out", "ky_out", "lh_in", "lh_out", "width_base", "width_gain", "support",
             "gk_base", "gk_ball", "ax_scale", "off_df", "off_mf", "off_fw"]
    base = dict(start or SHAPE)
    lo = np.array([0.0, 0.0, 0.2, 0.3, 0.2, 0.3, 0.0, 0.0, 0.5, 0.0, 0.0, 2.0, 0.0, 0.0, -20.0, -20.0, -20.0])
    hi = np.array([1.0, 1.0, 1.2, 1.4, 1.2, 1.4, 30.0, 40.0, 1.3, 0.8, 0.6, 30.0, 0.8, 2.0, 20.0, 20.0, 20.0])

    def objective(v):
        p = dict(base)
        p.update({n: float(x) for n, x in zip(names, np.clip(v, lo, hi))})
        return evaluate(train, p)["all"]

    x0 = np.array([base[n] for n in names])
    r = minimize(objective, x0, method="Powell", options={"maxiter": 4, "xtol": 1e-2, "ftol": 1e-3})
    out = dict(base)
    out.update({n: round(float(x), 3) for n, x in zip(names, np.clip(r.x, lo, hi))})
    return out


DEPTHS = [(10, 20), (20, 33), (33, 50)]  # ball distance from the defending side's goal line (pitch units)


def real_goal_side(tracks: list[TeamTrack]) -> dict[str, float]:
    """Outfield defenders between the ball and their own goal, by depth of the ball, in real tracking (team defending)."""
    out: dict[tuple, list[int]] = {d: [] for d in DEPTHS}
    for t in tracks:
        for pts, b, has in zip(t.real, t.ball, t.has_ball):
            if has or len(pts) < 10:
                continue
            outfield = pts[np.argsort(pts[:, 0])][1:]  # the deepest player is the goalkeeper
            for lo, hi in DEPTHS:
                if lo <= b[0] < hi:
                    out[(lo, hi)].append(int(np.sum(outfield[:, 0] < b[0])))
    return {f"{lo}-{hi}": float(np.mean(v)) for (lo, hi), v in out.items()}


def sim_goal_side(n: int = 4) -> dict[str, float]:
    """Same count in the simulator, taken when the ball carrier decides (Balanced vs Balanced)."""
    from .simulator.match import MatchSimulator

    out: dict[tuple, list[int]] = {d: [] for d in DEPTHS}
    orig = MatchSimulator._step

    def step(self, t, dt, evs):
        P, D = self.sides[self.poss], self.sides[self._other(self.poss)]
        bx = 100 - P.pos[self.c, 0]
        for lo, hi in DEPTHS:
            if lo <= bx < hi:
                out[(lo, hi)].append(int(np.sum(D.active & ~D.gk & (D.pos[:, 0] < bx))))
        return orig(self, t, dt, evs)

    MatchSimulator._step = step
    try:
        for s in range(n):
            for _ in MatchSimulator(seed=s, home_tactic="Balanced 4-3-3", away_tactic="Balanced 4-3-3", record_frames=False).events():
                pass
    finally:
        MatchSimulator._step = orig
    return {f"{lo}-{hi}": float(np.mean(v)) for (lo, hi), v in out.items()}


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
    tracks = load_tracks()
    matches = sorted({t.match for t in tracks})
    print(f"{len(matches)} real matches, {len(tracks)} teams, {sum(t.n_frames for t in tracks)} team-frames (formations: "
          f"{sorted({t.formation for t in tracks})})")
    print(f"{'model':<44}{'in poss.':>10}{'out of poss.':>14}{'all':>8}   (mean error in metres)")
    for label, kw in (("fixed formation shape (ignores the ball)", dict(use_ball=False)), ("ball-aware shape, default instructions", {}),
                      ("ball-aware shape, best line height and width", dict(fit_instructions=True))):
        r = evaluate(tracks, SHAPE, **kw)
        print(f"{label:<44}{r['in']:>10.2f}{r['out']:>14.2f}{r['all']:>8.2f}")
    if args.fit and len(matches) >= 3:
        test_m = set(matches[-max(1, len(matches) // 3):])
        train = [t for t in tracks if t.match not in test_m]
        test = [t for t in tracks if t.match in test_m]
        fitted = fit(train)
        print(f"\nfitted on {len(train)} teams of {len(matches) - len(test_m)} matches, tested on {len(test)} teams of {len(test_m)} unseen matches:")
        for label, p in (("current parameters", SHAPE), ("fitted parameters", fitted)):
            r = evaluate(test, p)
            print(f"{label:<44}{r['in']:>10.2f}{r['out']:>14.2f}{r['all']:>8.2f}")
        print("fitted parameters:", {k: fitted[k] for k in sorted(fitted)})


if __name__ == "__main__":
    main()
