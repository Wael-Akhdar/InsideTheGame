"""FastAPI server: live match stream (SSE), tactic catalog and the Tactic Lab."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse

from ..agents.interpreter import interpret_role, interpret_scenario
from ..agents.pipeline import Orchestrator, Viewer
from ..overlay import build_feed, export_overlay
from ..lab import evaluate, what_if
from ..scenario import PRESET_SCENARIOS, describe_rule, sanitize
from ..feed import SimulatorFeed
from ..feed.sportec import DataMissing as SportecMissing
from ..feed.sportec import SportecFeed
from ..feed.wyscout import LEAGUES, DataMissing, WyscoutFeed, list_matches
from ..simulator.match import MatchSimulator
from ..tactics import PRESETS, describe_catalog, get_formation, resolve_tactic

SESSIONS: dict[str, dict[str, Any]] = {}  # live match sessions: speed / pause / queued coach commands

app = FastAPI(title="GamePulse")
WEB = Path(__file__).resolve().parents[2] / "web"


def _spec(raw: Optional[str], default: str) -> Any:
    """A tactic query param is either a preset name or a JSON-encoded tactic."""
    if not raw:
        return default
    if raw.lstrip().startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default
    return raw


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/catalog")
def catalog():
    cat = describe_catalog()
    cat["scenarios"] = {k: {**v, "explain": [describe_rule(r) for r in v["rules"]]} for k, v in PRESET_SCENARIOS.items()}
    return cat


@app.get("/api/formation/{name}")
def formation(name: str):
    slots = get_formation(name)
    if slots is None:
        raise HTTPException(400, "Not a playable formation: use 10 outfield players, 3-5 defenders, 1-4 forwards (e.g. 4-1-2-1-2).")
    return [dict(slot=s[0], x=s[1], y=s[2], line=s[3], default_role=s[4]) for s in slots]


@app.post("/api/ai/role")
async def ai_role(body: dict = Body(...)):
    """Coach describes what a player should do -> role parameters (LLM if configured, keywords otherwise)."""
    return await run_in_threadpool(interpret_role, str(body.get("text", "")), str(body.get("line", "MF")))


@app.post("/api/ai/scenario")
async def ai_scenario(body: dict = Body(...)):
    """Coach describes a situation to test -> validated scenario rules."""
    return await run_in_threadpool(interpret_scenario, str(body.get("text", "")))


@app.get("/api/feeds/wyscout/{league}")
def wyscout_matches(league: str):
    """Real matches available (public Wyscout dataset, CC BY 4.0). No club names: matchday and date only."""
    if league not in LEAGUES:
        raise HTTPException(404, f"league must be one of {LEAGUES}")
    try:
        return list_matches(league)
    except DataMissing as e:
        raise HTTPException(404, str(e))


@app.get("/api/match/stream")
async def stream(seed: int = 42, speed: float = 60.0, mode: str = "casual", lang: str = "en",
                 home: Optional[str] = None, away: Optional[str] = None, scenario: Optional[str] = None,
                 source: str = "sim", league: str = "Spain",
                 sid: Optional[str] = None, team: Optional[str] = None, player: Optional[str] = Query(None)):
    speed = max(1.0, min(speed, 2000.0))
    scn = None
    if scenario:
        try:
            scn = sanitize(json.loads(scenario))
        except json.JSONDecodeError:
            scn = None
    if source == "sportec":  # a real match with tracking: events and all player positions, pseudonymised
        try:
            feed = await run_in_threadpool(SportecFeed, None, seed)
        except SportecMissing as e:
            raise HTTPException(404, str(e))
    elif source == "wyscout":  # a real match: events only, pseudonymised, same pipeline
        if league not in LEAGUES:
            raise HTTPException(404, f"league must be one of {LEAGUES}")
        try:
            feed = await run_in_threadpool(WyscoutFeed, league, seed)
        except DataMissing as e:
            raise HTTPException(404, str(e))
    else:
        feed = SimulatorFeed(seed=seed, home_tactic=_spec(home, "Possession 4-3-3"), away_tactic=_spec(away, "Counter-attack 4-4-2"),
                             scenario=scn)
    sim = getattr(feed, "sim", None)  # live coaching only exists for simulated matches
    sess = {"speed": speed, "paused": False, "queue": []}
    if sid:
        SESSIONS[sid] = sess
    orch = Orchestrator(*feed.teams)
    viewer = Viewer(mode=mode if mode in ("casual", "analyst") else "casual", lang=lang if lang in ("en", "fr", "es", "ar") else "en",
                    favorite_team=team, focus_player=player)

    def team_meta(t):
        return {"id": t.id, "name": t.name, "tactic": t.tactic.to_dict() if t.tactic else None,
                "players": [{"id": p.id, "name": p.name, "number": p.number, "slot": p.slot, "role": p.role, "line": p.position}
                            for p in t.players]}

    async def gen():
        meta = {"home": team_meta(feed.teams[0]), "away": team_meta(feed.teams[1]), "source": feed.name,
                "label": getattr(feed, "label", "Simulated match")}
        yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
        prev = 0.0
        try:
            for tk in feed.ticks():
                while sess["paused"]:
                    await asyncio.sleep(0.1)
                wait = max(0.0, (tk.t - prev) / max(1.0, sess["speed"]))  # speed can change at any time
                if wait:
                    await asyncio.sleep(wait)
                prev = max(prev, tk.t)
                overlays = orch.process_tick(tk, viewer)
                payload = {"frame": tk.frame, "events": [e.to_dict() for e in tk.events],
                           "snapshot": orch.state.snapshot(), "overlays": [o.to_dict() for o in overlays]}
                yield f"data: {json.dumps(payload)}\n\n"
                while sess["queue"]:  # coach commands take effect before the next tick is simulated
                    cmd = sess["queue"].pop(0)
                    if sim is None:
                        continue
                    if cmd["type"] == "tactic":
                        sim.set_tactic(sim.home.id if cmd["team"] == "home" else sim.away.id, cmd["spec"], announce=True)
                    elif cmd["type"] == "scenario":
                        sim.add_scenario(cmd["scenario"])
            yield "event: end\ndata: {}\n\n"
        finally:
            SESSIONS.pop(sid or "", None)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/overlay")
async def overlay(source: str = "sim", seed: int = 42, league: str = "Spain", lang: str = "en", mode: str = "casual",
                  team: Optional[str] = None, player: Optional[str] = None):
    """The whole match as timestamped overlay cards (JSON), ready for a video renderer."""
    if source not in ("sim", "wyscout", "sportec"):
        raise HTTPException(400, "source must be sim, wyscout or sportec")
    try:
        feed = await run_in_threadpool(build_feed, source, seed, league)
    except (DataMissing, SportecMissing) as e:
        raise HTTPException(404, str(e))
    viewer = Viewer(mode=mode if mode in ("casual", "analyst") else "casual", lang=lang if lang in ("en", "fr", "es", "ar") else "en",
                    favorite_team=team, focus_player=player)
    return await run_in_threadpool(export_overlay, feed, viewer)


@app.post("/api/match/control")
async def match_control(body: dict = Body(...)):
    """Live coaching: change speed, pause/resume, switch tactics or inject a scenario while the match is running."""
    sess = SESSIONS.get(str(body.get("sid", "")))
    if sess is None:
        raise HTTPException(404, "No running match for this session")
    reply: dict[str, Any] = {"ok": True}
    if "speed" in body:
        sess["speed"] = max(1.0, min(float(body["speed"]), 2000.0))
    if "paused" in body:
        sess["paused"] = bool(body["paused"])
    if body.get("tactic"):  # {"team": "home"|"away", "spec": <preset name | partial changes | full tactic>}
        t = body["tactic"]
        sess["queue"].append({"type": "tactic", "team": "away" if t.get("team") == "away" else "home", "spec": t.get("spec")})
    text = body.get("scenario_text")
    if text or body.get("scenario"):
        scn = await run_in_threadpool(interpret_scenario, text) if text else sanitize(body["scenario"])
        sess["queue"].append({"type": "scenario", "scenario": scn})
        reply["scenario"] = scn
    return reply


@app.post("/api/lab/whatif")
async def lab_whatif(body: dict = Body(...)):
    """Same seeds with and without a scenario: {"tactic", "scenario" (obj or "text"), "opponents", "n"}."""
    tactic = resolve_tactic(body.get("tactic"))
    scn = interpret_scenario(body["text"]) if body.get("text") else sanitize(body.get("scenario"))
    opponents = body.get("opponents") or [p for p in PRESETS.values() if p.name != tactic.name]
    n = max(4, min(int(body.get("n", 20)), 60))
    res = await run_in_threadpool(what_if, tactic, scn, opponents[:6], n)
    res["explain"] = [describe_rule(r) for r in scn["rules"]]
    return res


@app.post("/api/lab/run")
async def lab_run(body: dict = Body(...)):
    """Stress-test a tactic: {"tactic": <name|obj>, "opponents": [<name|obj>...], "n": 20}."""
    tactic = resolve_tactic(body.get("tactic"))
    opponents = body.get("opponents") or [p for p in PRESETS.values() if p.name != tactic.name]
    n = max(4, min(int(body.get("n", 20)), 60))
    scn = sanitize(body["scenario"]) if body.get("scenario") else None
    return await run_in_threadpool(evaluate, tactic, opponents[:10], n, 1000, None, scn)
