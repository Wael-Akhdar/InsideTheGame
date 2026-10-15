# GamePulse

**Feel the match, understand the moment.**
A tactical football lab and live match intelligence engine. Coaches design a formation, give every player a role, set team instructions, then watch the match unfold live (22 players on the pitch, live charts) or stress-test the tactic over hundreds of simulated matches against other tactics. A multi-agent AI layer explains every key moment, in the viewer's language and style.

Built for the *Inside the Game: Developer Hackathon* (Microsoft x Premier League). All data is synthetic: clubs and players are fictional.

## Simulated or real: one pipeline
Everything the analysis sees goes through an **event contract** (`docs/EVENT_CONTRACT.md`): line-ups and a stream of events.
The simulator is one source; a real match from the public Wyscout dataset (CC BY 4.0, pseudonymised) is another, selectable in the
Live match tab ("Data source"). On 180 real matches the events rebuild the official score every time, and a real Bundesliga match with player tracking (positions of all 22 players) plays on the pitch.
Quality audit on real matches: `docs/REAL_MATCH_AUDIT.md`. Real-match data: Bassek et al. (2025), Sportec Open DFL dataset (CC BY 4.0, with the authorization of the DFL); Pappalardo et al. (2019), *A public data set of spatio-temporal match events in soccer competitions*, Scientific Data 6:236.

## Insights the TV does not show
A goal is obvious on screen. GamePulse looks for what is not (`gamepulse/engine/insights.py`):
- **Dominant, not rewarded**: a team far ahead in expected goals but level or behind.
- **Pressing is fading**: pressing activity well below its early-match level while the opponent gains time on the ball.
- **Key player**: one outfield player involved in a disproportionate share of his team's passing.
- **Turning point**: how the balance of chances moved after a tactical change or a red card.

Each insight cites the events that justify it. The detectors read only the event stream and the line-ups, like a real data feed,
never the simulator's internals, so the same code can run on real matches.

## What a coach can do
- Pick any of **75 formations** (or type your own shape), and give every player a role. Roles can be **described in plain
  language** ("stay wide, beat his man, cross early") and are translated by AI.
- Test **scenarios**: presets or free text ("red card for my centre-back at 30', then the opponent scores at 40'").
- **Coach live**: change speed, pause, switch tactics or inject events while the match runs.
- **What-if**: compare a tactic with and without a scenario over many matches (same seeds, so differences come from the change).

Simulator realism is checked against real match statistics (`docs/CALIBRATION.md`; data: Pappalardo et al. 2019, CC BY 4.0).

See `docs/ROADMAP.md` for the vision, ideas (replaying real matches, scouting, set pieces...) and what the rules allow regarding video.

## Three modes
1. **Live match**: 22 players move on a pitch in real time; possession, xG, pressing and momentum charts update live; agents write explained insights.
2. **Tactics**: formation (4-3-3, 4-4-2, 4-2-3-1, 3-5-2, 5-3-2, 3-4-3), one role per player, five team instructions (line height, pressing, width, tempo, directness). Saved in the browser, exportable as JSON.
3. **Tactic Lab**: plays your tactic against any set of opponents (n matches each, half home / half away, in parallel) and reports W/D/L, xG balance, possession, PPDA, a robustness score and a plain-language diagnosis (e.g. "your high line is exposed by direct play").

## Pipeline

```
 Simulator ──> Stats engine ──> Moment detector ──> Explainer ──> Narrator ──> Persona ──> Overlay JSON ──> Web UI
 (events)      (xG, momentum,   (goals, chances,    (why it       (language,   (mode, club,  (timed, machine-
               pass difficulty)  swings, cards)      matters)      tone)        player)      readable)
```

## Agents and MCP

Microsoft Agent Framework agents answer questions with the engine as tools, and every number they write is fact-checked against
the tool results. The same tools are served over MCP (`python -m gamepulse.mcp_server`, or `/mcp/` on the API). See `docs/AGENTS.md`.

```
 question -> Router -> Match Analyst (live match tools) | Tactics Coach (simulation tools) -> Fact-checker -> answer + tool trace
```

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: add Azure OpenAI / Foundry credentials
python -m pytest -q -p no:anyio tests
uvicorn gamepulse.api.server:app --reload
# open http://127.0.0.1:8000   (add #demo to auto-start a match, #lab to auto-run the lab)
```

Without Azure credentials the narrator uses deterministic templates, so everything runs offline.
With `AZURE_OPENAI_*` set, narration and translation go through your Foundry deployment.

## Layout

| Path | What |
|---|---|
| `gamepulse/tactics.py` | Formations, roles, team instructions, presets |
| `gamepulse/simulator/` | Seeded tactical simulator: player positions, pressing, passing, dribbles, shots, fatigue |
| `gamepulse/scenario.py` | Scenario rules (red card, goal, injury, fatigue, tactic change), presets, validation |
| `gamepulse/agents/interpreter.py` | AI interpreter: free-text roles and scenarios to validated parameters (LLM or keyword fallback) |
| `gamepulse/lab.py` | Tactic Lab: headless batch simulation, aggregation, insights |
| `gamepulse/engine/state.py` | Live stats, momentum, control-vs-chaos, key-moment detection |
| `gamepulse/agents/pipeline.py` | Agents (Explainer, Narrator, Persona) and the orchestrator |
| `gamepulse/agents/llm.py` | Azure OpenAI client with offline fallback |
| `gamepulse/agents/tools.py`, `team.py`, `clients.py` | Agent Framework tools, Match Analyst / Tactics Coach / Router / Fact-checker, model clients |
| `gamepulse/mcp_server.py` | MCP server exposing the engine, the Lab and the agents |
| `gamepulse/api/server.py` | FastAPI + Server-Sent Events stream |
| `gamepulse/overlay.py` | Timestamped overlay JSON export, see docs/OVERLAY.md |
| `web/index.html` | Live dashboard (overlay cards, momentum bar, stats) |
| `docs/SUBMISSION.md` | Pitch, tagline, description, video script for Innovation Studio |
| `docs/TASKS.md` | Roadmap and work split |

## Status
Working end to end offline: simulator, engine, agents (template mode), API, dashboard, tests.
See `docs/TASKS.md` for what's next.
