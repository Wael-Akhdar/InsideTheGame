"""Shared data models for GamePulse."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

EVENT_TYPES = (
    "kickoff", "pass", "shot", "tackle", "possession_change",
    "pressure", "foul", "card", "goal", "save", "halftime", "fulltime",
)


@dataclass
class Player:
    id: str
    name: str
    team: str
    number: int
    position: str  # GK, DF, MF, FW


@dataclass
class Team:
    id: str
    name: str
    short: str
    style: dict[str, float]  # possession, pressing, directness, finishing (0..1)
    players: list[Player] = field(default_factory=list)


@dataclass
class Event:
    id: int
    minute: int
    second: int
    type: str
    team: str
    player: Optional[str] = None  # player id
    x: float = 50.0  # pitch coords 0..100 (own goal -> opponent goal)
    y: float = 50.0
    end_x: Optional[float] = None
    end_y: Optional[float] = None
    outcome: Optional[str] = None  # success / fail / on_target / off_target / blocked ...
    xg: Optional[float] = None
    speed_kmh: Optional[float] = None  # ball speed for passes/shots
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def clock(self) -> float:
        return self.minute + self.second / 60

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Moment:
    """A key moment detected by the engine, with the evidence that explains it."""
    kind: str  # goal, big_chance, momentum_swing, red_card, pressure_spike, milestone
    minute: int
    team: str
    player: Optional[str]
    score: float  # importance 0..1
    evidence: list[int]  # event ids that justify the moment
    facts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
