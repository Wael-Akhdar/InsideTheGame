# Roadmap (deadline: Oct 27, 2026, 23:59 PT; aim to freeze code on Oct 24)

Legend: [x] done, [ ] todo. Split suggestion: **A** = Wael, **B** = teammate. Swap anything, both touch back, front and AI.

## Week 1 (Oct 6-12): foundations
- [x] Repo, synthetic simulator, stats engine, agent pipeline, SSE API, basic dashboard
- [ ] **A** Plug in the real Foundry deployment (Azure OpenAI) and test narration + FR/ES/AR translation
- [ ] **B** Pitch view: draw the real pitch (SVG) with live ball position, shot map, pass lines
- [ ] **A+B** Link the project to the challenge on Innovation Studio and add the teammate

## Week 2 (Oct 13-19): wow features
- [ ] **A** Move orchestration to **Microsoft Agent Framework** (keep the same agent roles, add handoffs and failure recovery)
- [ ] **A** Expose the engine as **MCP tools** (get_stats, get_moments, get_player) for the agents
- [ ] **B** "Follow a player" mode UI plus per-viewer profile (club, player, language)
- [ ] **B** Broadcast overlay output: separate `/api/overlays` JSON endpoint with timecodes and a transparent-background overlay page
- [ ] **A** Full-time recap endpoint (text, plus Azure Speech audio if time allows)
- [ ] **A** Richer simulator: fatigue, substitutions, set pieces, more scenarios

## Week 3 (Oct 20-27): ship
- [ ] **A+B** Deploy to Azure Container Apps (Dockerfile plus a one-command deploy script)
- [ ] **A+B** Tests, docstrings, clean README, architecture diagram (judged: "well-structured, documented code")
- [ ] **B** Record the < 2 min demo video (script in `docs/SUBMISSION.md`), upload public to YouTube
- [ ] **A** Make the GitHub repo **public**, check no secrets are committed
- [ ] **A+B** Submit on Innovation Studio: pitch, video URL, repo URL, demo URL. Submit a day early.

## Judging checklist (20% each)
- Technology: Foundry + Agent Framework + Azure MCP + Copilot, documented code
- Agentic design: distinct agent roles, shared state, handoffs, recovery from failures
- Real-world impact: deployable, explainable, multilingual
- UX and presentation: clean dashboard, strong video
- Category fit: pipeline of 5 stages fully visible in the demo
