"""GamePulse as an MCP server: the match engine, the Tactic Lab and the agents as tools any MCP client can call
(GitHub Copilot, Microsoft Foundry agents, Claude, IDEs).

    python -m gamepulse.mcp_server                 # stdio (local clients)
    python -m gamepulse.mcp_server --http 8001     # streamable HTTP on http://localhost:8001/mcp

The FastAPI app also mounts the HTTP transport at /mcp, so the deployed demo is an MCP endpoint as well.
"""
from __future__ import annotations

import argparse
from typing import Any, Optional

from mcp.server import MCPServer

from .agents import tools as T

mcp = MCPServer(name="gamepulse", title="GamePulse",
                instructions="Football match intelligence: simulate matches, test tactics against opponents of a chosen level, run what-if "
                             "scenarios, analyse real (pseudonymised) matches and check how realistic the simulator is. Quote the numbers "
                             "the tools return; simulations are averages over many matches, not predictions of a single result.")


@mcp.tool(description="Preset tactics (formation and five instructions between 0 and 1) that can be tested.")
def list_tactics() -> list[dict[str, Any]]:
    return T.list_tactics()


@mcp.tool(description="Simulate a tactic against opponents many times. Levels: title, europe, upper, mid, lower, relegation. "
                      "Returns win/draw/loss, goals, xG, possession per opponent and a diagnosis.")
def test_tactic(tactic: str, opponents: Optional[list[str]] = None, level: str = "mid", opponent_level: str = "mid",
                matches: int = 12) -> dict[str, Any]:
    return T.test_tactic(tactic, opponents, level, opponent_level, matches)


@mcp.tool(description="Replay the same simulated matches with and without a scenario described in plain words "
                      "(e.g. 'red card for us at minute 30', 'switch to 5-4-1 at 70 if we lead').")
def what_if(tactic: str, scenario: str, opponent: str = "Balanced 4-3-3", level: str = "mid", opponent_level: str = "mid",
            matches: int = 24) -> dict[str, Any]:
    return T.what_if(tactic, scenario, opponent, level, opponent_level, matches)


@mcp.tool(description="Play one full simulated match and return the score, statistics and the key moments with their explanations.")
def simulate_match(home_tactic: str = "Possession 4-3-3", away_tactic: str = "Counter-attack 4-4-2", home_level: str = "mid",
                   away_level: str = "mid", seed: int = 42) -> dict[str, Any]:
    from .feed import SimulatorFeed
    from .strength import quality_for

    feed = SimulatorFeed(seed=seed, home_tactic=home_tactic, away_tactic=away_tactic, home_quality=quality_for(home_level),
                         away_quality=quality_for(away_level))
    return _run_feed(feed)


@mcp.tool(description="Analyse a real match from the public Wyscout dataset (league: Spain, Italy, France, Germany; players and clubs "
                      "pseudonymised): score, statistics and the explained key moments.")
def analyse_real_match(league: str = "Spain", match_index: int = 5) -> dict[str, Any]:
    from .feed.wyscout import WyscoutFeed

    return _run_feed(WyscoutFeed(league, match_index))


@mcp.tool(description="How closely the simulator matches real football. topic: summary, totals, spatial, strength, styles, formations, defending.")
def realism(topic: str = "summary") -> dict[str, Any]:
    return T.realism(topic)


@mcp.tool(description="Ask the GamePulse agents a tactics question in plain words; returns the answer, the tools used and the fact-check.")
async def ask_coach(question: str, tactic: Optional[str] = None, lang: str = "en") -> dict[str, Any]:
    from .agents.team import ask

    return await ask(question, None, {"tactic": tactic} if tactic else {}, lang)


def _run_feed(feed) -> dict[str, Any]:
    from .agents.pipeline import Orchestrator, Viewer

    orch = Orchestrator(*feed.teams)
    cards = []
    for tk in feed.ticks():
        cards += [o.to_dict() for o in orch.process_tick(tk, Viewer(mode="analyst"))]
    ctx = T.MatchContext(orch.state, *feed.teams)
    return {"label": getattr(feed, "label", feed.name), **T.match_snapshot(ctx),
            "key_moments": [{"minute": c["at_minute"], "kind": c["kind"], "headline": c["headline"], "why": c["explanation"]} for c in cards]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", type=int, default=0, help="serve streamable HTTP on this port instead of stdio")
    a = ap.parse_args()
    if a.http:
        mcp.run("streamable-http", port=a.http)
    else:
        mcp.run("stdio")


if __name__ == "__main__":
    main()
