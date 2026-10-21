"""Interpreter agent: turns a coach's plain-language instructions into simulator parameters.

    "Winger: stay wide, beat his man and cross, don't track back"  ->  role parameters
    "Red card for my centre-back at 30', then we press high"        ->  scenario rules

With Azure OpenAI / Foundry configured the LLM does the translation; its JSON is always validated and clamped, so
it can never push the simulator out of range.  Without credentials a keyword parser (EN/FR) gives a usable result.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from ..scenario import describe_rule, sanitize
from ..tactics import INSTRUCTIONS, ROLE_PARAMS, ROLES, get_formation, sanitize_role
from .llm import LLM

_ROLE_SYSTEM = f"""You translate a football coach's description of ONE player's job into numeric role parameters.
Parameters (all numbers): ax = how far forward he pushes when his team has the ball (-20 stays deep .. 25 bursts forward),
dx = shift when the team defends (-10 drops deeper .. 10 steps up), spread = width (0.6 inside .. 1.4 hugging touchline),
dr = dribbling tendency (0 never .. 2 always), sh = shooting tendency (0 .. 2), fw = preference for forward passes (-0.4 .. 0.6),
pr = pressing willingness (0 .. 2), sf = safe passing preference (-0.2 .. 0.5).
Typical values for reference: {', '.join(f"{k}={ {p: ROLES[k][p] for p in ROLE_PARAMS} }" for k in ('winger', 'anchor', 'poacher'))}.
Return JSON: {{"label": "<=4 words", "summary": "one sentence in the coach's language: what you understood", "params": {{...all 8 numbers...}}}}."""

_SCENARIO_SYSTEM = f"""You translate a football coach's imagined situation into scenario rules for a match simulator.
Output JSON {{"name": "...", "rules": [rule, ...]}} where rule = {{"trigger": {{"minute": 0-95, "if": optional
{{"team": "home|away", "score_diff_lte": int, "score_diff_gte": int}}}}, "action": action}}.
"home" is the coach's team, "away" the opponent. score_diff = goals of `team` minus goals of the other team.
Actions: {{"type":"red_card","team":..,"player": optional slot like "LCB"}}, {{"type":"goal","team":..}}, {{"type":"injury","team":..,"player": optional slot}},
{{"type":"fatigue","team":..,"amount":0-0.3}}, {{"type":"tactic_change","team":..,"changes":{{any of {list(INSTRUCTIONS)} as 0-1 numbers, and/or "formation": "4-2-3-1"}}}}.
"Going all out", "park the bus", "press high" are tactic_change rules. Use at most 8 rules. Only use what the coach says.
Also add "summary": one or two sentences, in the language requested, telling the coach what you understood and what will happen."""


# ----------------------------------------------------------------------------- roles
def _keyword_role(text: str, line: str) -> dict[str, float]:
    t = text.lower()
    p = {"ax": {"GK": 0, "DF": 4, "MF": 8, "FW": 6}[line], "dx": 0.0, "spread": 1.0, "dr": 1.0,
         "sh": {"GK": 0.0, "DF": 0.2, "MF": 0.7, "FW": 1.0}[line], "fw": 0.1, "pr": 1.0, "sf": 0.1}
    has = lambda *w: any(re.search(w_, t) for w_ in w)
    if has(r"\bwide\b", r"touch", r"largeur", r"ailier", r"côté", r"cote\b", r"hug"):
        p["spread"] += 0.2
    if has(r"inside", r"cut in", r"\baxe\b", r"rentre", r"half.?space", r"narrow"):
        p["spread"] -= 0.25; p["sh"] += 0.4
    if has(r"overlap", r"attack", r"push", r"monte", r"offens", r"advanced", r"forward run", r"get forward", r"burst"):
        p["ax"] += 10
    if has(r"stay back", r"stay deep", r"\bdeep\b", r"défens", r"defensive", r"reste", r"cover", r"couvr", r"protect", r"prot[eè]ge", r"don'?t (go|push)", r"hold (the )?position", r"sit"):
        p["ax"] -= 9; p["dx"] -= 3; p["sf"] += 0.3; p["sh"] -= 0.2
    if has(r"(don'?t|do not|never|no need to) track back", r"ne (redescend|replie) pas", r"stay(s)? high", r"stay(s)? up"):
        p["dx"] += 4; p["ax"] += 3
    if has(r"press", r"harcel", r"hunt", r"chase", r"win it back", r"aggress"):
        p["pr"] += 0.5
    if has(r"don'?t press", r"no press", r"ne presse pas", r"conserve energy", r"save energy"):
        p["pr"] -= 0.7
    if has(r"shoot", r"\btir", r"finish", r"score", r"\bbut", r"goal", r"poach", r"marque", r"frappe"):
        p["sh"] += 0.6
    if has(r"dribbl", r"1v1", r"one.on.one", r"take on", r"beat (his|the) man", r"percu", r"débord", r"pace", r"speed"):
        p["dr"] += 0.6
    if has(r"long ball", r"vertical", r"direct", r"profondeur", r"through ball", r"penetrat", r"forward pass", r"cross"):
        p["fw"] += 0.3
    if has(r"short", r"safe", r"simple", r"keep possession", r"conserve", r"circulat", r"recycle", r"retain"):
        p["sf"] += 0.3; p["fw"] -= 0.15
    if has(r"playmak", r"creat", r"vision", r"dictate", r"tempo", r"distribut", r"orchestr"):
        p["fw"] += 0.2; p["sh"] += 0.1
    return p


LANG_NAMES = {"en": "English", "fr": "French", "es": "Spanish", "ar": "Arabic"}
_OFFLINE = {"en": "Understood from keywords only (the AI model is not connected).", "fr": "Compris par mots-clés uniquement (le modèle d'IA n'est pas connecté).",
            "es": "Entendido solo por palabras clave (el modelo de IA no está conectado).", "ar": "فُهم عبر الكلمات المفتاحية فقط (نموذج الذكاء الاصطناعي غير متصل)."}


def interpret_role(text: str, line: str = "MF", llm: Optional[LLM] = None, lang: str = "en") -> dict[str, Any]:
    """Description -> sanitized role dict (+ `summary`, `source`)."""
    text = (text or "").strip()[:300]
    llm = llm or LLM()
    out = llm.complete_json(_ROLE_SYSTEM, f"Line: {line}. Answer the summary in {LANG_NAMES.get(lang, 'English')}. Coach says: {text}") if text else None
    if out and isinstance(out.get("params"), dict):
        role = sanitize_role(out["params"], out.get("label") or text[:30], text)
        role["summary"], role["source"] = str(out.get("summary", ""))[:200], "llm"
        return role
    role = sanitize_role(_keyword_role(text, line), (text.split(",")[0].split(".")[0])[:28].strip().capitalize() or "Custom role", text)
    role["summary"], role["source"] = _OFFLINE.get(lang, _OFFLINE["en"]), "rules"
    return role


# ----------------------------------------------------------------------------- scenarios
_NUM = r"(\d{1,2})"


def _keyword_scenario(text: str) -> dict[str, Any]:
    t = re.sub(r"\b(right now|now|immediately|maintenant|tout de suite)\b", "at 0", text.lower())  # "now" = already due
    rules: list[dict[str, Any]] = []
    opp_re = r"opponent|opposition|adversaire|\baway\b|\bthem\b|\btheir\b|\bthey\b|extérieur|northgate"
    own_re = r"\bmy\b|\bour\b|\bwe\b|\bus\b|\bnous\b|\bmon\b|\bmes\b|\bnotre\b|\bhome\b|riverside"

    def who(m, default="home"):
        win = t[max(0, m.start() - 45): m.end()]  # nearest mention wins: "red card for my CB ... opponent gets a goal"
        o = max((x.start() for x in re.finditer(opp_re, win)), default=-1)
        h = max((x.start() for x in re.finditer(own_re, win)), default=-1)
        return default if o == h else ("away" if o > h else "home")

    for m in re.finditer(r"(red card|carton rouge|sent off|expuls)[^.;]*?(?:at|à|a|minute|min|')\s*" + _NUM, t):
        rules.append({"trigger": {"minute": int(m.group(2))}, "action": {"type": "red_card", "team": who(m)}})
    for m in re.finditer(r"(injur|blessé|blesse|blessure)[^.;]*?(?:at|à|a|minute|min|')\s*" + _NUM, t):
        rules.append({"trigger": {"minute": int(m.group(2))}, "action": {"type": "injury", "team": who(m)}})
    for m in re.finditer(r"(?:goal|but)\b[^.;]*?(?:at|à|a|minute|min|')\s*" + _NUM, t):
        if re.search(r"red card|carton", m.group(0)):
            continue
        rules.append({"trigger": {"minute": int(m.group(1))}, "action": {"type": "goal", "team": who(m, "away")}})
    m = re.search(r"(\d)\s*[-:]\s*(\d)\s*(?:down|behind|mené|mene)", t) or re.search(r"(?:down|behind|mené)\s*(\d)\s*[-:]\s*(\d)", t)
    if m:
        n = abs(int(m.group(1)) - int(m.group(2))) or 1
        for k in range(n):
            rules.append({"trigger": {"minute": 10 + 15 * k}, "action": {"type": "goal", "team": "away"}})
    tm = re.search(r"(?:at|from|after|à|des|dès|a)\s*" + _NUM + r"\s*(?:'|min)?", t)
    minute = int(tm.group(1)) if tm else 60
    cond = {"team": "home", "score_diff_lte": -1} if re.search(r"trailing|losing|behind|down|mené|mene|perd", t) else None
    changes: dict[str, Any] = {}
    if re.search(r"all.out|attack|going for it|chase|comeback|come back|remont|offensi", t):
        changes.update(pressing=0.95, line_height=0.95, tempo=0.9, directness=0.65)
    if re.search(r"park the bus|low block|defend deep|sit back|bloc bas|défendre profond|se replie", t) and not changes:
        changes.update(line_height=0.1, pressing=0.15, width=0.3)
    if re.search(r"press (high|more)|high press|presse haut|pressing haut", t):
        changes.update(pressing=0.95, line_height=0.85)
    fm = re.search(r"\b(\d-\d(?:-\d){1,3})\b", t)
    if fm and get_formation(fm.group(1)):
        changes["formation"] = fm.group(1)
    if changes:
        team = "away" if re.search(r"opponent|opposition|adversaire|they park|them", t) and not re.search(r"\bwe\b|\bour\b|\bnous\b", t) else "home"
        trig: dict[str, Any] = {"minute": minute}
        if cond and team == "home":
            trig["if"] = cond
        rules.append({"trigger": trig, "action": {"type": "tactic_change", "team": team, "changes": changes}})
    return {"name": text[:50], "rules": rules}


def interpret_scenario(text: str, llm: Optional[LLM] = None, lang: str = "en") -> dict[str, Any]:
    """Free text -> sanitized scenario {"name", "rules", "source", "explain", "summary"} (summary and explain in `lang`)."""
    text = (text or "").strip()[:500]
    llm = llm or LLM()
    raw = llm.complete_json(_SCENARIO_SYSTEM, f"Language for the summary: {LANG_NAMES.get(lang, 'English')}. Coach says: {text}", 700) if text else None
    source = "llm"
    scn = sanitize(raw, text[:50]) if raw else {"rules": []}
    summary = str(raw.get("summary", ""))[:400] if raw else ""
    if not scn["rules"]:
        scn, source, summary = sanitize(_keyword_scenario(text), text[:50]), "rules", _OFFLINE.get(lang, _OFFLINE["en"])
    scn["source"] = source
    scn["summary"] = summary
    scn["explain"] = [describe_rule(r, lang) for r in scn["rules"]]
    return scn
