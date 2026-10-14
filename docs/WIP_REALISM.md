# Realism work in progress (branch `realism-wip`, paused 2026-10-14)

Not merged into `main`: `main` keeps the last verified state (calibration 8/8, spatial 12/14, strength curves in the Realism tab).

## Done on this branch
- Forwards' share of passes measured **per player** (`gamepulse/spatial.py`): Wyscout files most wingers as midfielders (real line-ups average
  4.05 DF / 3.84 MF / 2.1 FW), so shares by line were not comparable with a 4-3-3. Real per player: DF 10.9%, MF 10.9%, FW 6.6% of the team's passes.
  With `rw_fw` 0.12 and a little more shooting the simulator matched: spatial 14/14, calibration 8/8 (before the changes below).
- New spatial rows: passes starting in the final third (real 22.2%) and in the last 20 units (real 6.9%). The simulator has about 30% and 11-14%:
  the ball stays too long near the opponent's goal. This is the root of the strong-side problem below.
- Pass accuracy by start x (`ACC_X`, `ACC_X_ADJ`): crosses from near the goal line are often lost (real 62% at 84-92, 46% beyond), long kicks
  from the own box too (76-79%). The simulator now matches these.
- New event type `clearance` (contract, simulator, Wyscout feed). Real: about 14.6 clearances per team and match (12.5 for a much stronger side,
  15.9 for a much weaker one). Clearances are not passes, as in the event data.
- `DUEL["win"]`: tackle success, to reduce non-pass turnovers (real possessions end almost only by a failed pass, a shot or a clearance;
  the simulator had about 24 per team from tackles and dribbles).
- Experimental, off by default: `PINNED` (a side that rarely has the ball drops deeper), `BLOCK` (packed block: entry passes, shots),
  `QUALITY["keep"]` and `QUALITY["fin"]`. None of them alone moved the strong side's possession.
- `gamepulse/strength.py`: `real_formation_effects()` and `sim_formation_effects()`. Real effect of the formation on pass share once the strength
  gap is accounted for (1,446 matches, formation read from the starting line-up roles): 4-4-2 +0.4, 4-3-3 +0.3, 4-5-1 -0.6, 5-3-2 -2.1, 5-4-1 -1.1,
  3-5-2 +0.8, 3-4-3 +1.9 points (standard errors 0.3-0.8). The 44% of the 20-match study is not confirmed.
- `tools/tune_flow.py --es N`: evolution strategy over flow, clearance, duel and quality parameters, with the strong-vs-weak targets in the loss
  (share of passes 58.5%, of shots 61.5%, goal log ratio 1.07). Last run: loss 49.7 -> 30.1, stalled; it was stopped before writing its best values.

## Facts measured on real data (useful later)
- Passes per minute of possession do not depend on strength (18.6 to 19.5): a strong side has the ball longer, it does not pass faster.
- Strong side (gap +1.07): 494 passes, thirds 27/49/24%, accuracy 86/89/76%; weak side: 375 passes, 32/47/21%, 82/85/72%.
- Simulator strong side: about 430-440 passes, thirds about 21/45/34%: it gets into the final third far too often, shoots too often per pass,
  so its possessions are too short.

## Next steps
1. Fix the final-third excess for every team (passes from x > 66.7: 30% vs 22%; from x > 80: 11-14% vs 7%), then rerun the strength check.
2. Calibrate formations on `real_formation_effects()` and show the table in the Realism tab instead of the 20-match study.
3. Rerun `tools/realism_report.py`, the test suite, and merge into `main` only if calibration stays 8/8.
