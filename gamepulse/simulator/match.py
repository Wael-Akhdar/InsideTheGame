"""Tactical match simulator.

Both teams are positioned from their formation, roles and instructions (line height, pressing, width, tempo,
directness).  Players move every tick, the ball carrier decides between pass / dribble / shot based on his role,
his attributes and the pressure around him, and defenders press and tackle according to the team's pressing.
Everything is seeded, so a (tactic, tactic, seed) triple always replays the same match.

Coordinates: pitch is 0..100 on both axes (105 m x 68 m).  Players are stored in their *team frame* (own goal at
x=0); frames sent to the UI use *global* coordinates (home attacks to the right).
"""
from __future__ import annotations

import asyncio
import math
import random
from typing import AsyncIterator, Iterator, Optional

import numpy as np

from ..models import Event, Tick
from ..tactics import FORMATIONS, ROLES
from .teams import build_team

KX, KY = 1.05, 0.68  # units -> metres
HALF = 45 * 60


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


class _Side:
    """Per-team simulation state."""

    def __init__(self, team):
        self.team = team
        self.id = team.id
        self.tac = team.tactic
        slots = FORMATIONS[self.tac.formation]
        roles = [ROLES[r] for r in self.tac.roles]
        self.roles = roles
        self.base = np.array([[s[1], s[2]] for s in slots], float)
        self.gk = np.array([s[3] == "GK" for s in slots])
        self.ax = np.array([r["ax"] for r in roles], float)
        self.dx = np.array([r["dx"] for r in roles], float)
        self.spread = np.array([r["spread"] for r in roles], float)
        self.pr = np.array([r["pr"] for r in roles], float)
        self.pace = np.array([p.attrs["pace"] for p in team.players], float)
        self.pos = self.base.copy()
        self.active = np.ones(11, bool)
        self.fat = 1.0
        self.pressers: list[int] = []

    def attr(self, i: int, name: str) -> float:
        return self.team.players[i].attrs[name]


class MatchSimulator:
    def __init__(self, seed: int = 42, home_tactic="Possession 4-3-3", away_tactic="Counter-attack 4-4-2",
                 record_frames: bool = True, home_quality: float = 1.0, away_quality: float = 1.0):
        self.seed = seed
        self.rng = random.Random(seed)
        self.nprng = np.random.default_rng(seed)
        self.home = build_team("RVR", home_tactic, seed, home_quality)
        self.away = build_team("NTH", away_tactic, seed, away_quality)
        self.teams = {self.home.id: self.home, self.away.id: self.away}
        self.sides = {self.home.id: _Side(self.home), self.away.id: _Side(self.away)}
        self.record_frames = record_frames
        self.score = {self.home.id: 0, self.away.id: 0}
        self.poss_time = {self.home.id: 0.0, self.away.id: 0.0}
        self._eid = 0
        self.poss = self.home.id
        self.c = 0  # carrier index in the possessing side
        self.ball = np.array([50.0, 50.0])  # global coordinates

    # ------------------------------------------------------------------ utils
    def _other(self, tid: str) -> str:
        return self.away.id if tid == self.home.id else self.home.id

    def _ev(self, t: float, type_: str, team: str, **kw) -> Event:
        self._eid += 1
        return Event(id=self._eid, minute=int(t // 60), second=int(t % 60), type=type_, team=team, **kw)

    def _glob(self, side: _Side, p) -> np.ndarray:
        p = np.asarray(p, float)
        return p if side.id == self.home.id else 100.0 - p

    def _ball_in(self, side: _Side) -> np.ndarray:
        return self.ball if side.id == self.home.id else 100.0 - self.ball

    @staticmethod
    def _dists_m(p, others: np.ndarray) -> np.ndarray:
        return np.hypot((others[:, 0] - p[0]) * KX, (others[:, 1] - p[1]) * KY)

    def _opp_view(self, D: _Side) -> np.ndarray:
        """Defender positions expressed in the possessing team's frame (inactive players pushed far away)."""
        o = 100.0 - D.pos
        o = o.copy()
        o[~D.active] = 1e4
        return o

    # ------------------------------------------------------------------ restarts
    def _kickoff(self, tid: str):
        for s in self.sides.values():
            s.pos = s.base.copy()
            s.pos[:, 0] = np.minimum(s.pos[:, 0], 47.0)
        side = self.sides[tid]
        cand = [i for i in range(11) if side.active[i] and not side.gk[i]]
        c = max(cand, key=lambda i: side.base[i, 0])
        side.pos[c] = (50.0, 50.0)
        self.poss, self.c = tid, c
        self.ball = self._glob(side, (50.0, 50.0))

    def _give_to_gk(self, tid: str):
        side = self.sides[tid]
        side.pos[0] = (5.0, 50.0)
        self.poss, self.c = tid, 0
        self.ball = self._glob(side, side.pos[0])

    # ------------------------------------------------------------------ movement
    def _move(self, S: _Side, has_ball: bool, dt: float):
        tac = S.tac
        bx, by = self._ball_in(S)
        lh = tac.line_height
        if has_ball:
            tx = S.base[:, 0] + 0.3 * (bx - 50) + S.ax * (0.6 + 0.4 * tac.tempo) + (lh - 0.5) * 10
        else:
            tx = S.base[:, 0] + 0.3 * (bx - 50) + S.dx + (lh - 0.5) * 24
        tx[S.gk] = 5 + (lh - 0.5) * 8 + 0.08 * (bx - 50)
        ty = 50 + (S.base[:, 1] - 50) * (0.8 + 0.35 * tac.width) * S.spread + 0.2 * (by - 50)
        tgt = np.stack([np.clip(tx, 3, 97), np.clip(ty, 3, 97)], axis=1)

        S.pressers = []
        full = np.zeros(11, bool)
        if has_ball:
            c = self.c
            tgt[c] = (min(97.0, S.pos[c, 0] + 2.5), S.pos[c, 1])
            full[c] = True
        else:
            d = np.hypot(S.pos[:, 0] - bx, S.pos[:, 1] - by)
            radius = (16 + 30 * tac.pressing) * S.fat
            k = 1 + int(round(tac.pressing * 3 * S.fat))
            ok = np.where(~S.gk & S.active & (d < radius * S.pr))[0]
            ok = ok[np.argsort(d[ok])][:k]
            for i in ok:
                tgt[i] = (bx, by)
                full[i] = True
                S.pressers.append(int(i))

        vec = tgt - S.pos
        dist = np.hypot(vec[:, 0], vec[:, 1]) + 1e-9
        max_step = 5.0 * (S.pace / 75.0) * S.fat * dt
        frac = np.minimum(1.0, max_step / dist) * np.where(full, 1.0, 0.7)
        step = vec * frac[:, None] + self.nprng.normal(0, 0.25, (11, 2))
        step[~S.active] = 0
        S.pos = np.clip(S.pos + step, 1.0, 99.0)

    # ------------------------------------------------------------------ one tick
    def _step(self, t: float, dt: float, evs: list[Event]):
        rng = self.rng
        P, D = self.sides[self.poss], self.sides[self._other(self.poss)]
        prog = min(1.0, t / 5400)
        for s in (P, D):  # high pressing and tempo burn stamina
            s.fat = max(0.6, 1 - 0.38 * prog * (0.2 + 0.55 * s.tac.pressing + 0.25 * s.tac.tempo))
        self._move(P, True, dt)
        self._move(D, False, dt)
        c = self.c
        me = P.pos[c]
        self.ball = self._glob(P, me)
        self.poss_time[P.id] += dt

        opp = self._opp_view(D)
        d = self._dists_m(me, opp)
        j = int(np.argmin(d))
        dmin = float(d[j])
        pressure = float(np.clip(1 - d / 10, 0, None).sum())
        role = P.roles[c]

        # pressure event from the closest presser
        near = [i for i in D.pressers if math.hypot((D.pos[i, 0] - (100 - me[0])) * KX, (D.pos[i, 1] - (100 - me[1])) * KY) < 7]
        if near and rng.random() < 0.15:
            i = near[0]
            evs.append(self._ev(t, "pressure", D.id, player=D.team.players[i].id, x=float(D.pos[i, 0]), y=float(D.pos[i, 1]),
                                meta={"intensity": round(D.tac.pressing * D.fat * rng.uniform(0.8, 1.2), 2),
                                      "against": P.team.players[c].id}))

        # ---- tackle attempt by the closest defender
        if dmin < 3.5:
            p_try = 0.03 + 0.08 * D.tac.pressing * D.fat
            if rng.random() < p_try:
                tk = D.attr(j, "tackling")
                won = rng.random() < _clamp(0.42 + (tk - P.attr(c, "dribbling")) / 200, 0.15, 0.75)
                evs.append(self._ev(t, "tackle", D.id, player=D.team.players[j].id, x=float(D.pos[j, 0]), y=float(D.pos[j, 1]),
                                    outcome="won" if won else "lost", meta={"against": P.team.players[c].id}))
                if won:
                    self._turnover(D, j, t, evs, "tackle")
                    return
                if rng.random() < 0.18 * (0.5 + D.tac.pressing):
                    evs.append(self._ev(t, "foul", D.id, player=D.team.players[j].id, x=float(D.pos[j, 0]), y=float(D.pos[j, 1])))
                    if rng.random() < 0.004 * (0.6 + D.tac.pressing) and not D.gk[j]:
                        D.active[j] = False
                        evs.append(self._ev(t, "card", D.id, player=D.team.players[j].id, outcome="red"))
                    return

        # ---- choose action
        fx, fy = float(me[0]), float(me[1])
        in_box = fx > 84 and abs(fy - 50) < 24
        zone = 1.6 if in_box else (0.6 if fx > 70 else 0.0)
        shoot_p = 0.026 * (0.5 + 0.5 * role["sh"]) * zone * (0.7 + 0.3 * P.attr(c, "shooting") / 70)
        drib_p = 0.07 * role["dr"] * (P.attr(c, "dribbling") / 70) * (1.4 if dmin < 9 else 0.7)
        r = rng.random()
        if r < shoot_p:
            self._shoot(P, D, t, evs, pressure)
        elif r < shoot_p + drib_p and not P.gk[c]:
            self._dribble(P, D, t, evs, j, dmin)
        else:
            self._pass(P, D, t, evs, opp, pressure)

    def _turnover(self, D: _Side, j: int, t: float, evs: list[Event], reason: str):
        evs.append(self._ev(t, "possession_change", D.id, player=D.team.players[j].id,
                            x=float(D.pos[j, 0]), y=float(D.pos[j, 1]), meta={"reason": reason}))
        self.poss, self.c = D.id, j
        self.ball = self._glob(D, D.pos[j])

    def _dribble(self, P: _Side, D: _Side, t: float, evs: list[Event], j: int, dmin: float):
        rng, c = self.rng, self.c
        me = P.pos[c]
        ok = rng.random() < _clamp(0.58 + (P.attr(c, "dribbling") - D.attr(j, "tackling")) / 150 - (0.12 if dmin < 4 else 0), 0.2, 0.85)
        if ok:
            fwd = rng.uniform(4, 9)
            end = (min(97.0, me[0] + fwd), _clamp(me[1] + rng.uniform(-4, 4), 2, 98))
            evs.append(self._ev(t, "dribble", P.id, player=P.team.players[c].id, x=float(me[0]), y=float(me[1]),
                                end_x=end[0], end_y=end[1], outcome="success"))
            P.pos[c] = end
            self.ball = self._glob(P, end)
        else:
            evs.append(self._ev(t, "tackle", D.id, player=D.team.players[j].id, x=float(D.pos[j, 0]), y=float(D.pos[j, 1]),
                                outcome="won", meta={"against": P.team.players[c].id, "duel": "dribble"}))
            self._turnover(D, j, t, evs, "dribble_lost")

    def _pass(self, P: _Side, D: _Side, t: float, evs: list[Event], opp: np.ndarray, pressure: float):
        rng, c = self.rng, self.c
        me = P.pos[c]
        role = P.roles[c]
        directness = P.tac.directness
        cands, weights = [], []
        for i in range(11):
            if i == c or not P.active[i]:
                continue
            rp = P.pos[i]
            fwd = float(rp[0] - me[0])
            dm = math.hypot((rp[0] - me[0]) * KX, (rp[1] - me[1]) * KY)
            if dm < 4:
                continue
            open_r = min(14.0, float(self._dists_m(rp, opp).min()))
            w_dir = 0.9 + 1.2 * directness + 1.2 * role["fw"]
            w = math.exp(fwd / 22 * w_dir) * (0.35 + open_r / 14)
            w *= math.exp(-dm / (14 + 22 * directness + P.attr(c, "vision") / 10))
            if fwd > 0:
                w *= 1 - 0.5 * max(0.0, role["sf"])
            cands.append((i, fwd, dm, open_r))
            weights.append(w)
        if not cands:
            return
        i, fwd, dm, open_r = rng.choices(cands, weights=weights)[0]
        p = (1.03 - 0.10 * (P.tac.tempo - 0.5) - 0.0038 * dm * (1.2 - P.attr(c, "vision") / 150) - 0.07 * min(pressure, 2.0)
             - 0.10 * (1 - open_r / 14) + (P.attr(c, "passing") - 70) / 250
             - 0.08 * max(0.0, fwd) / 40 * (1 - max(0.0, role["sf"])))
        ok = rng.random() < _clamp(p, 0.3, 0.97)
        rp = P.pos[i]
        ev = self._ev(t, "pass", P.id, player=P.team.players[c].id, x=float(me[0]), y=float(me[1]),
                      end_x=float(rp[0]), end_y=float(rp[1]), outcome="success" if ok else "fail",
                      speed_kmh=round(_clamp(35 + dm * 1.6 + rng.uniform(-6, 8), 30, 110), 1),
                      meta={"distance_m": round(dm, 1), "forward": fwd > 3,
                            "receiver": P.team.players[i].id if ok else None})
        evs.append(ev)
        if ok:
            self.c = i
            self.ball = self._glob(P, rp)
        else:
            dd = self._dists_m(rp, opp)
            j = int(np.argmin(dd))
            self._turnover(D, j, t, evs, "interception")

    def _shoot(self, P: _Side, D: _Side, t: float, evs: list[Event], pressure: float):
        rng, c = self.rng, self.c
        me = P.pos[c]
        dist = max(4.0, math.hypot((100 - me[0]) * KX, (50 - me[1]) * KY))
        lateral = abs(me[1] - 50) * KY
        angle = math.atan2(7.32 * (100 - me[0]) * KX, ((100 - me[0]) * KX) ** 2 + lateral ** 2 - 3.66 ** 2 + 1e-9)
        angle = angle if angle > 0 else angle + math.pi
        xg = 0.62 * math.exp(-dist / 9.5) * (0.35 + 0.65 * min(1.0, angle / 0.55)) * (1 - 0.18 * min(pressure, 2.0))
        xg = _clamp(xg, 0.01, 0.8)
        finishing = P.attr(c, "shooting") / 70
        keeper = D.attr(0, "keeping") / 75
        roll = rng.random()
        if roll < xg * finishing / keeper * 0.8:
            outcome = "goal"
        else:
            r2 = rng.random()
            outcome = "saved" if r2 < 0.42 else ("blocked" if r2 < 0.42 + 0.18 + 0.1 * pressure else "off_target")
        shooter = P.team.players[c].id
        ev = self._ev(t, "shot", P.id, player=shooter, x=float(me[0]), y=float(me[1]), end_x=100.0,
                      end_y=rng.uniform(40, 60) if outcome != "off_target" else rng.choice([rng.uniform(25, 38), rng.uniform(62, 75)]),
                      outcome=outcome, xg=round(xg, 3), speed_kmh=round(rng.uniform(70, 125), 1),
                      meta={"distance_m": round(dist, 1)})
        evs.append(ev)
        if outcome == "goal":
            self.score[P.id] += 1
            evs.append(self._ev(t, "goal", P.id, player=shooter, x=float(me[0]), y=float(me[1]), xg=ev.xg,
                                meta={"score": dict(self.score), "assist_shot_id": ev.id}))
            self._kickoff(D.id)
        else:
            if outcome == "saved":
                evs.append(self._ev(t, "save", D.id, player=D.team.players[0].id, x=5.0, y=50.0, meta={"shot_id": ev.id}))
            self._give_to_gk(D.id)

    # ------------------------------------------------------------------ output
    def _frame(self, t: float) -> dict:
        if not self.record_frames:
            return {}
        h, a = self.sides[self.home.id], self.sides[self.away.id]
        pts = np.concatenate([h.pos, 100.0 - a.pos])
        side = self.sides[self.poss]
        return {"t": round(t, 1), "minute": int(t // 60), "ball": [round(float(self.ball[0]), 1), round(float(self.ball[1]), 1)],
                "poss": self.poss, "carrier": side.team.players[self.c].id,
                "p": np.round(pts, 1).tolist(),
                "off": [int(i) for i in range(22) if not (h.active if i < 11 else a.active)[i % 11]]}

    def ticks(self) -> Iterator[Tick]:
        rng = self.rng
        total = (90 + rng.randint(1, 4)) * 60
        self._kickoff(self.home.id)
        t = 0.0
        yield Tick(0.0, self._frame(0.0), [self._ev(0, "kickoff", self.home.id, x=50, y=50)])
        half_done = False
        while t < total:
            if t >= HALF and not half_done:
                half_done = True
                t = float(HALF)
                self._kickoff(self.away.id)
                yield Tick(t, self._frame(t), [self._ev(t, "halftime", self.away.id)])
                continue
            tempo = self.sides[self.poss].tac.tempo
            dt = (5.5 - 3.0 * tempo) * rng.uniform(0.8, 1.2)
            t += dt
            evs: list[Event] = []
            self._step(t, dt, evs)
            yield Tick(t, self._frame(t), evs)
        yield Tick(t, self._frame(t), [self._ev(t, "fulltime", self.poss)])

    def events(self) -> Iterator[Event]:
        for tk in self.ticks():
            yield from tk.events

    async def stream(self, speed: float = 60.0) -> AsyncIterator[Tick]:
        """Replay the match paced at `speed` x real time (speed=1 -> real match time)."""
        prev = 0.0
        for tk in self.ticks():
            wait = max(0.0, (tk.t - prev) / speed)
            if wait:
                await asyncio.sleep(wait)
            prev = max(prev, tk.t)
            yield tk
