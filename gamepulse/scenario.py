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


_W = {  # words of the scenario descriptions, per language
    "en": {"you": "your team", "opp": "the opponent", "trailing": "is trailing", "not_ahead": "is not ahead", "leading": "is leading",
           "not_behind": "is not behind", "if": "if", "red": "red card for {w}", "goal": "goal for {w}", "injury": "injury to a player of {w}",
           "fatigue": "{w} tire (+{p}% fatigue)", "change": "{w} change", "min": "{m}'",
           "keys": {"line_height": "line height", "pressing": "pressing", "width": "width", "tempo": "tempo", "directness": "directness", "formation": "formation"}},
    "fr": {"you": "votre équipe", "opp": "l'adversaire", "trailing": "est menée", "not_ahead": "ne mène pas", "leading": "mène",
           "not_behind": "n'est pas menée", "if": "si", "red": "carton rouge pour {w}", "goal": "but pour {w}", "injury": "blessure d'un joueur de {w}",
           "fatigue": "{w} fatigue (+{p} % de fatigue)", "change": "{w} change", "min": "{m}e min",
           "keys": {"line_height": "hauteur du bloc", "pressing": "pressing", "width": "largeur", "tempo": "tempo", "directness": "jeu direct", "formation": "système"}},
    "es": {"you": "tu equipo", "opp": "el rival", "trailing": "va perdiendo", "not_ahead": "no va ganando", "leading": "va ganando",
           "not_behind": "no va perdiendo", "if": "si", "red": "tarjeta roja para {w}", "goal": "gol de {w}", "injury": "lesión de un jugador de {w}",
           "fatigue": "{w} se cansa (+{p}% de fatiga)", "change": "{w} cambia", "min": "min {m}",
           "keys": {"line_height": "altura de la línea", "pressing": "presión", "width": "amplitud", "tempo": "ritmo", "directness": "juego directo", "formation": "sistema"}},
    "ar": {"you": "فريقك", "opp": "المنافس", "trailing": "متأخر", "not_ahead": "غير متقدم", "leading": "متقدم", "not_behind": "غير متأخر",
           "if": "إذا كان", "red": "بطاقة حمراء لـ{w}", "goal": "هدف لـ{w}", "injury": "إصابة لاعب من {w}", "fatigue": "إرهاق {w} (+{p}%)",
           "change": "{w} يغيّر", "min": "الدقيقة {m}",
           "keys": {"line_height": "ارتفاع الخط", "pressing": "الضغط", "width": "العرض", "tempo": "الإيقاع", "directness": "اللعب المباشر", "formation": "الخطة"}},
}


def describe_rule(r: dict[str, Any], lang: str = "en") -> str:
    """One scenario rule in plain words, in English, French, Spanish or Arabic."""
    w = _W.get(lang, _W["en"])
    a, t = r["action"], r["trigger"]
    who = w["you"] if a["team"] == "home" else w["opp"]
    when = w["min"].format(m=t["minute"])
    if "if" in t:
        c = t["if"]
        cw = w["you"] if c["team"] == "home" else w["opp"]
        if "score_diff_lte" in c:
            when += f" {w['if']} {cw} {w['trailing'] if c['score_diff_lte'] < 0 else w['not_ahead']} (≤ {c['score_diff_lte']})"
        if "score_diff_gte" in c:
            when += f" {w['if']} {cw} {w['leading'] if c['score_diff_gte'] > 0 else w['not_behind']} (≥ {c['score_diff_gte']})"
    player = f" ({a['player']})" if a.get("player") else ""
    if a["type"] == "tactic_change":
        what = w["change"].format(w=who) + ": " + ", ".join(
            f"{w['keys'].get(k, k)} → {v if isinstance(v, str) else round(v * 100)}" for k, v in a.get("changes", {}).items())
    elif a["type"] == "fatigue":
        what = w["fatigue"].format(w=who, p=round(a.get("amount", 0) * 100))
    else:
        what = w[{"red_card": "red", "goal": "goal", "injury": "injury"}[a["type"]]].format(w=who) + (player if a["type"] != "goal" else "")
    return f"{when} · {what}"


SCENARIO_NAMES = {  # preset names shown in the selector, per language
    "Red card for us at 30'": {"fr": "Carton rouge pour nous à la 30e", "es": "Roja para nosotros en el 30", "ar": "بطاقة حمراء لنا في الدقيقة 30"},
    "Opponent sees red at 55'": {"fr": "Rouge pour l'adversaire à la 55e", "es": "Roja para el rival en el 55", "ar": "بطاقة حمراء للمنافس في الدقيقة 55"},
    "Going 2-0 down early": {"fr": "Mené 2-0 très tôt", "es": "Perder 2-0 pronto", "ar": "التأخر 2-0 مبكراً"},
    "All-out attack when trailing (from 65')": {"fr": "Tout pour l'attaque si on est mené (dès la 65e)", "es": "Todo al ataque si perdemos (desde el 65)",
                                                "ar": "هجوم شامل عند التأخر (من الدقيقة 65)"},
    "Opponent parks the bus from 60'": {"fr": "L'adversaire gare le bus dès la 60e", "es": "El rival aparca el autobús desde el 60",
                                        "ar": "المنافس يتكتل دفاعياً من الدقيقة 60"},
    "Key defender injured at 40'": {"fr": "Défenseur clé blessé à la 40e", "es": "Defensa clave lesionado en el 40", "ar": "إصابة مدافع أساسي في الدقيقة 40"},
}


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
