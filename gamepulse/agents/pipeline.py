"""Multi-agent pipeline. Each agent has one role and communicates through shared state.

   Event -> StatsAgent -> MomentAgent -> ExplainerAgent -> NarratorAgent -> PersonaAgent -> Overlay

TODO(team): swap the plain-Python orchestrator for Microsoft Agent Framework (same agent roles),
and register the engine as MCP tools for the Foundry-hosted agents.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..engine.state import MatchState
from ..models import Event, Moment, Team
from .llm import LLM

LANGS = {"en": "English", "fr": "French", "es": "Spanish", "ar": "Arabic"}
MODES = {"casual": "casual fan", "analyst": "data-hungry analyst"}


@dataclass
class Viewer:
    mode: str = "casual"
    lang: str = "en"
    favorite_team: Optional[str] = None
    focus_player: Optional[str] = None  # player id -> "follow this player" mode


@dataclass
class Overlay:
    """Machine-readable, timestamped card that a broadcast renderer can place on screen."""
    at_minute: int
    kind: str
    headline: str
    body: str
    explanation: str
    evidence: list[int]
    importance: float
    lang: str
    mode: str

    def to_dict(self):
        return self.__dict__.copy()


class Agent:
    name = "agent"

    def __init__(self, llm: LLM, teams: dict[str, Team]):
        self.llm, self.teams = llm, teams
        self.names = {p.id: p.name for t in teams.values() for p in t.players}

    def pname(self, pid: Optional[str]) -> str:
        return self.names.get(pid or "", "the team")

    def tname(self, tid: str) -> str:
        return self.teams[tid].name


class ExplainerAgent(Agent):
    """Explains WHY a moment matters, grounded in evidence from the match state."""
    name = "explainer"

    def run(self, m: Moment, state: MatchState) -> str:
        score = state.score
        a, b = list(score)
        diff = score[m.team] - score[a if m.team == b else b]
        team = self.tname(m.team)
        cvc = state.control_vs_chaos()
        if m.kind == "goal":
            ctx = "levels the match" if diff == 0 else ("puts them ahead" if diff == 1 else
                  ("extends the lead" if diff > 1 else "pulls one back"))
            xg = m.facts.get("xg") or 0
            luck = "against the odds" if xg < 0.12 else ("from a high-quality chance" if xg > 0.3 else "from a decent chance")
            return f"The goal {ctx} for {team} ({self.tname(a)} {score[a]}-{score[b]} {self.tname(b)}), scored {luck} (xG {xg:.2f})."
        if m.kind == "big_chance":
            return (f"A {m.facts['xg']:.2f} xG chance - scoring probability this high is usually converted "
                    f"more than 1 time in 4. It was {m.facts['outcome'].replace('_', ' ')}.")
        if m.kind == "momentum_swing":
            f = m.facts
            return (f"Momentum moved from {f['before']:+.0f} to {f['after']:+.0f} within minutes: {team} now dominate "
                    f"territory and pressure. Play is {cvc['control']:.0f}% controlled vs {cvc['chaos']:.0f}% turnovers.")
        if m.kind == "red_card":
            return f"{team} are down to ten men - expect a deeper block and fewer attacks from them."
        return "A notable moment in the match."


class NarratorAgent(Agent):
    """Turns a moment + explanation into broadcast-ready copy in the viewer's language and mode."""
    name = "narrator"

    def run(self, m: Moment, why: str, v: Viewer, state: MatchState) -> tuple[str, str]:
        player, team = self.pname(m.player), self.tname(m.team)
        headline = {
            "goal": f"GOAL! {player} ({team})", "big_chance": f"Big chance for {player}!",
            "momentum_swing": f"{team} take control", "red_card": f"RED CARD - {player}",
        }.get(m.kind, "Key moment")
        facts = f"{m.kind} at minute {m.minute} by {player} ({team}). {why}"
        if m.player and v.mode == "analyst":
            facts += f" Player stats: {state.player_summary(m.player)}"
        system = (f"You are a Premier League studio commentator. Write 1-2 punchy sentences in {LANGS[v.lang]} "
                  f"for a {MODES[v.mode]}. Use ONLY the given facts, do not invent numbers.")
        body = self.llm.complete(system, facts)
        if body is None:
            body = why if v.mode == "analyst" else why.split(" (")[0].split(" - ")[0].rstrip(".") + "."
        return headline, body


class PersonaAgent(Agent):
    """Personalization: decides whether a moment is relevant for this viewer and re-ranks it."""
    name = "persona"

    def relevance(self, m: Moment, v: Viewer) -> float:
        score = m.score
        if v.favorite_team and m.team == v.favorite_team:
            score += 0.15
        if v.focus_player:
            score = 1.0 if m.player == v.focus_player else score * 0.5
        if v.mode == "casual" and m.kind == "momentum_swing":
            score -= 0.2  # casual fans want goals and chances, analysts want rhythm
        return round(min(1.0, score), 2)


class Orchestrator:
    """Runs the agent chain for each incoming event and yields overlays per viewer."""

    def __init__(self, home: Team, away: Team, llm: Optional[LLM] = None):
        teams = {home.id: home, away.id: away}
        self.state = MatchState(home.id, away.id)
        llm = llm or LLM()
        self.explainer = ExplainerAgent(llm, teams)
        self.narrator = NarratorAgent(llm, teams)
        self.persona = PersonaAgent(llm, teams)

    def process(self, ev: Event, viewer: Viewer, threshold: float = 0.55) -> list[Overlay]:
        moments = self.state.ingest(ev)  # stats + moment detection
        overlays = []
        for m in moments:
            rel = self.persona.relevance(m, viewer)
            if rel < threshold:
                continue
            why = self.explainer.run(m, self.state)
            headline, body = self.narrator.run(m, why, viewer, self.state)
            overlays.append(Overlay(m.minute, m.kind, headline, body, why, m.evidence, rel, viewer.lang, viewer.mode))
        return overlays
