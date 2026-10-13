"""A real match with tracking: the Sportec Open DFL dataset (CC BY 4.0, released with the authorization of the DFL).

    python tools/fetch_sportec.py            # one match (about 420 MB) into data/external/sportec/ (git-ignored)

Cite: Bassek, Rein, Weber, Memmert (2025), "An integrated dataset of spatiotemporal and event data in elite soccer", Scientific Data.

Unlike the Wyscout feed this one carries the positions of all players and of the ball (one frame every `step` seconds), so the
pipeline and the pitch view can be tested on real movement. Teams and players are pseudonymised ("Home #9"); the files themselves
hold real names and must never be published.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from ..models import Event, Player, Team, Tick

DATA = Path(__file__).resolve().parents[2] / "data" / "external" / "sportec"
FRAME = re.compile(r'<Frame N="(\d+)"[^>]*? X="(-?[\d.]+)" Y="(-?[\d.]+)"(?:[^>]*BallPossession="(\d)" BallStatus="(\d)")?')
FSET = re.compile(r'<FrameSet GameSection="(\w+)"[^>]*TeamId="([^"]+)" PersonId="([^"]+)"')
KX, KY = 1.05, 0.68
_CACHE: dict[str, dict[str, Any]] = {}


class DataMissing(FileNotFoundError):
    pass


_MATCH = re.compile(r"(DFL-MAT-\w+)\.xml")


def available_matches(folder: Path = DATA) -> list[str]:
    """Matches with all three files (match information, events, positions) downloaded."""
    found = []
    for p in folder.glob("DFL_02_01_*.xml"):
        mid = _MATCH.search(p.name).group(1)
        if list(folder.glob(f"DFL_03_02_*{mid}.xml")) and list(folder.glob(f"DFL_04_03_*{mid}.xml")):
            found.append(mid)
    return sorted(found)


def _utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def _line(code: str) -> str:
    c = (code or "").upper()
    if c == "TW":
        return "GK"
    if c.startswith(("IV", "LV", "RV")):
        return "DF"
    if c.startswith(("ST", "RA", "LA", "HL", "HR")) or c in ("OLM", "ORM"):
        return "FW"
    return "MF"


class SportecFeed:
    name = "sportec"

    def __init__(self, match: Optional[str] = None, index: int = 0, step: int = 2, pseudonymize: bool = True, folder: Path = DATA):
        matches = available_matches(folder)
        if not matches:
            raise DataMissing("Sportec data not found: run `python tools/fetch_sportec.py`")
        self.match_id = match or matches[index % len(matches)]
        self.step, self.pseudonymize, self.folder = step, pseudonymize, folder
        self._load()

    # ------------------------------------------------------------------ parsing
    def _load(self) -> None:
        key = f"{self.folder}:{self.match_id}:{self.step}:{self.pseudonymize}"
        if key in _CACHE:
            self.__dict__.update(_CACHE[key])
            return
        mi = ET.parse(next(self.folder.glob(f"DFL_02_01_*{self.match_id}.xml"))).getroot()
        gen = mi.find(".//General")
        home_club, away_club = gen.attrib["HomeTeamId"], gen.attrib["GuestTeamId"]
        side = {home_club: "HOM", away_club: "AWY"}
        res = gen.attrib.get("Result", "0:0").split(":")
        official = {"HOM": int(res[0]), "AWY": int(res[1])}
        persons: dict[str, dict[str, Any]] = {}
        lineups = {side[t.attrib["TeamId"]]: t.attrib.get("LineUp", "") for t in mi.iter("Team")}  # e.g. "4-2-3-1" (feed metadata)
        for t in mi.iter("Team"):
            for p in t.iter("Player"):
                persons[p.attrib["PersonId"]] = {"team": side[t.attrib["TeamId"]], "number": int(p.attrib.get("ShirtNumber", 0)),
                                                 "line": _line(p.attrib.get("PlayingPosition", "")),
                                                 "name": p.attrib.get("Shortname", "")}
        teams = []
        for s, label in (("HOM", "Home Team"), ("AWY", "Away Team")):
            ps = sorted([(pid, d) for pid, d in persons.items() if d["team"] == s], key=lambda x: x[1]["number"])
            # goalkeepers first, then by shirt number; pseudonyms use this rank, never the real shirt number
            ps.sort(key=lambda x: (x[1]["line"] != "GK", x[1]["number"]))
            teams.append(Team(id=s, name=label if self.pseudonymize else s, short=s, tactic=None, players=[
                Player(id=pid, name=f"{label.split()[0]} #{k + 1}" if self.pseudonymize else d["name"], team=s,
                       number=k + 1 if self.pseudonymize else d["number"], position=d["line"]) for k, (pid, d) in enumerate(ps)]))
        gks = {pid for pid, d in persons.items() if d["line"] == "GK"}

        # positions, one frame every `step` seconds
        stride = 25 * self.step
        pos: dict[tuple[str, str], dict[int, tuple[float, float]]] = {}
        ball: dict[str, dict[int, tuple]] = {"firstHalf": {}, "secondHalf": {}}
        first: dict[str, tuple[int, str]] = {}
        sec = person = team = ""
        with open(next(self.folder.glob(f"DFL_04_03_*{self.match_id}.xml")), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("<FrameSet"):
                    sec, team, person = FSET.search(line).groups()
                elif line.startswith("<Frame "):
                    m = FRAME.match(line)
                    n = int(m.group(1))
                    if sec not in first:
                        first[sec] = (n, re.search(r'T="([^"]+)"', line).group(1))
                    if (n - first[sec][0]) % stride:
                        continue
                    x, y = float(m.group(2)), float(m.group(3))
                    if team == "BALL":
                        ball[sec][n] = (x, y, m.group(4), m.group(5))
                    elif person in persons:
                        pos.setdefault((sec, person), {})[n] = (x, y)
        self.__dict__.update(teams=(teams[0], teams[1]), official_score=official, label="Bundesliga match with tracking", lineups=lineups)
        t0 = {s: _utc(v[1]) for s, v in first.items()}
        # which way does each team attack in each half? (from the keeper's mean position); mirror so that home always attacks right
        mirror = {}
        for s in ("firstHalf", "secondHalf"):
            xs = [sum(v[0] for v in d.values()) / len(d) for (ss, pid), d in pos.items() if ss == s and pid in gks and persons[pid]["team"] == "HOM"]
            mirror[s] = bool(xs) and xs[0] > 0  # home keeper on the right = home attacks left = mirror
        n0 = {s: v[0] for s, v in first.items()}
        # events
        er = ET.parse(next(self.folder.glob(f"DFL_03_02_*{self.match_id}.xml"))).getroot()
        raw = []
        for ev in er.iter("Event"):
            if not len(ev) or ev.attrib.get("EventTime") is None:
                continue
            raw.append((_utc(ev.attrib["EventTime"]), ev))
        raw.sort(key=lambda x: x[0])
        whistles = [t for t, ev in raw if ev[0].tag == "FinalWhistle"]
        h1_end = (whistles[0] - t0["firstHalf"]).total_seconds() if whistles else 2700.0
        offset = max(2700.0, h1_end + 15.0)
        total2 = (whistles[1] - t0["secondHalf"]).total_seconds() if len(whistles) > 1 else 2700.0

        def tsec(dt: datetime) -> float:
            return (dt - t0["firstHalf"]).total_seconds() if dt < t0["secondHalf"] else offset + (dt - t0["secondHalf"]).total_seconds()

        def section(dt: datetime) -> str:
            return "firstHalf" if dt < t0["secondHalf"] else "secondHalf"

        def norm(x: float, y: float, s: str, tracked: bool) -> tuple[float, float]:
            """Pitch coordinates (event: corner origin, tracking: centre origin) -> 0-100, home attacking right."""
            xc, yc = (x, y) if tracked else (x - 52.5, y - 34.0)
            if mirror[s]:
                xc, yc = -xc, -yc
            return max(0.0, min(100.0, (xc + 52.5) / 105 * 100)), max(0.0, min(100.0, (yc + 34.0) / 68 * 100))

        # frames
        frames: list[dict[str, Any]] = []
        last_poss = "HOM"
        carrier_hint: Optional[str] = None
        for s in ("firstHalf", "secondHalf"):
            for n in sorted(ball[s]):
                bx, by, bp, bs = ball[s][n]
                t = ((n - n0[s]) / 25.0) + (0.0 if s == "firstHalf" else offset)
                if (s == "firstHalf" and t > h1_end + 1) or (s == "secondHalf" and t > offset + total2 + 1):
                    continue
                gx, gy = norm(bx, by, s, True)
                if bs == "1" and bp in ("1", "2"):
                    last_poss = "HOM" if bp == "1" else "AWY"
                slots: list[tuple[str, float, float]] = []
                for sd in ("HOM", "AWY"):
                    on = [(pid, *norm(*pos[(s, pid)][n], s, True)) for pid, d in persons.items()
                          if d["team"] == sd and (s, pid) in pos and n in pos[(s, pid)]]
                    on.sort(key=lambda r: (persons[r[0]]["line"] != "GK", persons[r[0]]["number"]))
                    slots += on[:11] + [("", 50.0, 50.0)] * (11 - len(on[:11]))
                mates = [r for r in slots if r[0] and persons[r[0]]["team"] == last_poss]
                carrier = min(mates, key=lambda r: math.hypot(r[1] - gx, r[2] - gy))[0] if mates else None
                frames.append({"t": round(t, 1), "minute": int(t // 60), "ball": [round(gx, 1), round(gy, 1)], "poss": last_poss,
                               "carrier": carrier, "p": [[round(r[1], 1), round(r[2], 1)] for r in slots], "ids": [r[0] for r in slots],
                               "off": [i for i, r in enumerate(slots) if not r[0]]})
        self.frames = frames
        self.raw_events = [(tsec(dt), section(dt), ev) for dt, ev in raw if t0["firstHalf"] <= dt]
        self._persons, self._mirror, self._norm = persons, mirror, norm
        self._h1_end, self._offset, self._end = h1_end, offset, offset + total2
        _CACHE[key] = {k: v for k, v in self.__dict__.items() if k not in ("match_id", "step", "pseudonymize", "folder")}

    # ------------------------------------------------------------------ events
    def _events(self) -> list[tuple[float, Event]]:
        persons, norm = self._persons, self._norm
        out: list[tuple[float, Event]] = []
        eid = 0
        score = {"HOM": 0, "AWY": 0}
        poss = "HOM"
        raw = self.raw_events
        n = len(raw)
        side_of_person = {pid: d["team"] for pid, d in persons.items()}

        def make(t: float, type_: str, team: str, **kw) -> Event:
            nonlocal eid
            eid += 1
            return Event(id=eid, minute=int(t // 60), second=int(t % 60), type=type_, team=team, **kw)

        def tf(ev: ET.Element, s: str, team: str) -> tuple[float, float]:
            """Event position in the acting team's frame (attacking towards x = 100)."""
            x, y = norm(float(ev.attrib["X-Position"]), float(ev.attrib["Y-Position"]), s, False)
            return (x, y) if team == "HOM" else (100 - x, 100 - y)

        for i, (t, s, ev) in enumerate(raw):
            c = ev[0]
            tag = c.tag
            has_pos = "X-Position" in ev.attrib
            if tag == "Penalty" and len(c) and c[0].tag == "ShotAtGoal":  # a penalty wraps its shot
                c, tag = c[0], "ShotAtGoal"
            if not has_pos and tag not in ("Foul", "Caution"):
                continue
            player = c.attrib.get("Player")
            team = side_of_person.get(player) if player else None
            if tag == "Play" and player and team:
                x, y = tf(ev, s, team)
                ok = c.attrib.get("Evaluation") == "successfullyCompleted"
                end = None
                receiver = None
                for j in range(i + 1, min(i + 6, n)):  # the ball ends where the next recorded action takes place
                    nt, ns, nev = raw[j]
                    npl = nev[0].attrib.get("Player")
                    if nt - t > 8:
                        break
                    if npl and "X-Position" in nev.attrib:
                        end = tf(nev, ns, team)
                        if ok and side_of_person.get(npl) == team and npl != player:
                            receiver = npl
                        break
                if team != poss:
                    poss = team
                    out.append((t, make(t, "possession_change", team, player=player, x=x, y=y, meta={"reason": "feed"})))
                ex, ey = end if end else (x, y)
                out.append((t, make(t, "pass", team, player=player, x=x, y=y, end_x=ex, end_y=ey, outcome="success" if ok else "fail",
                                    meta={"distance_m": round(math.hypot((ex - x) * KX, (ey - y) * KY), 1), "forward": (ex - x) > 3,
                                          "receiver": receiver if ok else None})))
            elif tag == "ShotAtGoal" and player and team:
                x, y = tf(ev, s, team)
                kind = c[0].tag if len(c) else "ShotWide"
                outcome = {"SuccessfulShot": "goal", "SavedShot": "saved", "BlockedShot": "blocked"}.get(kind, "off_target")
                xg = float(c.attrib["xG"]) if "xG" in c.attrib else None
                if team != poss:
                    poss = team
                    out.append((t, make(t, "possession_change", team, player=player, x=x, y=y, meta={"reason": "feed"})))
                shot = make(t, "shot", team, player=player, x=x, y=y, end_x=100.0, end_y=50.0, outcome=outcome, xg=xg,
                            meta={"distance_m": float(c.attrib.get("DistanceToGoal", 0)), "xg_estimated": xg is None})
                out.append((t, shot))
                if outcome == "goal":
                    score[team] += 1
                    out.append((t, make(t, "goal", team, player=player, x=x, y=y, xg=xg,
                                        meta={"score": dict(score), "assist_shot_id": shot.id})))
            elif tag == "TacklingGame":
                w, l = c.attrib.get("Winner"), c.attrib.get("Loser")
                if c.attrib.get("WinnerRole") == "withoutBallControl":
                    d, won = w, True
                elif c.attrib.get("LoserRole") == "withoutBallControl":
                    d, won = l, False
                else:
                    continue
                dt_ = side_of_person.get(d)
                if d and dt_:
                    x, y = tf(ev, s, dt_)
                    out.append((t, make(t, "tackle", dt_, player=d, x=x, y=y, outcome="won" if won else "lost")))
            elif tag == "Foul" and c.attrib.get("Fouler"):
                f = c.attrib["Fouler"]
                ft = side_of_person.get(f)
                if ft:
                    x, y = tf(ev, s, ft) if has_pos else (None, None)
                    out.append((t, make(t, "foul", ft, player=f, x=x, y=y)))
            elif tag == "Caution" and player and team:
                color = c.attrib.get("CardColor", "yellow")
                out.append((t, make(t, "card", team, player=player, outcome="red" if color in ("red", "yellowRed") else "yellow")))
            elif tag == "BallClaiming" and player and team and team != poss:
                x, y = tf(ev, s, team)
                poss = team
                out.append((t, make(t, "possession_change", team, player=player, x=x, y=y, meta={"reason": "ball_claimed"})))
        return out

    def ticks(self) -> Iterator[Tick]:
        """Chronological ticks. Event ids are assigned here so that they increase strictly (goal -> shot links are remapped)."""
        evs = self._events()
        counter = 0

        def stamp(events: list[Event]) -> list[Event]:
            nonlocal counter
            remap = {}
            for e in events:
                counter += 1
                remap[e.id] = counter
                e.id = counter
            for e in events:
                if "assist_shot_id" in e.meta:
                    e.meta["assist_shot_id"] = remap.get(e.meta["assist_shot_id"], e.id)
            return events

        yield Tick(0.0, {"t": 0.0, "minute": 0, "poss": "HOM"}, stamp([Event(id=0, minute=0, second=0, type="kickoff", team="HOM", x=50, y=50)]))
        k, half_done = 0, False
        for fr in self.frames:
            t = fr["t"]
            bucket: list[Event] = []
            if not half_done and t > self._h1_end:
                half_done = True
                bucket.append(Event(id=0, minute=int(self._h1_end // 60), second=int(self._h1_end % 60), type="halftime", team=fr["poss"]))
            while k < len(evs) and evs[k][0] < t + self.step:
                bucket.append(evs[k][1])
                k += 1
            yield Tick(t, fr, stamp(bucket))
        last = self.frames[-1]["t"] if self.frames else 5400.0
        poss = self.frames[-1]["poss"] if self.frames else "HOM"
        yield Tick(last, {"t": last, "minute": int(last // 60), "poss": poss},
                   stamp([Event(id=0, minute=int(last // 60), second=int(last % 60), type="fulltime", team=poss)]))
