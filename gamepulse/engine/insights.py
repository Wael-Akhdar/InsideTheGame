"""Insights the TV does not show.

A goal is obvious on screen. These detectors look for what is not: a team that dominates without being rewarded, a pressing
that quietly fades, one player through whom the whole game flows, the moment a tactical change or a red card turned the match.

They read ONLY what a real data feed provides: the event stream and the line-ups (`state.roster`). They never look inside the
simulator, so the same code runs on real matches. Every insight carries the ids of the events that justify it.
"""
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from ..models import Event, Moment

if TYPE_CHECKING:  # pragma: no cover
    from .state import MatchState

CHECK_EVERY = 5  # minutes between two sweeps


def _in(events: list[Event], t0: float, t1: float) -> list[Event]:
    return [e for e in events if t0 <= e.clock < t1]


def _xg(events: list[Event], team: str) -> float:
    return sum(e.xg or 0.0 for e in events if e.type == "shot" and e.team == team)


def _ok(state: "MatchState", key: tuple, minute: float, cooldown: float) -> bool:
    """Cooldown so the same insight is not repeated every sweep."""
    last = state.insight_log.get(key)
    if last is not None and minute - last < cooldown:
        return False
    state.insight_log[key] = minute
    return True


def unlucky_dominance(state: "MatchState", m: int) -> list[Moment]:
    """Clearly better in expected goals, yet not winning."""
    out: list[Moment] = []
    if m < 20:
        return out
    for team, opp in ((state.home, state.away), (state.away, state.home)):
        xf, xa = _xg(state.events, team), _xg(state.events, opp)
        diff = state.score[team] - state.score[opp]
        if xf - xa >= 0.8 and diff <= 0 and _ok(state, ("unlucky", team), m, 30):
            shots = [e.id for e in state.events if e.type == "shot" and e.team == team][-8:]
            out.append(Moment("unlucky", m, team, None, min(0.9, 0.6 + 0.1 * (xf - xa)), shots,
                              {"xg_for": round(xf, 2), "xg_against": round(xa, 2), "goal_diff": diff}))
    return out


def pressing_fade(state: "MatchState", m: int) -> list[Moment]:
    """The team's pressing activity has dropped well below its early-match level, and the opponent benefits."""
    out: list[Moment] = []
    if m < 55 or not any(e.type == "pressure" for e in state.events):  # needs a feed that reports pressing
        return out
    press = ("pressure", "tackle")
    for team, opp in ((state.home, state.away), (state.away, state.home)):
        base = [e for e in _in(state.events, 5, 25) if e.team == team and e.type in press]
        now = [e for e in _in(state.events, m - 10, m) if e.team == team and e.type in press]
        b, r = len(base) / 2.0, len(now)  # per 10 minutes (the baseline window is 20 minutes long)
        if b < 8 or r > 0.65 * b:
            continue
        def acc(t0: float, t1: float) -> float:
            ps = [e for e in _in(state.events, t0, t1) if e.team == opp and e.type == "pass"]
            return 100 * sum(e.outcome == "success" for e in ps) / len(ps) if ps else 0.0
        a0, a1 = acc(5, 25), acc(m - 10, m)
        if a1 - a0 >= 2 and _ok(state, ("fade", team), m, 25):  # only if the opponent really gained time on the ball
            ev = [e.id for e in base[-3:]] + [e.id for e in now[-3:]]
            out.append(Moment("pressing_fade", m, team, None, 0.65, ev,
                              {"before": round(b), "now": r, "opp_acc_before": round(a0), "opp_acc_now": round(a1)}))
    return out


def hub_player(state: "MatchState", m: int) -> list[Moment]:
    """One outfield player is involved in a disproportionate share of his team's passing."""
    out: list[Moment] = []
    if m < 20:
        return out
    win = _in(state.events, m - 15, m)
    for team in (state.home, state.away):
        passes = [e for e in win if e.type == "pass" and e.team == team and e.outcome == "success"]
        if len(passes) < 40:
            continue
        inv: Counter[str] = Counter()
        for e in passes:
            if e.player:
                inv[e.player] += 1
            rec = e.meta.get("receiver")
            if rec:
                inv[rec] += 1
        for pid, n in inv.most_common(3):
            if state.roster.get(pid, {}).get("line") == "GK":
                continue
            share = 100 * n / (2 * len(passes))
            if share >= 23 and n >= 24 and _ok(state, ("hub", pid), m, 30):  # real matches: median 16.5%, 95th percentile 22%
                ev = [e.id for e in passes if e.player == pid or e.meta.get("receiver") == pid][-8:]
                out.append(Moment("key_player", m, team, pid, 0.62, ev, {"share": round(share), "involvements": n, "typical": round(100 / 11)}))
            break
    return out


def turning_point(state: "MatchState", m: int) -> list[Moment]:
    """Ten minutes after a tactical change or a red card: did the balance of chances really move?"""
    out: list[Moment] = []
    for ev in state.events:
        if ev.type not in ("tactic_change", "card") or (ev.type == "card" and ev.outcome != "red") or ev.minute < 8:
            continue
        if m < ev.minute + 10 or ("turn", ev.id) in state.insight_log:
            continue
        state.insight_log[("turn", ev.id)] = m
        team = ev.team
        opp = state.away if team == state.home else state.home

        def xgd(t0: float, t1: float) -> float:
            w = _in(state.events, t0, t1)
            return _xg(w, team) - _xg(w, opp)

        before, after = xgd(ev.clock - 10, ev.clock), xgd(ev.clock, ev.clock + 10)
        if abs(after - before) >= 0.25:
            cause = "its tactical change" if ev.type == "tactic_change" else "the red card"
            out.append(Moment("turning_point", m, team, ev.player, 0.8, [ev.id], {"cause": cause, "at": ev.minute,
                                                                                  "before": round(before, 2), "after": round(after, 2)}))
    return out


DETECTORS = (unlucky_dominance, pressing_fade, hub_player, turning_point)


def detect(state: "MatchState", minute: int) -> list[Moment]:
    found: list[Moment] = []
    for d in DETECTORS:
        found.extend(d(state, minute))
    return found
