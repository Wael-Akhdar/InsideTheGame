"""Scenarios: scripted situations a coach wants to test ("red card at 30'", "2-0 down early", "park the bus from 60'").

A scenario is a list of rules.  Each rule = trigger (minute + optional condition) -> action.  It is plain JSON, so it can
be built by hand, picked from presets, or written by an LLM from free text (see agents/interpreter.py).

    {"name": "...", "rules": [
        {"trigger": {"minute": 30, "if": {"team": "home", "score_diff_lte": -1}},
         "action": {"type": "tactic_change", "team": "home", "changes": {"pressing": 0.9, "formation": "4-2-4"}}}
    ]}

"home" means the coach's team (in the Tactic Lab it is the team being tested, whichever side it plays on).
"""
from __future__ import annotations

import copy
from typing import Any

from .tactics import INSTRUCTIONS, get_formation

ACTIONS = ("red_card", "goal", "tactic_change", "injury", "fatigue")
TEAMS = ("home", "away")
MAX_RULES = 12


def _team(v: Any, default: str = "home") -> str:
    return v if v in TEAMS else default


def sanitize_rule(r: Any) -> dict[str, Any] | None:
    if not isinstance(r, dict):
        return None
    trig, act = r.get("trigger") or {}, r.get("action") or {}
    typ = act.get("type")
    if typ not in ACTIONS:
        return None
    try:
        minute = max(0, min(95, int(float(trig.get("minute", 0)))))
    except (TypeError, ValueError):
        minute = 0
    trigger: dict[str, Any] = {"minute": minute}
    cond = trig.get("if")
    if isinstance(cond, dict):
        c: dict[str, Any] = {"team": _team(cond.get("team"))}
        for k in ("score_diff_lte", "score_diff_gte"):
            if k in cond:
                try:
                    c[k] = int(cond[k])
                except (TypeError, ValueError):
                    pass
        if len(c) > 1:
            trigger["if"] = c
    action: dict[str, Any] = {"type": typ, "team": _team(act.get("team"))}
    if typ in ("red_card", "injury") and act.get("player"):
        action["player"] = str(act["player"])[:8]  # formation slot, e.g. "LCB"; otherwise random
    if typ == "fatigue":
        try:
            action["amount"] = max(0.0, min(0.3, float(act.get("amount", 0.15))))
        except (TypeError, ValueError):
            action["amount"] = 0.15
    if typ == "tactic_change":
        ch = act.get("changes") if isinstance(act.get("changes"), dict) else {}
        clean: dict[str, Any] = {}
        for k in INSTRUCTIONS:
            if k in ch:
                try:
                    clean[k] = max(0.0, min(1.0, float(ch[k])))
                except (TypeError, ValueError):
                    pass
        if isinstance(ch.get("formation"), str) and get_formation(ch["formation"]):
            clean["formation"] = ch["formation"]
        if not clean:
            return None
        action["changes"] = clean
    return {"trigger": trigger, "action": action}


def sanitize(obj: Any, name: str = "Custom scenario") -> dict[str, Any]:
    """Validate and clamp a scenario coming from the UI or from an LLM. Invalid rules are dropped."""
    if isinstance(obj, list):
        obj = {"rules": obj}
    obj = obj if isinstance(obj, dict) else {}
    rules = [x for x in (sanitize_rule(r) for r in (obj.get("rules") or [])[:MAX_RULES]) if x]
    return {"name": str(obj.get("name") or name)[:60], "rules": sorted(rules, key=lambda r: r["trigger"]["minute"])}


def mirror(scn: dict[str, Any]) -> dict[str, Any]:
    """Swap home/away (used when the coach's team plays away in the Tactic Lab)."""
    out = copy.deepcopy(scn)
    flip = {"home": "away", "away": "home"}
    for r in out["rules"]:
        r["action"]["team"] = flip[r["action"]["team"]]
        if "if" in r["trigger"]:
            r["trigger"]["if"]["team"] = flip[r["trigger"]["if"]["team"]]
    return out


def describe_rule(r: dict[str, Any]) -> str:
    a, t = r["action"], r["trigger"]
    who = "your team" if a["team"] == "home" else "the opponent"
    when = f"{t['minute']}'"
    if "if" in t:
        c = t["if"]
        cw = "your team" if c["team"] == "home" else "the opponent"
        if "score_diff_lte" in c:
            when += f" if {cw} {'is trailing' if c['score_diff_lte'] < 0 else 'is not ahead'} (diff ≤ {c['score_diff_lte']})"
        if "score_diff_gte" in c:
            when += f" if {cw} {'is leading' if c['score_diff_gte'] > 0 else 'is not behind'} (diff ≥ {c['score_diff_gte']})"
    what = {"red_card": f"red card for {who}" + (f" ({a['player']})" if a.get("player") else ""),
            "goal": f"goal for {who}", "injury": f"injury to a player of {who}" + (f" ({a['player']})" if a.get("player") else ""),
            "fatigue": f"{who} tire (+{round(a.get('amount', 0) * 100)}% fatigue)",
            "tactic_change": f"{who} change: " + ", ".join(f"{k} → {v if isinstance(v, str) else round(v * 100)}" for k, v in a.get("changes", {}).items())}[a["type"]]
    return f"{when} · {what}"


PRESET_SCENARIOS: dict[str, dict[str, Any]] = {
    "Red card for us at 30'": {"rules": [{"trigger": {"minute": 30}, "action": {"type": "red_card", "team": "home"}}]},
    "Opponent sees red at 55'": {"rules": [{"trigger": {"minute": 55}, "action": {"type": "red_card", "team": "away"}}]},
    "Going 2-0 down early": {"rules": [{"trigger": {"minute": 12}, "action": {"type": "goal", "team": "away"}},
                                        {"trigger": {"minute": 27}, "action": {"type": "goal", "team": "away"}}]},
    "All-out attack when trailing (from 65')": {"rules": [
        {"trigger": {"minute": 65, "if": {"team": "home", "score_diff_lte": -1}},
         "action": {"type": "tactic_change", "team": "home", "changes": {"pressing": 0.95, "line_height": 0.95, "tempo": 0.9, "directness": 0.7, "formation": "3-4-3"}}}]},
    "Opponent parks the bus from 60'": {"rules": [
        {"trigger": {"minute": 60}, "action": {"type": "tactic_change", "team": "away", "changes": {"line_height": 0.1, "pressing": 0.15, "width": 0.3, "formation": "5-4-1"}}}]},
    "Key defender injured at 40'": {"rules": [{"trigger": {"minute": 40}, "action": {"type": "injury", "team": "home", "player": "LCB"}}]},
}
PRESET_SCENARIOS = {k: sanitize(v, k) for k, v in PRESET_SCENARIOS.items()}
