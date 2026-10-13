"""A real match from the public Wyscout dataset (CC BY 4.0), exposed through the GamePulse event contract.

    python tools/fetch_wyscout.py     # once: data goes to data/external/ (git-ignored)

Cite: Pappalardo et al. (2019), "A public data set of spatio-temporal match events in soccer competitions", Scientific Data 6:236.

Teams and players are pseudonymised by default ("Home Team", "Home #7"): real club and player names never reach the UI,
the overlays or the logs. The feed contains only events (no player positions), exactly like many commercial event feeds.
"""
from __future__ import annotations

import json
import math
import zipfile
from pathlib import Path
from typing import Any, Iterator, Optional

from ..models import Event, Player, Team, Tick
from .xg import estimate_xg

DATA = Path(__file__).resolve().parents[2] / "data" / "external" / "wyscout"
LEAGUES = ("England", "France", "Germany", "Italy", "Spain")
KX, KY = 1.05, 0.68
HALF = 45 * 60
LINE = {"GK": "GK", "DF": "DF", "MD": "MF", "FW": "FW"}
BALL_EVENTS = {"Pass", "Shot", "Free Kick", "Others on the ball"}
# Wyscout tag ids (official mapping, figshare 11743818, CC BY 4.0)
GOAL, OWN_GOAL, HEAD, LOST, WON, RED, YELLOW, SECOND_YELLOW, ACCURATE, BLOCKED = 101, 102, 403, 701, 703, 1701, 1702, 1703, 1801, 2101


class DataMissing(FileNotFoundError):
    pass


_EVENTS: dict[str, dict[int, list[dict]]] = {}  # optional per-league cache (memory heavy: tests and batch jobs only)


def clear_cache() -> None:
    _EVENTS.clear()


def _league_events(league: str, match_id: int, cache: bool) -> list[dict]:
    if cache and league in _EVENTS:
        return _EVENTS[league].get(match_id, [])
    with zipfile.ZipFile(DATA / "events.zip") as z:
        allev = json.loads(z.read(f"events_{league}.json"))
    if cache:
        grouped: dict[int, list[dict]] = {}
        for e in allev:
            if e["matchPeriod"] in ("1H", "2H"):
                grouped.setdefault(e["matchId"], []).append(e)
        _EVENTS[league] = grouped
        return grouped.get(match_id, [])
    return [e for e in allev if e["matchId"] == match_id and e["matchPeriod"] in ("1H", "2H")]


def list_matches(league: str) -> list[dict[str, Any]]:
    """Matches of a league as (index, matchday, date): no club names."""
    out = []
    for i, m in enumerate(_matches(league)):
        out.append({"index": i, "id": m["wyId"], "matchday": m.get("gameweek"), "date": str(m.get("dateutc", ""))[:10]})
    return out


def _matches(league: str) -> list[dict[str, Any]]:
    path = DATA / "matches.zip"
    if not path.exists():
        raise DataMissing("Wyscout data not found: run `python tools/fetch_wyscout.py`")
    with zipfile.ZipFile(path) as z:
        return sorted(json.loads(z.read(f"matches_{league}.json")), key=lambda m: (m.get("dateutc", ""), m["wyId"]))


class WyscoutFeed:
    name = "wyscout"

    def __init__(self, league: str = "Spain", index: int = 0, match_id: Optional[int] = None, pseudonymize: bool = True,
                 cache: bool = False):
        if league not in LEAGUES:
            raise ValueError(f"league must be one of {LEAGUES}")
        matches = _matches(league)
        self.match = next((m for m in matches if m["wyId"] == match_id), None) if match_id else matches[index % len(matches)]
        if self.match is None:
            raise ValueError(f"unknown match id {match_id}")
        self.league, self.pseudonymize = league, pseudonymize
        self.raw = list(_league_events(league, self.match["wyId"], cache))
        self.raw.sort(key=lambda e: (e["matchPeriod"], e["eventSec"]))
        sides = {tid: td["side"] for tid, td in self.match["teamsData"].items()}
        self.team_of = {int(tid): ("HOM" if side == "home" else "AWY") for tid, side in sides.items()}
        self.official_score = {("HOM" if td["side"] == "home" else "AWY"): td["score"] for td in self.match["teamsData"].values()}
        self.teams = self._build_teams()
        self.label = f"{league} 2017/18, matchday {self.match.get('gameweek')}"

    # ------------------------------------------------------------------ line-ups
    def _build_teams(self) -> tuple[Team, Team]:
        roles = {p["wyId"]: LINE.get(p["role"]["code2"], "MF")
                 for p in json.loads((DATA / "players.json").read_text(encoding="utf-8"))} if (DATA / "players.json").exists() else {}
        real_names = {}
        if not self.pseudonymize and (DATA / "players.json").exists():
            real_names = {p["wyId"]: p["shortName"] for p in json.loads((DATA / "players.json").read_text(encoding="utf-8"))}
        order: dict[str, list[int]] = {"HOM": [], "AWY": []}
        for tid, td in self.match["teamsData"].items():
            side = self.team_of[int(tid)]
            for p in td["formation"]["lineup"] + td["formation"]["bench"]:
                if p["playerId"] not in order[side]:
                    order[side].append(p["playerId"])
        for e in self.raw:  # anyone who touched the ball but was not listed
            if e["playerId"] and e["playerId"] not in order[self.team_of[e["teamId"]]]:
                order[self.team_of[e["teamId"]]].append(e["playerId"])
        teams = []
        for side, label, short in (("HOM", "Home Team", "HOM"), ("AWY", "Away Team", "AWY")):
            ps = [Player(id=f"P{pid}", name=real_names.get(pid, f"{label.split()[0]} #{k + 1}"), team=side, number=k + 1,
                         position=roles.get(pid, "MF")) for k, pid in enumerate(order[side])]
            teams.append(Team(id=side, name=label if self.pseudonymize else side, short=short, tactic=None, players=ps))
        return teams[0], teams[1]

    # ------------------------------------------------------------------ events
    def ticks(self) -> Iterator[Tick]:
        eid = 0
        score = {"HOM": 0, "AWY": 0}
        poss = "HOM"
        halftime_done = False

        def make(t: float, type_: str, team: str, **kw) -> Event:
            nonlocal eid
            eid += 1
            return Event(id=eid, minute=int(t // 60), second=int(t % 60), type=type_, team=team, **kw)

        def pid_of(e: dict) -> Optional[str]:
            return f"P{e['playerId']}" if e.get("playerId") else None

        yield Tick(0.0, {"t": 0.0, "minute": 0, "poss": poss}, [make(0.0, "kickoff", poss, x=50, y=50)])
        n = len(self.raw)
        first_half_end = max((e["eventSec"] for e in self.raw if e["matchPeriod"] == "1H"), default=float(HALF))
        offset = max(float(HALF), first_half_end + 15.0)  # the running clock includes first-half stoppage time
        for i, e in enumerate(self.raw):
            t = e["eventSec"] + (offset if e["matchPeriod"] == "2H" else 0)
            out: list[Event] = []
            if e["matchPeriod"] == "2H" and not halftime_done:
                halftime_done = True
                ht = first_half_end + 1.0
                yield Tick(ht, {"t": ht, "minute": int(ht // 60), "poss": poss}, [make(ht, "halftime", poss)])
            team = self.team_of[e["teamId"]]
            other = "AWY" if team == "HOM" else "HOM"
            tags = {x["id"] for x in e["tags"]}
            name, sub = e["eventName"], e["subEventName"]
            pid = pid_of(e)
            pos = e.get("positions") or []
            x0, y0 = (pos[0]["x"], pos[0]["y"]) if pos else (50.0, 50.0)
            clamp = lambda v: max(0.0, min(100.0, float(v)))

            if (name in BALL_EVENTS and pid) and team != poss:
                poss = team
                out.append(make(t, "possession_change", team, player=pid, x=clamp(x0), y=clamp(y0), meta={"reason": "feed"}))

            if OWN_GOAL in tags and pid:  # counted for the other team
                score[other] += 1
                out.append(make(t, "goal", other, player=None, x=100.0, y=50.0, meta={"score": dict(score), "own_goal": True}))
            if name == "Pass" and pid:
                end = pos[1] if len(pos) > 1 and pos[1] else None
                x1, y1 = (end["x"], end["y"]) if end else (x0, y0)
                ok = ACCURATE in tags
                receiver = None
                if ok:  # the receiver is the next player of the same team to touch the ball
                    for j in range(i + 1, min(i + 4, n)):
                        nxt = self.raw[j]
                        if nxt["teamId"] == e["teamId"] and nxt["playerId"] and nxt["playerId"] != e["playerId"] \
                                and nxt["eventSec"] - e["eventSec"] < 8 and nxt["matchPeriod"] == e["matchPeriod"]:
                            receiver = f"P{nxt['playerId']}"
                            break
                out.append(make(t, "pass", team, player=pid, x=clamp(x0), y=clamp(y0), end_x=clamp(x1), end_y=clamp(y1),
                                outcome="success" if ok else "fail",
                                meta={"distance_m": round(math.hypot((x1 - x0) * KX, (y1 - y0) * KY), 1), "forward": (x1 - x0) > 3,
                                      "receiver": receiver, "kind": sub}))
            elif (name == "Shot" or (name == "Free Kick" and sub in ("Free kick shot", "Penalty"))) and pid:
                outcome = "goal" if GOAL in tags else "blocked" if BLOCKED in tags else "saved" if ACCURATE in tags else "off_target"
                shot = make(t, "shot", team, player=pid, x=clamp(x0), y=clamp(y0), end_x=100.0, end_y=50.0, outcome=outcome,
                            xg=estimate_xg(x0, y0, penalty=sub == "Penalty", header=HEAD in tags, freekick=sub == "Free kick shot"),
                            meta={"distance_m": round(math.hypot((100 - x0) * KX, (50 - y0) * KY), 1), "xg_estimated": True})
                out.append(shot)
                if outcome == "goal":
                    score[team] += 1
                    out.append(make(t, "goal", team, player=pid, x=clamp(x0), y=clamp(y0), xg=shot.xg,
                                    meta={"score": dict(score), "assist_shot_id": shot.id}))
            elif name == "Duel" and sub == "Ground defending duel" and pid and (WON in tags or LOST in tags):
                out.append(make(t, "tackle", team, player=pid, x=clamp(x0), y=clamp(y0), outcome="won" if WON in tags else "lost"))
            elif name == "Foul" and pid:
                out.append(make(t, "foul", team, player=pid, x=clamp(x0), y=clamp(y0)))
                if RED in tags or SECOND_YELLOW in tags:
                    out.append(make(t, "card", team, player=pid, outcome="red"))
                elif YELLOW in tags:
                    out.append(make(t, "card", team, player=pid, outcome="yellow"))
            elif name == "Save attempt" and pid and GOAL not in tags:  # a keeper beaten by the shot did not save it
                out.append(make(t, "save", team, player=pid, x=clamp(x0), y=clamp(y0)))
            yield Tick(t, {"t": t, "minute": int(t // 60), "poss": poss}, out)

        end = (self.raw[-1]["eventSec"] + offset) if self.raw else 5400.0
        yield Tick(end, {"t": end, "minute": int(end // 60), "poss": poss}, [make(end, "fulltime", poss)])
