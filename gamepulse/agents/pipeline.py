"""Multi-agent pipeline. Each agent has one role and communicates through shared state.

   Event -> StatsAgent -> MomentAgent -> ExplainerAgent -> NarratorAgent -> PersonaAgent -> Overlay

The question-answering agents (match analyst, tactics coach, fact-checker) run on Microsoft Agent Framework in `team.py`;
the engine is exposed as MCP tools by `gamepulse/mcp_server.py`. A narrator sentence that contains a number absent from its
facts is rejected by the same fact-checker and replaced by the template.
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
    # timing and targeting, so a renderer can place the card on a video without knowing our engine
    t: float = 0.0  # match clock in seconds when the card should appear (time of the triggering event)
    duration: float = 8.0  # seconds the card stays on screen
    team: Optional[str] = None
    player: Optional[str] = None
    id: int = 0

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
        if m.kind == "goal" and m.facts.get("own_goal"):
            return f"An own goal: {team} are credited with it ({self.tname(a)} {score[a]}-{score[b]} {self.tname(b)})."
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
        if m.kind == "tactic_change":
            ch = ", ".join(f"{k.replace('_', ' ')} {v if isinstance(v, str) else round(v * 100)}" for k, v in m.facts["changes"].items())
            return f"{team} change their approach ({ch}). Watch the next minutes: shape, pressing and tempo will shift."
        if m.kind == "unlucky":
            f = m.facts
            return (f"{team} lead the expected goals {f['xg_for']:.1f} to {f['xg_against']:.1f} but the score is "
                    f"{self.tname(a)} {score[a]}-{score[b]} {self.tname(b)}. The performance is there; the finishing is not rewarding it yet.")
        if m.kind == "pressing_fade":
            f = m.facts
            return (f"{team}'s pressing has faded: {f['before']} pressing actions per 10 minutes early on, {f['now']} now. "
                    f"Over the same period {self.tname(state.away if m.team == state.home else state.home)}'s pass accuracy moved from "
                    f"{f['opp_acc_before']}% to {f['opp_acc_now']}%, so they get more time on the ball.")
        if m.kind == "key_player":
            f = m.facts
            return (f"{self.pname(m.player)} is involved in {f['share']}% of {team}'s passing over the last 15 minutes "
                    f"(a typical player: about {f['typical']}%). Cutting him off is the quickest way to disrupt {team}.")
        if m.kind == "turning_point":
            f = m.facts
            return (f"Since {f['cause']} at {f['at']}', the expected-goals balance of {team} moved from {f['before']:+.1f} to "
                    f"{f['after']:+.1f} per 10 minutes.")
        if m.kind == "injury":
            return f"{team} lose a key player's mobility - expect gaps on that side and fewer high-intensity runs."
        return "A notable moment in the match."


    def plain(self, m: Moment, state: MatchState) -> Optional[str]:
        """Short fan-friendly wording for the insights that need no numbers; None for the other kinds."""
        team = self.tname(m.team)
        f = m.facts
        return {
            "unlucky": f"{team} are playing better than the score says ({f.get('xg_for', 0):.1f} expected goals to {f.get('xg_against', 0):.1f}) and could be rewarded soon.",
            "pressing_fade": f"{team} are running out of steam: they are pressing much less than earlier.",
            "key_player": f"{self.pname(m.player)} is everywhere: {team}'s game goes through him.",
            "turning_point": (f"The match changed at {f.get('at')}': {team} " +
                              ("are now creating more." if f.get("after", 0) > f.get("before", 0) else "have lost their edge.")),
        }.get(m.kind)


class NarratorAgent(Agent):
    """Turns a moment + explanation into broadcast-ready copy in the viewer's language and mode."""
    name = "narrator"

    def run(self, m: Moment, why: str, v: Viewer, state: MatchState, plain: Optional[str] = None) -> tuple[str, str]:
        player, team = self.pname(m.player), self.tname(m.team)
        headline = {
            "goal": (f"OWN GOAL - {team} are credited" if m.facts.get("own_goal") else f"GOAL! {player} ({team})"), "big_chance": f"Big chance for {player}!",
            "momentum_swing": f"{team} take control", "red_card": f"RED CARD - {player}",
            "tactic_change": f"{team} switch tactics", "injury": f"{player} ({team}) is hurt",
            "unlucky": f"{team}: dominant, not rewarded", "pressing_fade": f"{team}'s pressing is fading",
            "key_player": f"{player} runs {team}'s game", "turning_point": f"Turning point for {team}",
        }.get(m.kind, "Key moment")
        facts = f"{m.kind} at minute {m.minute} by {player} ({team}). {why}"
        if m.player and v.mode == "analyst":
            facts += f" Player stats: {state.player_summary(m.player)}"
        system = (f"You are a Premier League studio commentator. Write 1-2 punchy sentences in {LANGS[v.lang]} "
                  f"for a {MODES[v.mode]}. Use ONLY the given facts, do not invent numbers.")
        body = self.llm.complete(system, facts)
        if body is not None:
            from .team import fact_check  # every number the model writes must be in the facts it was given
            if not fact_check(body, [("facts", facts)], "")["grounded"]:
                body = None
        if body is None:
            body = why if v.mode == "analyst" else (plain or why.split(" (")[0].split(" - ")[0].rstrip(".") + ".")
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
        if v.mode == "casual" and m.kind in ("momentum_swing", "pressing_fade"):
            score -= 0.2  # casual fans want goals and chances, analysts want rhythm and pressing
        return round(min(1.0, score), 2)


class Orchestrator:
    """Runs the agent chain for each incoming event and yields overlays per viewer."""

    def __init__(self, home: Team, away: Team, llm: Optional[LLM] = None):
        teams = {home.id: home, away.id: away}
        self.state = MatchState(home.id, away.id)
        # line-ups are part of any real feed: id, name and line (GK / DF / MF / FW) of every player
        self.state.roster = {p.id: {"name": p.name, "line": p.position} for t in (home, away) for p in t.players}
        llm = llm or LLM()
        self.explainer = ExplainerAgent(llm, teams)
        self.narrator = NarratorAgent(llm, teams)
        self.persona = PersonaAgent(llm, teams)

    def process_tick(self, tick, viewer: Viewer, threshold: float = 0.55) -> list[Overlay]:
        """Feed one simulation tick (frame + events) through the agent chain."""
        if tick.frame:
            self.state.observe_frame(tick.t, tick.frame["poss"])
        overlays: list[Overlay] = []
        for ev in tick.events:
            overlays.extend(self.process(ev, viewer, threshold))
        return overlays

    def process(self, ev: Event, viewer: Viewer, threshold: float = 0.55) -> list[Overlay]:
        moments = self.state.ingest(ev)  # stats + moment detection
        overlays = []
        for m in moments:
            rel = self.persona.relevance(m, viewer)
            if rel < threshold:
                continue
            why = self.explainer.run(m, self.state)
            headline, body = self.narrator.run(m, why, viewer, self.state, self.explainer.plain(m, self.state))
            overlays.append(Overlay(m.minute, m.kind, headline, body, why, m.evidence, rel, viewer.lang, viewer.mode,
                                    t=ev.minute * 60 + ev.second, duration=10.0 if m.score >= 0.8 else 7.0,
                                    team=m.team, player=m.player))
        return overlays
