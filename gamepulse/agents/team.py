"""The GamePulse agent team (Microsoft Agent Framework).

    question -> Router -> Match Analyst  (tools: match_snapshot, key_moments, player_report, top_players)
                       -> Tactics Coach  (tools: list_tactics, test_tactic, what_if, realism)
             -> Fact-checker: every number in the answer must come from a tool result (or the question)

The live overlay chain (stats -> moments -> explainer -> narrator -> persona) lives in `pipeline.py`; its narrator is checked by the
same fact-checker. With no model configured the agents run on the offline planner of `clients.py`: same tools, same checks.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from agent_framework import Agent

from ..tactics import PRESETS
from .clients import backend, make_client
from .tools import MatchContext, make_lab_tools, make_match_tools

LANG_NAMES = {"en": "English", "fr": "French", "es": "Spanish", "ar": "Arabic"}

ANALYST_INSTRUCTIONS = (
    "You are GamePulse's match analyst for a football (soccer) broadcast. Answer the viewer's question about the match being played. "
    "Always call the tools first and quote only numbers they return; never invent a statistic. Two to four sentences, plain words, "
    "explain why it matters. If the tools cannot answer, say so.")
COACH_INSTRUCTIONS = (
    "You are GamePulse's tactics coach assistant. A coach asks how a tactic would do, or what happens if something changes. "
    "Use the simulation tools (test_tactic, what_if, list_tactics) and quote their numbers: points per game, win rate, expected goals. "
    "Say how many simulated matches the answer rests on, give one concrete recommendation, and never present a simulation as a certainty.")

# ------------------------------------------------------------------------------------------------ offline planning
LEVEL_WORDS = [("title", ("title", "top team", "champion", "big team", "much stronger", "best team")),
               ("europe", ("european", "europe", "stronger", "top four", "top 4")),
               ("relegation", ("relegation", "bottom", "much weaker", "small team", "worst")),
               ("lower", ("weaker", "lower half"))]


def _tactics_in(q: str) -> list[str]:
    ql = q.lower()
    hits = []
    for name in PRESETS:
        key = name.lower().rsplit(" ", 1)[0]  # "possession", "low block", "counter-attack", ...
        pos = ql.find(key)
        if pos < 0:
            pos = ql.find(name.lower())
        if pos >= 0:
            hits.append((pos, name))
    return [n for _, n in sorted(hits)]


def _level(q: str) -> Optional[str]:
    ql = q.lower()
    for lvl, words in LEVEL_WORDS:
        if any(w in ql for w in words):
            return lvl
    return None


def analyst_planner(ctx: Optional[MatchContext]):
    def plan(q: str, tools: list[str]) -> list[tuple[str, dict]]:
        ql = q.lower()
        if ctx is not None:
            for pid, name in ctx.names.items():
                if name.lower() in ql or name.split()[-1].lower() in ql.split():
                    return [("player_report", {"player": name})]
        moments = any(w in ql for w in ("moment", "happen", "why", "goal", "chance", "turning", "key", "changed"))
        if any(w in ql for w in ("score", "winning", "on top", "dominat", "possession", "who is better", "stats", "xg", "expected")) \
                and not any(w in ql for w in ("most", "player")):
            return [("match_snapshot", {})] + ([("key_moments", {"last_n": 4})] if moments else [])
        if any(w in ql for w in ("best", "top", "most", "leading", "who has")):
            stat = "shots" if "shot" in ql else "xg" if ("xg" in ql or "expected" in ql) else "goals" if "goal" in ql else "passes"
            return [("top_players", {"stat": stat, "n": 3})]
        if any(w in ql for w in ("moment", "happen", "why", "goal", "chance", "turning", "key", "changed")):
            return [("key_moments", {"last_n": 4}), ("match_snapshot", {})]
        return [("match_snapshot", {})]
    return plan


def coach_planner(hints: dict):
    def plan(q: str, tools: list[str]) -> list[tuple[str, dict]]:
        ql = q.lower()
        named = _tactics_in(q)
        mine = hints.get("tactic") or (named[0] if named else "Balanced 4-3-3")
        others = [n for n in named if n != mine]
        opp_level = _level(q) or hints.get("opponent_level") or "mid"
        level = hints.get("level") or "mid"
        if any(w in ql for w in ("realis", "accurate", "trust", "real data", "how good is the sim")):
            return [("realism", {"topic": "summary"})]
        if any(w in ql for w in ("which tactics", "what tactics", "options", "presets", "list")):
            return [("list_tactics", {})]
        if any(w in ql for w in ("what if", "red card", "injur", "sent off", "if we", "if i", "switch", "change to", "at minute", "minute")):
            return [("what_if", {"tactic": mine, "scenario": q, "opponent": others[0] if others else "Balanced 4-3-3",
                                 "level": level, "opponent_level": opp_level, "matches": 30})]
        return [("test_tactic", {"tactic": mine, "opponents": others or None, "level": level, "opponent_level": opp_level, "matches": 12})]
    return plan


def _pair(d: dict) -> str:
    items = list(d.items())
    return " vs ".join(f"{v}" for _, v in items) if len(items) == 2 else str(d)


def analyst_writer(q: str, results: list[tuple[str, Any]]) -> str:
    if not results:
        return "I could not find match data to answer that."
    out = []
    for name, r in results:
        r = _parse(r)
        if name == "match_snapshot" and isinstance(r, dict) and "score" in r:
            (h, gh), (a, ga) = list(r["score"].items())
            out.append(f"After {r['minute']} minutes it is {h} {gh}-{ga} {a}. Possession {_pair(r['possession_pct'])}%, "
                       f"shots {_pair(r['shots'])}, expected goals {_pair(r['expected_goals'])}, pass accuracy {_pair(r['pass_accuracy_pct'])}%.")
            xg = list(r["expected_goals"].values())
            if abs(xg[0] - xg[1]) >= 0.5:
                lead = list(r["expected_goals"])[0 if xg[0] > xg[1] else 1]
                out.append(f"{lead} are creating the better chances.")
        elif name == "key_moments" and isinstance(r, list):
            if not r:
                out.append("No key moment detected yet.")
            for m in r[-3:]:
                who = m.get("player") or m.get("team")
                out.append(f"{m['minute']}': {m['kind'].replace('_', ' ')} ({who}).")
        elif name == "player_report" and isinstance(r, dict):
            if "error" in r:
                out.append(r["error"])
            else:
                st = r["stats"]
                bits = [f"{int(st[k])} {k}" for k in ("passes", "shots", "goals") if st.get(k)]
                if st.get("pass_acc") is not None and st.get("passes"):
                    bits.append(f"{st['pass_acc']}% pass accuracy")
                if st.get("xg"):
                    bits.append(f"xG {st['xg']}")
                out.append(f"{r['player']} ({r['team']}): " + (", ".join(bits) if bits else "little involvement so far") + ".")
        elif name == "top_players" and isinstance(r, list) and r:
            stat = [k for k in r[0] if k not in ("player", "team")][0]
            val = lambda v: f"{v:g}" if isinstance(v, (int, float)) else v
            out.append(f"Most {stat}: " + ", ".join(f"{x['player']} ({x['team']}) {val(x[stat])}" for x in r) + ".")
    return " ".join(out)


def coach_writer(q: str, results: list[tuple[str, Any]]) -> str:
    if not results:
        return "Tell me which tactic to test (for example 'Possession 4-3-3 against a Low block 5-3-2')."
    out = []
    for name, r in results:
        r = _parse(r)
        if name == "test_tactic" and isinstance(r, dict) and "matchups" in r:
            ms = sorted(r["matchups"], key=lambda m: m["ppg"])
            out.append(f"Over {r['matches_per_opponent']} simulated matches per opponent ({r['level']} level vs {r['opponent_level']} level), "
                       f"{r['tactic']} earns {r['points_per_game']} points per game.")
            best, worst = ms[-1], ms[0]
            line = lambda m: f"{m['win']}% wins, {m['draw']}% draws, xG {m['xgf']} for {m['xga']} against, {m['possession']}% possession"
            if len(ms) == 1:
                out.append(f"Against {best['opponent']}: {line(best)}.")
            else:
                out.append(f"Best against {best['opponent']} ({line(best)}); hardest against {worst['opponent']} ({line(worst)}).")
            if r.get("diagnosis"):
                out.append(r["diagnosis"][0])
        elif name == "what_if" and isinstance(r, dict):
            if "error" in r:
                out.append(f"I could not turn that into a scenario. Try 'red card for us at minute 30'.")
            else:
                out.append(f"Scenario: {'; '.join(r['scenario'])}. Over the same {r['matches']} simulated matches against {r['opponent']}, "
                           f"{r['tactic']} goes from {r['points_per_game_before']} to {r['points_per_game_after']} points per game "
                           f"(wins {r['win_pct_before']}% -> {r['win_pct_after']}%, goal difference {r['goal_diff_before']} -> {r['goal_diff_after']}): "
                           f"the change {r['verdict']}.")
        elif name == "list_tactics" and isinstance(r, list):
            out.append("Presets: " + "; ".join(f"{t['name']} (directness {t['directness']}, pressing {t['pressing']})" for t in r) + ".")
        elif name == "realism" and isinstance(r, dict):
            out.append(f"The simulator matches {r.get('match_totals_within_tolerance')} match totals and {r.get('pitch_checks_within_tolerance')} "
                       f"pitch-location checks of real football; players are placed within {r.get('placement_error_m')} m on average. "
                       f"Known gaps: {', '.join(r.get('known_gaps', [])) or 'none'}.")
    return " ".join(out)


def _parse(r: Any) -> Any:
    if isinstance(r, str):
        try:
            return json.loads(r)
        except ValueError:
            return r
    if isinstance(r, list) and r and hasattr(r[0], "text"):  # list of Content from the framework
        try:
            return json.loads(r[0].text)
        except (ValueError, TypeError):
            return r[0].text
    return r


# ------------------------------------------------------------------------------------------------ fact-checking
_NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?")


def _numbers(obj: Any) -> set[float]:
    text = obj if isinstance(obj, str) else json.dumps(obj, default=str)
    return {float(x) for x in _NUM.findall(text)}


def fact_check(answer: str, results: list[tuple[str, Any]], question: str = "") -> dict[str, Any]:
    """Every number in the answer must appear in a tool result or in the question (small rounding allowed)."""
    known = _numbers(question) | {float(i) for i in range(0, 11)}
    for _, r in results:
        known |= _numbers(_parse(r))
    unsupported = []
    for x in _numbers(answer):
        if not any(abs(x - k) <= max(0.051, 0.006 * abs(k)) or abs(x - round(k)) < 0.01 for k in known):
            unsupported.append(x)
    return {"grounded": not unsupported, "unsupported": sorted(unsupported)}


# ------------------------------------------------------------------------------------------------ team
def route(question: str, ctx: Optional[MatchContext]) -> str:
    ql = question.lower()
    coach_words = ("tactic", "formation", "press", "against", " vs ", "what if", "red card", "test", "lab", "line", "beat", "simulat",
                   "realis", "set up", "4-", "3-", "5-", "should i", "should we")
    if ctx is None or any(w in ql for w in coach_words):
        return "coach"
    return "analyst"


def build_agent(kind: str, ctx: Optional[MatchContext] = None, hints: Optional[dict] = None, lang: str = "en") -> Agent:
    hints = hints or {}
    say = f" Answer in {LANG_NAMES.get(lang, 'English')}."
    if kind == "analyst":
        return Agent(make_client(analyst_planner(ctx), analyst_writer), ANALYST_INSTRUCTIONS + say, name="match_analyst",
                     description="Answers questions about the live match from the engine's statistics.", tools=make_match_tools(ctx))
    extra = f" The coach's current tactic is {hints['tactic']}." if hints.get("tactic") else ""
    return Agent(make_client(coach_planner(hints), coach_writer), COACH_INSTRUCTIONS + extra + say, name="tactics_coach",
                 description="Tests tactics and what-if scenarios with the match simulator.", tools=make_lab_tools())


async def ask(question: str, ctx: Optional[MatchContext] = None, hints: Optional[dict] = None, lang: str = "en") -> dict[str, Any]:
    """Route a question to the right agent, run it (tools included) and fact-check the answer."""
    question = (question or "").strip()[:500]
    kind = route(question, ctx)
    agent = build_agent(kind, ctx, hints, lang)
    used = backend()
    try:
        resp = await agent.run(question)
    except Exception as exc:  # model unavailable (expired Developer deployment, quota, network): same agent, offline planner
        print(f"[agents] {used} failed ({type(exc).__name__}: {str(exc)[:120]}), answering offline")
        from .clients import OfflineChatClient
        planner, writer = (analyst_planner(ctx), analyst_writer) if kind == "analyst" else (coach_planner(hints or {}), coach_writer)
        agent = Agent(OfflineChatClient(planner, writer), ANALYST_INSTRUCTIONS if kind == "analyst" else COACH_INSTRUCTIONS,
                      name=agent.name, tools=make_match_tools(ctx) if kind == "analyst" else make_lab_tools())
        resp = await agent.run(question)
        used = "offline (model unavailable)"
    calls, results = {}, []
    trace = []
    for m in resp.messages:
        for c in m.contents:
            if c.type == "function_call":
                args = c.arguments if isinstance(c.arguments, dict) else json.loads(c.arguments or "{}")
                calls[c.call_id] = c.name
                trace.append({"tool": c.name, "args": args})
            elif c.type == "function_result":
                results.append((calls.get(c.call_id, "?"), c.result))
    answer = resp.text or ""
    check = fact_check(answer, results, question)
    return {"agent": agent.name, "backend": used, "answer": answer, "tools": trace, **check}
