"""FastAPI server: streams a synthetic match as Server-Sent Events, with per-viewer overlays."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse

from ..agents.pipeline import Orchestrator, Viewer
from ..simulator.match import MatchSimulator

app = FastAPI(title="GamePulse")
WEB = Path(__file__).resolve().parents[2] / "web"


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/match/stream")
async def stream(seed: int = 42, scenario: str = "balanced", speed: float = 60.0,
                 mode: str = "casual", lang: str = "en",
                 team: Optional[str] = None, player: Optional[str] = Query(None)):
    sim = MatchSimulator(seed=seed, scenario=scenario)
    orch = Orchestrator(sim.home, sim.away)
    viewer = Viewer(mode=mode, lang=lang, favorite_team=team, focus_player=player)

    async def gen():
        meta = {"home": sim.home.name, "away": sim.away.name, "home_id": sim.home.id, "away_id": sim.away.id,
                "players": {p.id: p.name for t in (sim.home, sim.away) for p in t.players}}
        yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
        async for ev in sim.stream(speed):
            overlays = orch.process(ev, viewer)
            payload = {"event": ev.to_dict(), "snapshot": orch.state.snapshot(),
                       "overlays": [o.to_dict() for o in overlays]}
            yield f"data: {json.dumps(payload)}\n\n"
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
