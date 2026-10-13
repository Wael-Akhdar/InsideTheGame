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

## Calibration against real matches
The simulator is compared with 2,892 real team-matches (Wyscout public dataset, CC BY 4.0; France, Germany, Italy and Spain,
2017/18). Full table in [CALIBRATION.md](CALIBRATION.md). With the default balanced tactics, passes per match, pass accuracy,
mean pass length, forward-pass share, shots, goals, shot conversion and fouls are all within tolerance of the real values.
Early versions were off on pass length (33 m vs 20 m real), pass volume, accuracy and fouls (4.5 vs 13.8); fixing that meant
making teams compact around the ball and slowing the pace of play, then re-balancing shots and tackles.

Team shape is checked against real tracking data (Sportec Open DFL, one Bundesliga match, 25 Hz), see [MOVEMENT.md](MOVEMENT.md):
team depth, width, compactness, distance between teammates and distance to the ball are within a few metres of the real values
in and out of possession (for example depth 36.5 m vs 35.9 m in possession, 34.1 m vs 32.9 m out of possession). Before the
fix the simulated teams were 45 m deep against 33-36 m in reality. This is one match with both teams in a 4-2-3-1, so it is a
check on orders of magnitude, not a benchmark.

Reproduce: `python tools/fetch_wyscout.py && python -m gamepulse.calibration` and
`python tools/fetch_sportec.py && python -m gamepulse.movement`. Raw data stays in `data/external/` (git-ignored).

## What is still not realistic
- **Possession still converts a little too weakly against a balanced side.** Possession 4-3-3 holds about 59% of the ball
  against Balanced 4-3-3 but creates less xG (about 0.8 vs 1.0). Some of this is real (a high line is exposed to counters),
  but the size of the gap has not been checked against real data.
- Possession and territory gaps are calibrated to be plausible, not fitted to real data, so absolute values (for example
  62%) should not be quoted as findings about real teams.
- No set pieces, offsides, throw-ins, substitutions, weather or crowd effects. Every player attribute is generated.
- Pass accuracy by length is flatter than real: short passes are too safe (88% vs 82%) and very long passes (50 m and more) far too
  good (about 69% vs 45%).
- Style bands: the possession preset matches the real high-possession teams on accuracy (85% vs 87%) but takes less of the ball
  (56% of the passes vs 59%), plays fewer forward passes (37% vs 45%) and creates fewer shots (7.5 vs 13.5), even fewer than the
  direct preset (8.2). Real high-possession teams are also better teams, so this is not a like-for-like comparison.
- The preset matchups are not a rock-paper-scissors table backed by evidence. Treat the Lab as a way to compare
  *your* tactics under the same model, and as a source of hypotheses, not as predictions.

## How to validate further
1. Compare simulated distributions with published team-level aggregates (possession vs shots, PPDA vs turnovers by zone).
2. Add monotonic tests for every instruction (already done for possession, directness, pressing; line height and width are next).
3. Compare movement (team width, depth, speed) with open tracking data: Sportec Open DFL (7 matches, CC BY 4.0) and SkillCorner
   Open Data (10 matches, MIT). See docs/ROADMAP.md for the rules around real data and video.
