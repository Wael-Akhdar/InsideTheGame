# GamePulse: texts for the Innovation Studio project page

> Everything the platform asks for must be in **English**. Edit freely, and keep the tech list honest:
> only list services you actually use in the final repo.

## Project name
**GamePulse**

## Tagline (pick one)
1. *Feel the match, understand the moment.* (recommended)
2. *Every pass has a story. GamePulse tells it.*
3. *Explainable match intelligence, made for every fan.*

## Short description (one line, ~150 chars)
A multi-agent AI engine that turns live football events into explained key moments, real-time narratives and recaps, personalized per fan, in any language.

## Elevator pitch (paste into the submission)
Football stories don't end with the scoreline. **GamePulse** is a multi-agent AI engine on Azure that ingests live football events (passes, shots, tackles, pressure), detects the moments that matter and, above all, **explains why they matter**: a 0.31 xG chance, a momentum swing after a pressing change, a red card that reshapes the game.

Five specialized agents (Stats, Moment Detector, Explainer, Narrator, Persona) collaborate through shared match state. Every insight is grounded in cited event IDs, so nothing is hallucinated. The output is timestamped, machine-readable overlay JSON ready for a broadcast renderer, and it is personalized: an analyst sees xG, pass difficulty and control-vs-chaos; a casual fan gets punchy commentary. Viewers pick their language, favorite club, or follow a single player through the whole match.

To make this testable without real data, we built a seeded **synthetic match simulator** with tactical styles, pressing, fatigue-like dynamics and scenarios (comeback, red card), producing football-realistic event streams (~28 shots and ~3 goals per match on average).

**Problem solved:** broadcasters and streamers have rich event data but little scalable, explainable, personalized storytelling. GamePulse produces it live, in many languages, for every audience segment at once.

## Full description (long form)
### What it does
1. **Ingest**: live stream of synthetic match events (SSE).
2. **Interpret**: rolling-window momentum, xG, pass difficulty rating, ball and shot speed, control vs chaos.
3. **Explain**: each key moment comes with a reason and evidence event IDs.
4. **Render**: overlay cards (JSON) plus a live web dashboard.
5. **Personalize**: casual vs analyst mode, language (EN/FR/ES), favorite team, follow-a-player mode.

### Agents
| Agent | Role |
|---|---|
| Stats | Aggregates events into team and player stats, momentum, rhythm |
| Moment Detector | Finds goals, big chances, momentum swings, red cards |
| Explainer | Explains *why* the moment matters, with evidence |
| Narrator | Writes broadcast-ready copy in the viewer's language and mode |
| Persona | Re-ranks and filters moments per viewer |

### Microsoft / Azure technologies (update as you build)
- **Microsoft Foundry** / Azure OpenAI: narration, translation (planned for the deployed version)
- **Microsoft Agent Framework**: agent orchestration (planned, currently plain-Python orchestrator)
- **Azure Container Apps**: hosting the API and the dashboard (planned)
- **GitHub + GitHub Copilot**: development workflow
- *Optional stretch:* Azure Speech (spoken recaps), Azure Cosmos DB / Fabric (match storage and analytics), Azure MCP

### Categories we target
Grand Prize, Best Use of Microsoft Foundry, Best Multi-Agent System, Best Azure Cloud Native Integration (one Grand Prize plus one Category Prize per entrant maximum).

## Demo video script (< 2 min, public on YouTube)
| Time | Shot |
|---|---|
| 0:00-0:10 | Hook: "A goal is just a number. Why did it matter?" |
| 0:10-0:30 | Architecture in one diagram: events, 5 agents, overlays |
| 0:30-1:00 | Live dashboard in analyst mode: momentum bar, xG, explanation card with evidence |
| 1:00-1:20 | Switch to casual fan plus French, same moment told differently |
| 1:20-1:40 | "Follow a player" mode and the red card scenario |
| 1:40-2:00 | Azure deployment and the pitch: why it's production-ready |

No third-party logos or copyrighted music in the video.
