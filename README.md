# GamePulse

**Feel the match, understand the moment.**
A multi-agent AI engine that turns live (synthetic) football events into explained key moments, real-time narratives and recaps, personalized per fan and per language.

Built for the *Inside the Game: Developer Hackathon* (Microsoft x Premier League). All data is synthetic: clubs and players are fictional.

## Pipeline

```
 Simulator ──> Stats engine ──> Moment detector ──> Explainer ──> Narrator ──> Persona ──> Overlay JSON ──> Web UI
 (events)      (xG, momentum,   (goals, chances,    (why it       (language,   (mode, club,  (timed, machine-
               pass difficulty)  swings, cards)      matters)      tone)        player)      readable)
```

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: add Azure OpenAI / Foundry credentials
python -m pytest -q -p no:anyio tests
uvicorn gamepulse.api.server:app --reload
# open http://127.0.0.1:8000
```

Without Azure credentials the narrator uses deterministic templates, so everything runs offline.
With `AZURE_OPENAI_*` set, narration and translation go through your Foundry deployment.

## Layout

| Path | What |
|---|---|
| `gamepulse/simulator/` | Seeded synthetic match generator (styles, pressing, scenarios) |
| `gamepulse/engine/state.py` | Live stats, momentum, control-vs-chaos, key-moment detection |
| `gamepulse/agents/pipeline.py` | Agents (Explainer, Narrator, Persona) and the orchestrator |
| `gamepulse/agents/llm.py` | Azure OpenAI client with offline fallback |
| `gamepulse/api/server.py` | FastAPI + Server-Sent Events stream |
| `web/index.html` | Live dashboard (overlay cards, momentum bar, stats) |
| `docs/SUBMISSION.md` | Pitch, tagline, description, video script for Innovation Studio |
| `docs/TASKS.md` | Roadmap and work split |

## Status
Working end to end offline: simulator, engine, agents (template mode), API, dashboard, tests.
See `docs/TASKS.md` for what's next.
