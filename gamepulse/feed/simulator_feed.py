"""The simulator seen through the event contract."""
from __future__ import annotations

from typing import Iterator, Optional

from ..models import Team, Tick
from ..simulator.match import MatchSimulator


class SimulatorFeed:
    """Wraps a MatchSimulator. `sim` stays reachable for live coaching (tactic changes, scenarios), but the
    analysis pipeline only receives what the contract allows."""

    name = "simulator"

    def __init__(self, sim: Optional[MatchSimulator] = None, **kwargs):
        self.sim = sim or MatchSimulator(**kwargs)
        self.teams: tuple[Team, Team] = (self.sim.home, self.sim.away)

    def ticks(self) -> Iterator[Tick]:
        return self.sim.ticks()
