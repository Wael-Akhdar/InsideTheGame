"""Live match state: aggregates events into stats, momentum and key moments."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

from ..models import Event, Moment

WINDOW_MIN = 5.0  # rolling window for momentum / pressure
BIG_CHANCE_XG = 0.35

# weight of each event type in the momentum score
_MOMENTUM_W = {"shot": 3.0, "pass_final_third": 0.6, "pressure": 0.5, "tackle_won": 0.8, "goal": 5.0}


def pass_difficulty(ev: Event) -> float:
    """Pass difficulty rating 0..10 from distance, direction, zone and ball speed."""
    dist = ev.meta.get("distance_m", 0.0)
    score = min(dist / 40, 1.0) * 4.0
    if ev.end_x is not None and ev.x is not None:
        score += max(0.0, (ev.end_x - ev.x)) / 35 * 2.5  # progressive passes are harder
        if ev.end_x > 78:
            score += 2.0  # into the box
    if ev.speed_kmh:
        score += min(ev.speed_kmh / 95, 1.0) * 1.5
    return round(min(score, 10.0), 1)


@dataclass
class TeamStats:
    passes: int = 0
    passes_ok: int = 0
    shots: int = 0
    on_target: int = 0
    xg: float = 0.0
    tackles: int = 0
    tackles_won: int = 0
    pressures: int = 0
    fouls: int = 0
    possession_events: int = 0

    @property
    def pass_acc(self) -> float:
        return round(100 * self.passes_ok / self.passes, 1) if self.passes else 0.0


@dataclass
class MatchState:
    home: str
    away: str
    events: list[Event] = field(default_factory=list)
    score: dict[str, int] = field(default_factory=dict)
    stats: dict[str, TeamStats] = field(default_factory=dict)
    player_stats: dict[str, dict[str, float]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(float)))
    moments: list[Moment] = field(default_factory=list)
    minute: int = 0
    poss_time: dict[str, float] = field(default_factory=dict)
    _last_t: float = 0.0
    _window: deque = field(default_factory=deque)
    _momentum_hist: list[tuple[float, float]] = field(default_factory=list)  # (clock, home-away)
    _last_swing_clock: float = -99.0
    _last_pressure_clock: float = -99.0

    def __post_init__(self):
        self.score = {self.home: 0, self.away: 0}
        self.stats = {self.home: TeamStats(), self.away: TeamStats()}
        self.poss_time = {self.home: 0.0, self.away: 0.0}

    # ------------------------------------------------------------ ingestion
    def ingest(self, ev: Event) -> list[Moment]:
        """Update state with one event, return any new key moments it triggered."""
        self.events.append(ev)
        self.minute = ev.minute
        st = self.stats.get(ev.team)
        ps = self.player_stats[ev.player] if ev.player else None
        new: list[Moment] = []

        if ev.type == "pass" and st:
            st.passes += 1
            st.passes_ok += ev.outcome == "success"
            ev.meta["difficulty"] = pass_difficulty(ev)
            if ps is not None:
                ps["passes"] += 1
                ps["passes_ok"] += ev.outcome == "success"
                ps["pass_difficulty_sum"] += ev.meta["difficulty"]
        elif ev.type == "shot" and st:
            st.shots += 1
            st.on_target += ev.outcome in ("goal", "saved")
            st.xg += ev.xg or 0
            if ps is not None:
                ps["shots"] += 1
                ps["xg"] += ev.xg or 0
            if (ev.xg or 0) >= BIG_CHANCE_XG and ev.outcome != "goal":
                new.append(Moment("big_chance", ev.minute, ev.team, ev.player, min(1.0, 0.5 + ev.xg),
                                  [ev.id], {"xg": ev.xg, "outcome": ev.outcome}))
        elif ev.type == "goal":
            self.score[ev.team] += 1
            if ps is not None:
                ps["goals"] += 1
            new.append(Moment("goal", ev.minute, ev.team, ev.player, 1.0, [ev.id, ev.meta.get("assist_shot_id", ev.id)],
                              {"score": dict(self.score), "xg": ev.xg}))
        elif ev.type == "tackle" and st:
            st.tackles += 1
            st.tackles_won += ev.outcome == "won"
        elif ev.type == "pressure" and st:
            st.pressures += 1
        elif ev.type == "foul" and st:
            st.fouls += 1
        elif ev.type == "possession_change" and st:
            st.possession_events += 1
        elif ev.type == "card" and ev.outcome == "red":
            new.append(Moment("red_card", ev.minute, ev.team, ev.player, 0.95, [ev.id], {}))

        self._update_window(ev)
        new.extend(self._detect_swings(ev))
        self.moments.extend(new)
        return new

    def observe_frame(self, t: float, poss: str):
        """Track possession time from simulation frames."""
        if poss in self.poss_time:
            self.poss_time[poss] += max(0.0, t - self._last_t)
        self._last_t = t

    def possession(self) -> dict[str, float]:
        tot = sum(self.poss_time.values())
        if tot <= 0:
            return {self.home: 50.0, self.away: 50.0}
        return {k: round(100 * v / tot, 1) for k, v in self.poss_time.items()}

    def pressure_window(self) -> dict[str, int]:
        """Pressing actions (pressures + tackles) per team in the rolling window."""
        out = {self.home: 0, self.away: 0}
        for e in self._window:
            if e.type in ("pressure", "tackle") and e.team in out:
                out[e.team] += 1
        return out

    # ------------------------------------------------------------ momentum
    def _weight(self, ev: Event) -> float:
        if ev.type == "pass" and ev.outcome == "success" and (ev.end_x or 0) > 66:
            return _MOMENTUM_W["pass_final_third"]
        if ev.type == "tackle" and ev.outcome == "won":
            return _MOMENTUM_W["tackle_won"]
        if ev.type in ("shot", "pressure", "goal"):
            return _MOMENTUM_W[ev.type]
        return 0.0

    def _update_window(self, ev: Event):
        self._window.append(ev)
        while self._window and ev.clock - self._window[0].clock > WINDOW_MIN:
            self._window.popleft()
        self._momentum_hist.append((ev.clock, self.momentum()))

    def momentum(self) -> float:
        """Home minus away pressure score in the rolling window, normalized to -100..100."""
        sums = {self.home: 0.0, self.away: 0.0}
        for e in self._window:
            if e.team in sums:
                sums[e.team] += self._weight(e)
        total = sums[self.home] + sums[self.away]
        return round(100 * (sums[self.home] - sums[self.away]) / total, 1) if total > 1 else 0.0

    def control_vs_chaos(self) -> dict[str, float]:
        """Rhythm indicator: share of turnovers (chaos) vs completed passes (control) in the window."""
        passes = sum(1 for e in self._window if e.type == "pass")
        turnovers = sum(1 for e in self._window if e.type in ("possession_change", "tackle"))
        total = passes + turnovers
        chaos = round(100 * turnovers / total, 1) if total else 0.0
        return {"control": round(100 - chaos, 1), "chaos": chaos, "events_in_window": len(self._window)}

    def _detect_swings(self, ev: Event) -> list[Moment]:
        out: list[Moment] = []
        if len(self._momentum_hist) < 20 or ev.clock - self._last_swing_clock < 10:
            return out
        past = [m for c, m in self._momentum_hist if ev.clock - c >= 4]
        if not past:
            return out
        before, now = past[-1], self._momentum_hist[-1][1]
        if abs(now - before) >= 50 and abs(now) >= 25:
            team = self.home if now > before else self.away
            self._last_swing_clock = ev.clock
            evid = [e.id for e in list(self._window)[-6:]]
            out.append(Moment("momentum_swing", ev.minute, team, None, 0.7, evid,
                              {"before": before, "after": now, "control_vs_chaos": self.control_vs_chaos()}))
        return out

    # ------------------------------------------------------------- helpers
    def player_summary(self, pid: str) -> dict[str, float]:
        p = dict(self.player_stats.get(pid, {}))
        if p.get("passes"):
            p["pass_acc"] = round(100 * p.get("passes_ok", 0) / p["passes"], 1)
            p["avg_pass_difficulty"] = round(p.get("pass_difficulty_sum", 0) / p["passes"], 1)
        return p

    def snapshot(self) -> dict:
        return {
            "minute": self.minute,
            "score": self.score,
            "momentum": self.momentum(),
            "possession": self.possession(),
            "pressure": self.pressure_window(),
            "control_vs_chaos": self.control_vs_chaos(),
            "stats": {t: {**s.__dict__, "pass_acc": s.pass_acc, "xg": round(s.xg, 2)} for t, s in self.stats.items()},
        }
