# GamePulse: product vision and roadmap

## Vision
GamePulse started as a live match-intelligence engine. The direction now is a **tactical lab for coaches**: design a
formation and a role for every player, simulate it against other tactics, test the situations the coach worries about
("what if we go 0-2 down?", "what if I lose my centre-back at 30'?"), and let AI explain *why* it works or breaks.
The broadcast/fan side (explained moments, overlays, multilingual narration) stays as the second audience of the same engine.

## Done
- Tactical simulator: 22 players positioned by formation + role + team instructions; pressing, passing, dribbles, shots,
  fatigue; fully seeded so a match can be replayed.
- **75 formations** (every playable shape with 3-5 defenders, 1-4 forwards, up to three midfield lines). Any other valid
  shape can be typed in the editor (e.g. `4-1-2-1-2`).
- **Roles in plain language**: the coach describes what a player should do ("stay wide, beat his man, cross early, don't
  track back"); the interpreter agent turns it into role parameters. Azure OpenAI / Foundry when configured, keyword parser
  (EN/FR) otherwise. Output is always validated and clamped before the simulator sees it.
- **Scenarios**: JSON rules (trigger = minute + optional score condition, action = red card / forced goal / injury /
  fatigue / tactic change). Presets plus free text ("red card for my centre-back at 30', then the opponent scores at 40'")
  interpreted by AI. Works in the live match and in the Lab.
- **Live coaching**: speed, pause, tactic sliders, formation and tactic switch, and free-text scenario injection while the
  match is running ("red card for the opponent now").
- **What-if**: the Lab replays the same seeds with and without a scenario. Matches are identical until the first scripted
  action fires, so every difference afterwards is caused by the change.
- Tactic Lab: batch simulation against many opponents, robustness score, plain-language diagnosis.

## Ideas for coaches (not built yet)
1. **Replay a real match and change it** (the big one). Import the coach's own match, rebuild the tactic their team
   actually played, replay it in the simulator with the same analysis, then change something ("what if I had pressed higher
   after 60'?") and compare. The what-if engine already does the second half.
2. **Opponent scouting**: describe or import the next opponent, auto-derive their tactic, and let the Lab find the best
   counter among candidate tactics (search over formations / instructions).
3. **Substitutions and squad management**: fatigue plan, who to replace and when, bench impact.
4. **Set pieces**: corners, free kicks, throw-ins (currently ignored by the simulator).
5. **Per-player attributes**: edit each player's ratings (passing, dribbling, shooting, tackling, pace, vision, stamina,
   keeping) or import the real squad, so the simulation reflects the coach's actual players. Today they are generated
   from the slot and role.
6. **Better analytics**: passing networks, heatmaps, expected threat (xT), pressing traps, PPDA by zone, team shape
   (width / depth / compactness) over time.
7. **Coach assistant**: chat agent over the match data ("why did we lose control after 60'?"), and a one-page PDF
   tactical report after each Lab run.
8. **Search for the best tactic**: automatic optimisation of instructions and roles against a basket of opponents.
9. **Multiplayer coaching**: two coaches, one match, each controlling a side live.

## Real video and match data: what the hackathon rules allow
Importing the coach's own match footage and rebuilding the tactic from it is the strongest product idea, but check the
rules before building it for the submission:
- Section 4.7: *"Projects must use synthetic, football-realistic data."* No real match footage, data or related material
  is provided by the organisers, and any footage an entrant uses must be one they have all rights and consents for.
- The same section lists *auto-eventing* (running a model over a video feed to generate pass and speed metrics) as a
  feature teams may consider, so video analysis itself is in scope. What is not allowed is relying on real Premier League
  data or on footage you do not own.
- Safe plan: keep the **import format open** (structured events and positions as JSON/CSV, the same format the simulator
  already emits) and demo it **only with synthetic matches**, e.g. a match exported from the simulator and re-imported.
  Describe video import as the production path in the pitch, but do not show real footage in the demo video or repo.
- If we want to go further (a model over real video), ask the organisers in writing before the deadline (rule 11.6 covers
  requests for clarification). Do not commit any real footage or data to the public repo.

### Organizers' answer (hackathon support, 13 Oct 2026)
We asked three questions in writing and support replied by email:
1. **Open datasets to calibrate the simulator**: yes, "you can use any data" as long as the hackathon rules are respected,
   with **no trademark issues**.
2. **Our own rendered footage for video eventing**: yes.
3. **Real footage we have the rights to** (e.g. amateur footage we filmed): yes.

Keep the email as evidence. What this does and does not change:
- Open datasets (StatsBomb Open Data, SkillCorner Open Data, Metrica sample data, Wyscout public dataset) are usable to
  calibrate and validate the simulator, and as an alternative input stream for the pipeline. Check each licence yourself
  and credit the source in text.
- **Trademarks**: do not use third-party logos (including the StatsBomb logo that its terms ask for, Premier League or club
  crests). Credit by name in text, and pseudonymise real clubs and players in any demo or screenshot.
- Do not commit raw third-party data or footage to the public repo; keep downloads in a git-ignored folder and commit only
  aggregated calibration results and code.

## Open design questions
- How much should the LLM decide versus the parameters? Today the LLM only writes validated parameters and rules; the
  simulator stays deterministic and testable.
- Scenario DSL growth: substitutions, weather, crowd/home advantage, "opponent switches to a back three when losing".
- Calibration: the simulator is tuned to football-realistic totals (about 23 shots and 2.5 goals per match). Real tactical
  effects (pressing vs. possession) need more validation before claims about real teams.
