"""Tools the agents call: the match engine and the Tactic Lab, exposed as Microsoft Agent Framework function tools.

The same functions are served over MCP by `gamepulse.mcp_server`, so any MCP client (Copilot, Foundry agents, IDEs) can use them.
Every tool returns plain JSON-friendly data with the numbers it is based on: agents must quote these, never invent them.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, Any, Optional

from agent_framework import tool

from ..engine.state import MatchState
from ..models import Team

ROOT = Path(__file__).resolve().parents[2]


class MatchContext:
    """What the match tools can see: the live match state and the line-ups (filled by the running pipeline)."""

    def __init__(self, state: MatchState, home: Team, away: Team):
        self.state, self.home, self.away = state, home, away
        self.teams = {home.id: home, away.id: away}
        self.names = {p.id: p.name for t in (home, away) for p in t.players}
        self.player_team = {p.id: t.id for t in (home, away) for p in t.players}

    def tname(self, tid: str) -> str:
        return self.teams[tid].name if tid in self.teams else tid


# ------------------------------------------------------------------------------------------------ match tools
def match_snapshot(ctx: MatchContext) -> dict[str, Any]:
    s = ctx.state
    poss = s.possession()
    return {
        "minute": s.minute,
        "score": {ctx.tname(t): g for t, g in s.score.items()},
        "possession_pct": {ctx.tname(t): round(v) for t, v in poss.items()},
        "shots": {ctx.tname(t): st.shots for t, st in s.stats.items()},
        "shots_on_target": {ctx.tname(t): st.on_target for t, st in s.stats.items()},
        "expected_goals": {ctx.tname(t): round(st.xg, 2) for t, st in s.stats.items()},
        "pass_accuracy_pct": {ctx.tname(t): st.pass_acc for t, st in s.stats.items()},
        "momentum": {"value": round(s.momentum(), 1), "meaning": f"positive favours {ctx.tname(s.home)}, negative {ctx.tname(s.away)}"},
    }


def key_moments(ctx: MatchContext, last_n: int = 5) -> list[dict[str, Any]]:
    out = []
    for m in ctx.state.moments[-max(1, min(last_n, 20)):]:
        facts = {k: v for k, v in m.facts.items() if isinstance(v, (int, float, str, bool))}
        out.append({"minute": m.minute, "kind": m.kind, "team": ctx.tname(m.team), "player": ctx.names.get(m.player or "", None),
                    "facts": facts, "evidence_event_ids": m.evidence[:8]})
    return out


def find_player(ctx: MatchContext, name: str) -> Optional[str]:
    q = name.lower().strip()
    if q in ctx.names:
        return q
    for pid, n in ctx.names.items():
        if q == n.lower() or q in n.lower() or n.lower().split()[-1] == q:
            return pid
    return None


def player_report(ctx: MatchContext, player: str) -> dict[str, Any]:
    pid = find_player(ctx, player)
    if pid is None:
        return {"error": f"no player called {player!r}", "players": sorted(ctx.names.values())}
    st = ctx.state.player_summary(pid)
    keep = ("passes", "passes_ok", "pass_acc", "shots", "goals", "xg", "avg_pass_difficulty")
    return {"player": ctx.names[pid], "team": ctx.tname(ctx.player_team[pid]),
            "stats": {k: round(v, 2) if isinstance(v, float) else v for k, v in st.items() if k in keep}}


def top_players(ctx: MatchContext, stat: str = "passes", n: int = 3) -> list[dict[str, Any]]:
    stat = stat if stat in ("passes", "shots", "xg", "goals") else "passes"
    rows = [(pid, ctx.state.player_summary(pid).get(stat, 0)) for pid in ctx.names]
    rows.sort(key=lambda r: -r[1])
    return [{"player": ctx.names[p], "team": ctx.tname(ctx.player_team[p]), stat: round(v, 2)} for p, v in rows[:max(1, min(n, 10))]]


def make_match_tools(ctx: MatchContext) -> list:
    """Function tools bound to one live match."""

    @tool(name="match_snapshot")
    def _snapshot() -> dict:
        """Score, minute, possession, shots, expected goals, pass accuracy and momentum of the match being played."""
        return match_snapshot(ctx)

    @tool(name="key_moments")
    def _moments(last_n: Annotated[int, "how many recent moments"] = 5) -> list:
        """The most recent key moments detected by the engine (goals, big chances, momentum swings, tactical shifts) with their facts."""
        return key_moments(ctx, last_n)

    @tool(name="player_report")
    def _player(player: Annotated[str, "player name or surname"]) -> dict:
        """Statistics of one player in this match (passes, accuracy, pass difficulty, shots, xG, goals)."""
        return player_report(ctx, player)

    @tool(name="top_players")
    def _top(stat: Annotated[str, "passes | shots | xg | goals"] = "passes", n: int = 3) -> list:
        """The players leading this match in one statistic."""
        return top_players(ctx, stat, n)

    return [_snapshot, _moments, _player, _top]


# ------------------------------------------------------------------------------------------------ lab tools
def list_tactics() -> list[dict[str, Any]]:
    from ..tactics import PRESETS

    return [{"name": t.name, "formation": t.formation, "line_height": t.line_height, "pressing": t.pressing, "width": t.width,
             "tempo": t.tempo, "directness": t.directness} for t in PRESETS.values()]


def _levels() -> list[str]:
    from ..strength import LEVELS

    return list(LEVELS)


def test_tactic(tactic: str, opponents: Optional[list[str]] = None, level: str = "mid", opponent_level: str = "mid",
                matches: int = 12) -> dict[str, Any]:
    from ..lab import evaluate
    from ..tactics import PRESETS, resolve_tactic

    mine = resolve_tactic(tactic)
    opps = [o for o in (opponents or []) if o in PRESETS] or [p for p in PRESETS if p != mine.name][:4]
    r = evaluate(mine, opps, n=max(4, min(matches, 24)), workers=None, level=level, opponent_level=opponent_level)
    return {"tactic": mine.name, "level": level, "opponent_level": opponent_level, "matches_per_opponent": r["n"],
            "points_per_game": r["overall_ppg"],
            "matchups": [{k: m[k] for k in ("opponent", "win", "draw", "loss", "ppg", "gf", "ga", "xgf", "xga", "possession")} for m in r["matchups"]],
            "diagnosis": [i["text"] for i in r["insights"]]}


def what_if(tactic: str, scenario: str, opponent: str = "Balanced 4-3-3", level: str = "mid", opponent_level: str = "mid",
            matches: int = 12) -> dict[str, Any]:
    from ..lab import what_if as run_what_if
    from ..scenario import describe_rule
    from .interpreter import interpret_scenario

    scn = interpret_scenario(scenario)
    if not scn["rules"]:
        return {"error": "could not understand the scenario", "scenario": scenario}
    r = run_what_if(tactic, scn, [opponent], max(4, min(matches, 24)), 1000, level, opponent_level)
    m = r["matchups"][0]
    return {"tactic": tactic, "opponent": opponent, "scenario": [describe_rule(x) for x in scn["rules"]], "matches": r["n"],
            "points_per_game_before": r["baseline_ppg"], "points_per_game_after": r["scenario_ppg"], "verdict": r["verdict"],
            "goal_diff_before": m["goal_diff_before"], "goal_diff_after": m["goal_diff_after"],
            "win_pct_before": m["win_before"], "win_pct_after": m["win_after"]}


def realism(topic: str = "summary") -> dict[str, Any]:
    f = ROOT / "web" / "realism.json"
    if not f.exists():
        return {"error": "realism report not generated"}
    r = json.loads(f.read_text())
    ok = lambda rows: f"{sum(x['ok'] for x in rows)}/{len(rows)}"
    summary = {"match_totals_within_tolerance": ok(r["totals"]), "pitch_checks_within_tolerance": ok(r["spatial"]),
               "placement_error_m": r["placement"]["model"], "fixed_formation_error_m": r["placement"]["fixed"],
               "known_gaps": [x["label"] for x in r["spatial"] if not x["ok"]], "sources": r["sources"]}
    return r.get(topic, summary) if topic != "summary" else summary


def make_lab_tools() -> list:

    @tool(name="list_tactics")
    def _list() -> list:
        """The preset tactics a coach can test (formation and the five instructions, each 0-1)."""
        return list_tactics()

    @tool(name="test_tactic")
    def _test(tactic: Annotated[str, "tactic name, e.g. 'Possession 4-3-3'"],
              opponents: Annotated[Optional[list[str]], "opponent tactic names; empty = the other presets"] = None,
              level: Annotated[str, "your squad level: title | europe | upper | mid | lower | relegation"] = "mid",
              opponent_level: Annotated[str, "opponents' level, same scale"] = "mid",
              matches: Annotated[int, "simulated matches per opponent (4-40)"] = 12) -> dict:
        """Simulate many matches of a tactic against opponents and return win/draw/loss, goals, xG, possession and a diagnosis."""
        return test_tactic(tactic, opponents, level, opponent_level, matches)

    @tool(name="what_if")
    def _what_if(tactic: Annotated[str, "your tactic name"], scenario: Annotated[str, "the situation in plain words, e.g. 'red card at 30 minutes'"],
                 opponent: Annotated[str, "opponent tactic name"] = "Balanced 4-3-3", level: str = "mid", opponent_level: str = "mid",
                 matches: int = 12) -> dict:
        """Replay the same matches with and without a scenario (red card, injury, tactical change at minute X) and compare."""
        return what_if(tactic, scenario, opponent, level, opponent_level, matches)

    @tool(name="realism")
    def _realism(topic: Annotated[str, "summary | totals | spatial | strength | styles | formations | defending"] = "summary") -> dict:
        """How closely the simulator matches real football (checked against 1,446 real matches and real tracking data)."""
        return realism(topic)

    return [_list, _test, _what_if, _realism]
