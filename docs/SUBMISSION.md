# GamePulse: texts for the Innovation Studio project page

> The platform asks for everything in **English** (rules 4.9). Paste the sections below into the matching fields.
> Keep the technology list honest: every item is used in the final repo.

## Links
| Field | Value |
|---|---|
| Live demo (free, no login, available until judging ends) | https://gamepulse.lemonbay-43a4c2ef.polandcentral.azurecontainerapps.io |
| GitHub repository (public) | https://github.com/Wael-Akhdar/InsideTheGame |
| Demo video (YouTube, < 2 min) | https://youtu.be/HjBZtuYut1M |
| Team | Wael Akhdar, Jessim Ziani (EPITA) |

## Project name
**GamePulse**

## Tagline
*Feel the match, understand the moment.*

## Short description (one line)
Multi-agent AI on Microsoft Foundry that turns synthetic football events into explained, multilingual match intelligence, plus a tactical lab coaches can trust.

## Elevator pitch
Football stories don't end with the scoreline. TV shows the goal, not why it happened, what is changing, or what a coach should do next.

**GamePulse** ingests a live stream of synthetic, football-realistic match events and turns it into explainable match intelligence. It computes
possession, expected goals, pressing and momentum, detects the moments that matter (a team dominant but not rewarded, a pressing that fades,
a turning point after a tactical change) and **explains why each one matters, citing the events behind it**. Every insight is rendered on screen
and exported as timestamped overlay JSON for broadcast graphics, and it is personalized: casual or analyst view, favourite team, follow a player,
and four languages (English, French, Spanish, Arabic) that can be switched mid-match.

Viewers and coaches can **ask questions**. Agents built with the **Microsoft Agent Framework** answer by calling the engine's tools (match
snapshot, key moments, player reports, tactic simulations), and a **fact-checker rejects any number that is not in the tool results**. The model is
a **gpt-4.1-mini fine-tuned in Microsoft Foundry** into a grounded football commentator: on matches it never saw, 40/40 sentences grounded and in
the right language, 6/6 agent answers grounded.

For coaches, the **Tactic Lab** runs many simulated matches of a tactic against every style, at their level and the opponent's, with what-if
scenarios ("red card at 30'", "we switch to 5-4-1 at 70' if we lead") described in plain words. It is useful because the simulator is
**validated against real football**: 8/8 match totals within tolerance of 1,446 real league matches, 14/16 pitch checks, 13 m placement error
against real tracking data. The known gaps are shown in the app, not hidden.

Everything is also exposed as an **MCP server**, and the app runs on **Azure Container Apps**, built by GitHub Actions.

**Problem solved:** broadcasters and clubs have rich event data but little scalable, explainable and personalized storytelling, and coaches
have no cheap way to test a plan before the match. GamePulse does both from the same engine, and every number it shows can be traced back to it.

## How it answers the challenge (rules 4.1)
| Challenge stage | GamePulse |
|---|---|
| Ingest | Event contract fed by the synthetic match simulator (or a real public match, pseudonymised), streamed live (SSE) |
| Interpret | Live stats, xG, pass difficulty, pressing (PPDA), momentum, per-player reports |
| Explain | Moment detectors + Explainer: each insight says why it matters and cites its evidence event IDs; fact-checked |
| Render | Live dashboard and timestamped overlay JSON (`/api/overlay`, schema in `docs/OVERLAY.md`) |
| Personalize | Casual / analyst view, favourite team, follow a player, 4 languages incl. right-to-left Arabic, switchable mid-match |
| Narrative generation, multi-language storytelling | Fine-tuned narrator and agents writing in the viewer's language |
| Data innovation | Tactical match simulator calibrated and validated against public real data (Realism tab) |

## Microsoft and Azure technologies
| Technology | Use |
|---|---|
| **Microsoft Agent Framework** | Match Analyst and Tactics Coach agents with function tools, a router, and a fact-checker on every answer |
| **Microsoft Foundry / Azure OpenAI** | gpt-4.1-mini fine-tuned into the GamePulse commentator (4 languages, grounded), DefaultV2 guardrails |
| **MCP** | Engine, Tactic Lab and agents as MCP tools (`python -m gamepulse.mcp_server`, or `/mcp/` on the live app) |
| **Azure Container Apps** | Hosts the live demo; a service principal keeps the fine-tuned deployment alive |
| **GitHub Actions + GitHub Container Registry** | Every push to `main` builds and publishes the container image |

## Categories
Grand Prize, plus the category prizes that fit best: **Best Multi-Agent System**, **Best Use of Microsoft Foundry Project**,
**Best Azure Cloud Native Integration**.

## Testing instructions (for judges)
1. Open the live demo (no login). The first load can take a few seconds.
2. **Live match** tab: press *Kick off*. Switch the language in the header while it plays. Ask the match analyst a question, e.g.
   "Who is on top, and what were the key moments?". The tool trace and the fact-check badge appear under the answer.
3. While the match plays, type a situation in *Live coaching*, e.g. "The opponent gets a red card, and we go all out attack".
4. **Tactic Lab** tab: choose a tactic, your level and the opponent's, press *Run simulations*. Then ask the tactics coach, e.g.
   "How do we do against a Low block 5-3-2 of a title contender?".
5. **Realism** tab: how the simulator compares with real football.
6. Shortcuts: `#demo`, `#lab`, `#coach`, `#analyst`, `#realism` at the end of the URL. `/api/overlay` returns the overlay JSON.

If the fine-tuned model is unavailable, the agents answer with the offline planner (same tools, same fact-checker), and the answer is labelled so.
Locally: see *Run it* in the README (runs fully offline without Azure credentials; 40 tests).

## Data
The challenge data is synthetic: matches are generated by our simulator, with fictional clubs and players. Public real data is used only to
calibrate and validate the simulator, and is pseudonymised when shown: Wyscout public dataset (Pappalardo et al. 2019, CC BY 4.0) and Sportec
Open DFL dataset (Bassek et al. 2025, CC BY 4.0). The organizers confirmed by email (2026-10-13) that open datasets may be used. Raw data is
never committed. No third-party logos or copyrighted music.

## Demo video (as recorded, 1:53)
Recorded on the real app with the fine-tuned model (`video/record.py`, `video/voice.py`, `video/build.py`). Voice-over: Microsoft neural
voice (Andrew).

| Time | Shot |
|---|---|
| 0:00 | Title: GamePulse, feel the match, understand the moment |
| 0:04 | The problem: the goal is obvious on TV, why it happened is not |
| 0:12 | Live match: events streamed, stats, momentum, detected moments |
| 0:26 | Insights explained with their evidence, exported as overlay JSON |
| 0:36 | Language switched to French mid-match |
| 0:45 | Ask the match analyst: tool calls and fact-check |
| 1:00 | Live coaching in plain words |
| 1:09 | Tactic Lab: title contender vs mid-table |
| 1:17 | Ask the tactics coach: it runs the simulations |
| 1:30 | Realism: validated against real matches and tracking data |
| 1:42 | Built on Microsoft: Agent Framework, Foundry, MCP, Container Apps |
| 1:51 | End card: live demo link, repository, team |
