"""Seeded synthetic match simulator producing football-realistic event streams."""
from __future__ import annotations

import asyncio
import math
import random
from typing import AsyncIterator, Iterator, Optional

from ..models import Event, Team
from .teams import default_teams

SCENARIOS = {
    # scenario -> (minute, effect) tweaks applied to team styles / events
    "balanced": {},
    "comeback": {"underdog_boost_after": 60},
    "red_card": {"red_card_minute": 55},
}


class MatchSimulator:
    """Possession-chain simulator. One call to `events()` yields a full 90+ minute match."""

    def __init__(self, seed: int = 42, scenario: str = "balanced",
                 teams: Optional[tuple[Team, Team]] = None):
        self.rng = random.Random(seed)
        self.seed = seed
        self.scenario = scenario
        self.home, self.away = teams or default_teams()
        self.teams = {self.home.id: self.home, self.away.id: self.away}
        self._eid = 0
        self.score = {self.home.id: 0, self.away.id: 0}
        self.red_carded: dict[str, int] = {}
        self.red_emitted = False

    # ---------------------------------------------------------------- helpers
    def _other(self, tid: str) -> str:
        return self.away.id if tid == self.home.id else self.home.id

    def _ev(self, minute: int, second: int, type_: str, team: str, **kw) -> Event:
        self._eid += 1
        return Event(id=self._eid, minute=minute, second=second, type=type_, team=team, **kw)

    def _pick(self, tid: str, positions: tuple[str, ...]) -> str:
        pool = [p for p in self.teams[tid].players if p.position in positions]
        return self.rng.choice(pool).id

    def _style(self, tid: str, minute: int) -> dict[str, float]:
        s = dict(self.teams[tid].style)
        if self.scenario == "comeback" and minute >= 60 and tid == self.away.id:
            s["pressing"] = min(1, s["pressing"] + 0.35)
            s["directness"] = min(1, s["directness"] + 0.2)
            s["possession"] = min(1, s["possession"] + 0.15)
        if tid in self.red_carded and minute >= self.red_carded[tid]:
            s["pressing"] *= 0.5
            s["possession"] *= 0.7
        return s

    # ------------------------------------------------------------------ main
    def events(self) -> Iterator[Event]:
        rng = self.rng
        possession = self.home.id
        x = 50.0
        yield self._ev(0, 0, "kickoff", possession, x=50, y=50)
        total_minutes = 90 + rng.randint(1, 4)
        t = 0.0
        halftime_done = False
        if self.scenario == "red_card":
            self.red_carded[self.away.id] = SCENARIOS["red_card"]["red_card_minute"]

        while t < total_minutes * 60:
            minute, second = int(t // 60), int(t % 60)
            if minute >= 45 and not halftime_done:
                halftime_done = True
                yield self._ev(45, 0, "halftime", possession)
                possession, x = self.away.id, 50.0
                t = 45 * 60
                continue
            if self.scenario == "red_card" and minute == self.red_carded.get(self.away.id) \
                    and not self.red_emitted:
                self.red_emitted = True
                pid = self._pick(self.away.id, ("DF", "MF"))
                yield self._ev(minute, second, "card", self.away.id, player=pid, outcome="red")
                t += 20
                continue

            style = self._style(possession, minute)
            opp = self._other(possession)
            opp_style = self._style(opp, minute)
            dt = rng.uniform(2.5, 7.0)
            t += dt
            minute, second = int(t // 60), int(t % 60)
            if minute >= total_minutes:
                break

            # defender pressure on the ball (higher when the opponent presses)
            if rng.random() < 0.18 * opp_style["pressing"]:
                presser = self._pick(opp, ("MF", "FW", "DF"))
                yield self._ev(minute, second, "pressure", opp, player=presser, x=100 - x, y=rng.uniform(10, 90),
                               meta={"intensity": round(opp_style["pressing"] * rng.uniform(0.7, 1.2), 2)})

            # decide action from zone
            in_box_zone = x > 78
            r = rng.random()
            shoot_p = 0.10 if in_box_zone else (0.025 if x > 65 else 0.0)
            if r < shoot_p:
                yield from self._shot(possession, minute, second, x)
                possession, x = self._after_shot(possession, minute)
                continue
            if r < shoot_p + 0.10 * opp_style["pressing"] + 0.04:
                tackler = self._pick(opp, ("DF", "MF"))
                won = rng.random() < 0.5 * (0.5 + opp_style["pressing"] * 0.6)
                carrier = self._pick(possession, ("MF", "FW", "DF"))
                yield self._ev(minute, second, "tackle", opp, player=tackler, x=100 - x,
                               y=rng.uniform(5, 95), outcome="won" if won else "lost",
                               meta={"against": carrier})
                if won:
                    yield self._ev(minute, second, "possession_change", opp, x=100 - x, y=rng.uniform(5, 95))
                    possession, x = opp, 100 - x
                continue
            if r < shoot_p + 0.115 * opp_style["pressing"] + 0.04 + 0.025:
                fouler = self._pick(opp, ("DF", "MF"))
                yield self._ev(minute, second, "foul", opp, player=fouler, x=100 - x, y=rng.uniform(5, 95))
                t += rng.uniform(5, 15)
                continue

            # pass
            ok, nx = self._pass(possession, minute, second, x, style, opp_style)
            yield ok
            if ok.outcome == "fail":
                yield self._ev(minute, second, "possession_change", opp, x=100 - nx, y=ok.end_y or 50)
                possession, x = opp, 100 - nx
            else:
                x = nx

        yield self._ev(total_minutes, 0, "fulltime", possession)

    # --------------------------------------------------------------- actions
    def _pass(self, tid: str, minute: int, second: int, x: float, style: dict, opp_style: dict):
        rng = self.rng
        passer = self._pick(tid, ("DF", "MF", "FW"))
        forward = rng.random() < 0.3 + 0.35 * style["directness"]
        dx = rng.uniform(5, 35) if forward else rng.uniform(-18, 8)
        nx = max(2.0, min(98.0, x + dx))
        y0, y1 = rng.uniform(5, 95), rng.uniform(5, 95)
        dist_m = math.hypot((nx - x) * 1.05, (y1 - y0) * 0.68)
        base = 0.9 - 0.006 * dist_m - 0.15 * opp_style["pressing"] + (0.04 if not forward else 0)
        success = rng.random() < max(0.35, base)
        ev = self._ev(minute, second, "pass", tid, player=passer, x=x, y=y0, end_x=nx, end_y=y1,
                      outcome="success" if success else "fail",
                      speed_kmh=round(rng.uniform(40, 95), 1),
                      meta={"distance_m": round(dist_m, 1), "forward": forward,
                            "receiver": self._pick(tid, ("DF", "MF", "FW")) if success else None})
        return ev, nx

    def _shot(self, tid: str, minute: int, second: int, x: float):
        rng = self.rng
        style = self._style(tid, minute)
        shooter = self._pick(tid, ("FW", "MF", "FW"))
        dist = max(5.0, (100 - x) * 1.05 + rng.uniform(-3, 5))
        angle_pen = rng.uniform(0.7, 1.0)
        xg = max(0.01, min(0.85, (0.55 * math.exp(-dist / 11)) * angle_pen * (0.8 + style["finishing"] * 0.4)))
        roll = rng.random()
        speed = round(rng.uniform(70, 125), 1)
        if roll < xg * 0.7:
            outcome = "goal"
        elif roll < xg + 0.30:
            outcome = rng.choice(["saved", "saved", "blocked"])
        else:
            outcome = "off_target"
        ev = self._ev(minute, second, "shot", tid, player=shooter, x=x, y=rng.uniform(25, 75),
                      end_x=100, end_y=rng.uniform(35, 65), outcome=outcome, xg=round(xg, 3), speed_kmh=speed,
                      meta={"distance_m": round(dist, 1)})
        yield ev
        if outcome == "goal":
            self.score[tid] += 1
            yield self._ev(minute, second, "goal", tid, player=shooter, x=x, y=ev.y, xg=ev.xg,
                           meta={"score": dict(self.score), "assist_shot_id": ev.id})
        elif outcome == "saved":
            gk = self._pick(self._other(tid), ("GK",))
            yield self._ev(minute, second, "save", self._other(tid), player=gk, x=0, y=50, meta={"shot_id": ev.id})

    def _after_shot(self, tid: str, minute: int):
        opp = self._other(tid)
        # restart: kickoff after goal, goal kick / counter otherwise
        return opp, self.rng.choice([15.0, 25.0, 40.0])

    # -------------------------------------------------------- live streaming
    async def stream(self, speed: float = 30.0) -> AsyncIterator[Event]:
        """Replay events paced at `speed` x real time (speed=1 -> real match time)."""
        prev = 0.0
        for ev in self.events():
            wait = max(0.0, (ev.clock - prev) * 60 / speed)
            if wait:
                await asyncio.sleep(wait)
            prev = max(prev, ev.clock)
            yield ev
