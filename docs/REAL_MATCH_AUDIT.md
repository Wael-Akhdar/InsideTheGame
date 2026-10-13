# Quality audit on real matches

Everything below was measured on public data (Wyscout, CC BY 4.0; Sportec Open DFL, CC BY 4.0). Only aggregates are shown.
Reproduce with `python tools/fetch_wyscout.py`, `python tools/fetch_sportec.py`, `python tools/audit_feed.py real|sim`,
`python tools/fit_xg.py` and `python -m gamepulse.calibration`.

## 1. Shot quality (xG) used on real feeds without expected goals
The first version estimated xG with a hand-written geometric formula. Checked against 43,040 real shots (4,790 goals) it
predicted 6,080 goals (+27%), was too generous on headers (0.21 predicted vs 0.13 real) and too stingy on free kicks.
It was replaced by a logistic model fitted on those shots (`tools/fit_xg.py`; distance, goal angle, header, free kick).
- Held-out league (Spain): 876 goals predicted for 912 real (-4%); log-loss 0.290 against 0.343 for a constant rate.
- All shots: 4,792 predicted for 4,790 goals; every probability bin within a point or two of the observed rate.
- Limit: geometry only. On the one tracked Bundesliga match (21 shots) the provider's own xG sums to 2.51 and ours to 3.79, with a
  weak correlation (0.25): the provider also uses defenders, pressure and assist type. When a feed carries its own xG, we use it.

## 2. Insight detectors on real matches (120 matches, 5 leagues) against simulated matches
| Per match | Real | Simulator |
|---|---|---|
| goals | 2.2 to 3.3 (league dependent) | 2.2 |
| big chances without a goal | about 1.2 | 0.6 |
| momentum swings | about 5.3 | 4.4 |
| key player (passing hub) | 0.3 | 0.6 |
| dominant but not rewarded | 0.3 to 0.8 | 0.04 |
| pressing fade | about 0.05 (no pressure events in this feed) | 0.5 |

Passing share of the top outfield player over 15 minutes: real median 16.5%, 95th percentile 22%. The simulator started at a median of
20.5% (passing too concentrated); after flattening the receiver choice it is 17.8% (95th percentile 23%). The key-player threshold
(23%) comes from the real distribution. Pressing fade is disabled on feeds that carry no pressure events: counting tackles alone
measured something else.

## 3. Simulator shot locations
Real shots by quality bin (share of shots, xG below 0.03 / 0.03-0.06 / 0.06-0.10 / 0.10-0.15 / 0.15-0.25 / 0.25-0.40 / above 0.40):
19 / 23 / 22 / 16 / 12 / 4 / 4 %. The simulator had 40 / 21 / 14 / 10 / 8 / 5 / 3 %: far too many hopeful long shots. After
re-weighting the zones it is 22 / 22 / 20 / 13 / 12 / 6 / 5 %. Goals per team-match follow (1.2 against 1.2 real).

## 4. Review of the tracked match (Bundesliga, real positions at 2-second steps)
- The events rebuild the official score (1-2, including a penalty), the stream satisfies the contract, 22 positions in every frame.
- The pipeline ran unchanged. Fouls (19) and cards (3) match the file.
- Problems found and fixed during the review: momentum swings fired at minute 5 on a handful of events (now not before minute 10, at most
  one every 20 minutes); real shirt numbers were used as pseudonyms (replaced by rank); a penalty and fouls without coordinates were
  dropped (handled); the half-time clock went backwards in the simulator (fixed).
- Still open: one match is a smoke test, not a benchmark; texts are template-based until a language model is connected.
