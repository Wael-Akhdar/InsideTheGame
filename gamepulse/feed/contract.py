"""The event contract: the ONLY thing the analysis pipeline knows about a match.

Any source (our simulator, a real data provider) must produce a `Feed`: two `Team` line-ups and a stream of `Tick`s.
The pipeline never looks behind the feed, so what works on simulated matches works on real ones. See docs/EVENT_CONTRACT.md.
"""
from __future__ import annotations

from typing import Iterable, Iterator, Optional, Protocol

from ..models import EVENT_TYPES, Event, Team, Tick

OUTCOMES = {
    "pass": {"success", "fail"},
    "shot": {"goal", "saved", "blocked", "off_target"},
    "tackle": {"won", "lost"},
    "dribble": {"success", "fail"},
    "card": {"red", "yellow"},
}
LINES = {"GK", "DF", "MF", "FW"}


class ContractError(ValueError):
    """An event or line-up broke the contract."""


class Feed(Protocol):
    """A match source. `teams` is (home, away); `ticks()` yields chronological ticks."""

    name: str
    teams: tuple[Team, Team]

    def ticks(self) -> Iterator[Tick]: ...


def validate_event(e: Event, team_ids: Optional[set[str]] = None) -> list[str]:
    """Return the list of problems with one event (empty = valid)."""
    bad: list[str] = []
    if e.type not in EVENT_TYPES:
        bad.append(f"unknown type {e.type!r}")
    if team_ids is not None and e.team not in team_ids:
        bad.append(f"unknown team {e.team!r}")
    if not (0 <= e.minute <= 130 and 0 <= e.second < 60):
        bad.append(f"bad time {e.minute}:{e.second}")
    for name in ("x", "y", "end_x", "end_y"):
        v = getattr(e, name)
        if v is not None and not (0.0 <= v <= 100.0):
            bad.append(f"{name}={v} outside the 0-100 pitch")
    allowed = OUTCOMES.get(e.type)
    if allowed and e.outcome not in allowed:
        bad.append(f"{e.type} outcome {e.outcome!r} not in {sorted(allowed)}")
    if e.type in ("pass", "shot", "tackle", "foul", "card", "goal", "save") and not e.player and not e.meta.get("own_goal"):
        bad.append(f"{e.type} without a player")
    if e.xg is not None and not (0.0 <= e.xg <= 1.0):
        bad.append(f"xg={e.xg} outside 0-1")
    return bad


def validate_stream(feed: Feed, ticks: Optional[Iterable[Tick]] = None, limit: int = 20) -> None:
    """Raise ContractError describing the first problems found in the whole stream."""
    home, away = feed.teams
    ids = {home.id, away.id}
    players = {p.id: p for t in (home, away) for p in t.players}
    problems: list[str] = []
    last_id, last_clock = 0, -1.0
    for tk in ticks if ticks is not None else feed.ticks():
        for e in tk.events:
            for p in validate_event(e, ids):
                problems.append(f"event {e.id}: {p}")
            if e.player and e.player not in players:
                problems.append(f"event {e.id}: player {e.player!r} not in the line-ups")
            if e.id <= last_id:
                problems.append(f"event {e.id}: ids must increase (previous {last_id})")
            if e.clock + 1e-6 < last_clock:
                problems.append(f"event {e.id}: goes back in time ({e.clock:.2f} < {last_clock:.2f})")
            last_id, last_clock = e.id, max(last_clock, e.clock)
        fp = tk.frame.get("p") if tk.frame else None
        if fp is not None:  # player positions are optional, but when present they must be complete and on the pitch
            if len(fp) != 22 or not all(0 <= x <= 100 and 0 <= y <= 100 for x, y in fp):
                problems.append(f"tick at {tk.t}: frame needs 22 positions inside the pitch")
            slot_ids = tk.frame.get("ids")
            if slot_ids is not None and (len(slot_ids) != 22 or any(i and i not in players for i in slot_ids)):
                problems.append(f"tick at {tk.t}: frame ids must list 22 known players (or empty slots)")
        if tk.frame and tk.frame.get("poss") not in (None, home.id, away.id):
            problems.append(f"tick at {tk.t}: unknown possession team {tk.frame['poss']!r}")
        if len(problems) >= limit:
            break
    bad_lines = [p.id for p in players.values() if p.position not in LINES]
    if bad_lines:
        problems.append(f"players with an invalid line: {bad_lines[:5]}")
    if problems:
        raise ContractError("; ".join(problems[:limit]))
