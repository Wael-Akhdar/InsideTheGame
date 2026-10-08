# How the simulator works, and how far to trust it

## What it is
A **rule-based, agent-based simulation** written by hand. It is *not* trained on real match data and it is not a
neural model. Every number below is a design decision that we calibrated against football-realistic totals, which
is also what the hackathon asks for (synthetic, football-realistic data).

Each match is a sequence of ticks (about 4 seconds of match time). On every tick:
1. **Positioning**: all 22 players move towards a target position computed from the formation slot, the player's role
   (how far he pushes forward / drops, how wide he stays), the team's instructions (line height, width) and where the ball is.
   Short-passing teams close in on the ball to offer options; direct teams stay stretched. Out of possession the
   nearest defenders press the ball, how many and how far depends on the pressing instruction.
2. **Ball carrier decision**: shoot, carry into open space, dribble, or pass. The choice depends on the role (shooting,
   dribbling, forward-pass tendencies), the zone of the pitch and the pressure around him (opponents within 10 m).
3. **Outcome**: pass success depends on distance, forward risk, pressure on the passer, how marked the receiver is,
   the passer's attributes and the tempo. Failed passes are intercepted by the nearest opponent. Tackles and dribbles
   are duels (tackling vs dribbling). Shots get an xG from distance, angle and pressure, then a finishing and goalkeeper roll.
4. **Context**: fatigue (pressing and tempo burn stamina), red cards and injuries, numerical superiority, scripted scenarios.

Team instructions change *behaviour*, and possession, territory and chances **emerge** from it:
- `directness` sets pass length and risk, how often long balls are hit, and how much the team recycles under pressure.
- `pressing` sets how many players chase the ball and how far; it also drains stamina.
- `line_height`, `width`, `tempo` shape the block, the spacing and the number of actions per minute.

## Known weakness that was found and fixed
Early versions did **not** make a possession-based tactic keep the ball: Possession 4-3-3 vs Low block 5-3-2 gave
about 50% possession, and the low block even made more passes. The cause: turnovers were driven almost entirely by random
pass failures that did not depend on style, so possession could not diverge. The fix gave tactics real mechanisms
(support play, safe vs risky pass selection, long balls, progressive carries, pressure scaled by the opponent's pressing).
Now the same matchup gives about 62% possession for the possession side and about 85% vs 77% pass accuracy.

`tests/test_tactics_effects.py` guards this: possession style must keep the ball against a low block, a mirror match must
stay balanced, directness must trade accuracy for territory, and pressing must lower the opponent's freedom (PPDA).

## What is still not realistic
- **Possession does not yet convert into chances well enough.** Possession 4-3-3 holds about 62% of the ball but creates
  fewer shots than a low block (about 8 vs 11). Some sterility against a compact block is real; this much is probably too much.
- Possession and territory gaps are calibrated to be plausible, not fitted to real data, so absolute values (for example
  62%) should not be quoted as findings about real teams.
- No set pieces, offsides, throw-ins, substitutions, weather or crowd effects. Every player attribute is generated.
- Shots per team average roughly 14 per match (real top-flight: about 12 to 13); goals about 1.3 per team.
- The preset matchups are not a rock-paper-scissors table backed by evidence. Treat the Lab as a way to compare
  *your* tactics under the same model, and as a source of hypotheses, not as predictions.

## How to validate further
1. Compare simulated distributions with published team-level aggregates (possession vs shots, PPDA vs turnovers by zone).
2. Add monotonic tests for every instruction (already done for possession, directness, pressing; line height and width are next).
3. Import real tracking or event data as JSON (the simulator already exports the same format) and fit the few coefficients
   that matter most. See docs/ROADMAP.md for the rules around real data and video.
