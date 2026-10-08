"""FastAPI server: live match stream (SSE), tactic catalog and the Tactic Lab."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import Body, FastAPI, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse

from ..agents.pipeline import Orchestrator, Viewer
from ..lab import evaluate
from ..simulator.match import MatchSimulator
from ..tactics import PRESETS, describe_catalog, resolve_tactic

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
    return describe_catalog()


@app.get("/api/match/stream")
async def stream(seed: int = 42, speed: float = 60.0, mode: str = "casual", lang: str = "en",
                 home: Optional[str] = None, away: Optional[str] = None,
                 team: Optional[str] = None, player: Optional[str] = Query(None)):
    speed = max(1.0, min(speed, 2000.0))
    sim = MatchSimulator(seed=seed, home_tactic=_spec(home, "Possession 4-3-3"), away_tactic=_spec(away, "Counter-attack 4-4-2"))
    orch = Orchestrator(sim.home, sim.away)
    viewer = Viewer(mode=mode if mode in ("casual", "analyst") else "casual", lang=lang if lang in ("en", "fr", "es", "ar") else "en",
                    favorite_team=team, focus_player=player)

    def team_meta(t):
        return {"id": t.id, "name": t.name, "tactic": t.tactic.to_dict(),
                "players": [{"id": p.id, "name": p.name, "number": p.number, "slot": p.slot, "role": p.role, "line": p.position}
                            for p in t.players]}

    async def gen():
        yield f"event: meta\ndata: {json.dumps({'home': team_meta(sim.home), 'away': team_meta(sim.away)})}\n\n"
        async for tk in sim.stream(speed):
            overlays = orch.process_tick(tk, viewer)
            payload = {"frame": tk.frame, "events": [e.to_dict() for e in tk.events],
                       "snapshot": orch.state.snapshot(), "overlays": [o.to_dict() for o in overlays]}
            yield f"data: {json.dumps(payload)}\n\n"
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/lab/run")
async def lab_run(body: dict = Body(...)):
    """Stress-test a tactic: {"tactic": <name|obj>, "opponents": [<name|obj>...], "n": 20}."""
    tactic = resolve_tactic(body.get("tactic"))
    opponents = body.get("opponents") or [p for p in PRESETS.values() if p.name != tactic.name]
    n = max(4, min(int(body.get("n", 20)), 60))
    return await run_in_threadpool(evaluate, tactic, opponents[:10], n)
