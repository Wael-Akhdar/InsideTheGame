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
A first fix gave about 62% possession but made the possession side sterile (it recycled the ball in its own third), so the
forward-pass preference was flattened and patient teams now also carry the ball into space. The same matchup now gives about
58% possession, about 82% vs 77% pass accuracy, and the possession side creates slightly more shots and clearly more xG
(about 10.8 vs 9.1 shots, 0.9 vs 0.7 xG).

`tests/test_tactics_effects.py` guards this: possession style must keep the ball against a low block, a mirror match must
stay balanced, directness must trade accuracy for territory, and pressing must lower the opponent's freedom (PPDA).

## What is still not realistic
- **Possession still converts a little too weakly against a balanced side.** Possession 4-3-3 holds about 59% of the ball
  against Balanced 4-3-3 but creates less xG (about 0.8 vs 1.0). Some of this is real (a high line is exposed to counters),
  but the size of the gap has not been checked against real data.
- Possession and territory gaps are calibrated to be plausible, not fitted to real data, so absolute values (for example
  62%) should not be quoted as findings about real teams.
- No set pieces, offsides, throw-ins, substitutions, weather or crowd effects. Every player attribute is generated.
- Shots per team average about 12.7 per match (real top-flight: about 12 to 13); goals about 1.2 per team (a little low).
- The preset matchups are not a rock-paper-scissors table backed by evidence. Treat the Lab as a way to compare
  *your* tactics under the same model, and as a source of hypotheses, not as predictions.

## How to validate further
1. Compare simulated distributions with published team-level aggregates (possession vs shots, PPDA vs turnovers by zone).
2. Add monotonic tests for every instruction (already done for possession, directness, pressing; line height and width are next).
3. Import real tracking or event data as JSON (the simulator already exports the same format) and fit the few coefficients
   that matter most. See docs/ROADMAP.md for the rules around real data and video.
