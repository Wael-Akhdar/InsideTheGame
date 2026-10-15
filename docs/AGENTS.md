# Agents, tools and MCP

GamePulse is built on **Microsoft Agent Framework** (Python, `agent-framework-core` 1.22) and exposes its engine over **MCP**.

```
                ┌──────────── live overlay chain (per event, pipeline.py) ────────────┐
 feed ─ events ─┤ Stats ─> Moment detector ─> Explainer ─> Narrator ─> Fact-checker ─> Persona ─> overlay JSON
                └──────────────────────────────────────────────────────────────────────┘

 question ─> Router ─┬─> Match Analyst  ── tools: match_snapshot, key_moments, player_report, top_players
                     └─> Tactics Coach  ── tools: list_tactics, test_tactic, what_if, realism
                              │
                              └─> Fact-checker: every number of the answer must appear in a tool result

 MCP server (gamepulse/mcp_server.py, also mounted at /mcp/ on the API):
   list_tactics · test_tactic · what_if · simulate_match · analyse_real_match · realism · ask_coach
```

| Piece | File | Role |
|---|---|---|
| Tools | `gamepulse/agents/tools.py` | The engine and the Tactic Lab as Agent Framework function tools. They return the numbers; agents may only quote them. |
| Match Analyst | `gamepulse/agents/team.py` | Answers questions about the match being played (score, who dominates, key moments, players). |
| Tactics Coach | `gamepulse/agents/team.py` | Runs simulations to answer coaching questions ("how does my 4-3-3 do against a low block of a title contender?", "what if we get a red card at 30?"). |
| Router | `gamepulse/agents/team.py` | Sends the question to the analyst (live match questions) or the coach (tactics). |
| Fact-checker | `gamepulse/agents/team.py` | Rejects any answer or overlay sentence that contains a number absent from the tool results or facts. |
| Overlay chain | `gamepulse/agents/pipeline.py` | Explainer, Narrator, Persona: the explained, personalised cards of the live match. |
| Models | `gamepulse/agents/clients.py` | Azure OpenAI deployment (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`) or a Microsoft Foundry project (`FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`, Azure CLI login). Without them, an offline planner plays the model: same agents, same tool-calling loop, same checks. |
| MCP server | `gamepulse/mcp_server.py` | `python -m gamepulse.mcp_server` (stdio) or `--http 8001`; the API serves the same tools at `/mcp/`. |

## Try it

```bash
curl -s localhost:8000/api/ask -H 'content-type: application/json' \
  -d '{"question": "How does Low block 5-3-2 do against Possession 4-3-3 of a title contender?"}'
python -m gamepulse.mcp_server                  # add it to an MCP client (VS Code / Copilot, Claude, a Foundry agent)
```

In the app: **Ask the match analyst** under the live insights, **Ask the tactics coach** in the Tactic Lab. Each answer shows the agent,
the tools it called with their arguments, and whether every number was traced to a tool result.

## Why this design
- Numbers come from the engine, never from the model: the model plans tool calls and writes; the fact-checker enforces it.
- The same tools serve the web app, the agents and any MCP client.
- The demo runs fully offline (judging, tests), and switches to Azure OpenAI / Foundry with environment variables only.
