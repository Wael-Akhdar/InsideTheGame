"""Agents run offline (no model key): routing, tool calls, fact-checking, MCP tools."""
import asyncio

from gamepulse.agents.pipeline import Orchestrator, Viewer
from gamepulse.agents.team import ask, fact_check, route
from gamepulse.agents.tools import MatchContext
from gamepulse.feed import SimulatorFeed


def _ctx(minutes=60):
    feed = SimulatorFeed(seed=3)
    orch = Orchestrator(*feed.teams)
    for tk in feed.ticks():
        orch.process_tick(tk, Viewer())
        if tk.t > minutes * 60:
            break
    return MatchContext(orch.state, *feed.teams)


def test_fact_check_flags_invented_numbers():
    res = [("match_snapshot", {"shots": {"A": 9, "B": 4}, "xg": {"A": 1.23}})]
    assert fact_check("A have 9 shots and 1.2 xG.", res)["grounded"]
    bad = fact_check("A have 17 shots.", res)
    assert not bad["grounded"] and bad["unsupported"] == [17.0]
    assert fact_check("Ils prennent 1,67 point par match.", [("t", {"ppg": 1.67})])["grounded"]  # decimal comma


def test_routing():
    ctx = _ctx(20)
    assert route("Who is on top?", ctx) == "analyst"
    assert route("How does Possession 4-3-3 do against a low block?", ctx) == "coach"
    assert route("Who is on top?", None) == "coach"  # no live match: only the coach can answer


def test_analyst_answers_from_tools():
    ctx = _ctx()
    r = asyncio.run(ask("Who is on top, and what were the key moments?", ctx))
    assert r["agent"] == "match_analyst" and r["grounded"]
    assert {t["tool"] for t in r["tools"]} >= {"match_snapshot", "key_moments"}
    assert "minutes" in r["answer"]


def test_coach_runs_the_lab():
    r = asyncio.run(ask("How does Low block 5-3-2 do against Possession 4-3-3 of a title contender?", None, {}))
    assert r["agent"] == "tactics_coach" and r["grounded"]
    call = r["tools"][0]
    assert call["tool"] == "test_tactic" and call["args"]["tactic"] == "Low block 5-3-2"
    assert call["args"]["opponents"] == ["Possession 4-3-3"] and call["args"]["opponent_level"] == "title"
    assert "points per game" in r["answer"]


def test_mcp_server_lists_the_tools():
    from gamepulse.mcp_server import mcp
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"test_tactic", "what_if", "simulate_match", "analyse_real_match", "realism", "ask_coach"} <= names
