# The event contract

The analysis pipeline (stats, key moments, insights, explanations, overlays) knows **nothing about a match except what this
contract allows**. Any source that honours it works: our simulator, a real data provider, a replay. This is what makes the system
deployable on a real feed, and it is checked by code (`gamepulse/feed/contract.py`, `tests/test_feed.py`).

## A feed
- `teams`: two `Team` line-ups, `(home, away)`. Each has `id`, `name`, and players with `id`, `name`, `number`, and `position`
  (`GK`, `DF`, `MF` or `FW`). Tactics, roles or attributes are **not** part of the contract (`tactic` may be `None`).
- `ticks()`: chronological `Tick`s. A tick has a time `t` in seconds of match time, the events that happened, and an optional
  `frame`. The frame must at least carry `poss` (the team id with the ball). Player positions (`p`) are optional.

## An event
| Field | Meaning |
|---|---|
| `id` | integer, strictly increasing across the stream |
| `minute`, `second` | running match clock (stoppage time is included: the second half does not restart at 45:00 if the first half ran long) |
| `type` | `kickoff`, `pass`, `shot`, `dribble`, `tackle`, `possession_change`, `pressure`, `foul`, `card`, `goal`, `save`, `halftime`, `fulltime`, `tactic_change`, `injury` |
| `team` | id of the acting team |
| `player` | id of a player in the line-ups (required for pass, shot, tackle, foul, card, goal, save; an own goal has none) |
| `x`, `y`, `end_x`, `end_y` | **team frame**, 0-100: x runs from the acting team's own goal (0) to the opponent's goal (100), y across the pitch |
| `outcome` | pass: `success` / `fail`; shot: `goal` / `saved` / `blocked` / `off_target`; tackle: `won` / `lost`; card: `red` / `yellow` |
| `xg` | probability 0-1 for shots, when known (`meta.xg_estimated` says when it was computed from geometry) |
| `meta` | free-form extras: `receiver` (player id) on a successful pass, `distance_m`, `score` on goals, `own_goal`, ... |

A feed may omit any event type it cannot provide: detectors that need it simply stay silent (for example a feed without
`pressure` events gets no pressing insight based on them). Anything not listed here must not be needed by the pipeline.

## Frames (optional)
`frame` = `{"t", "minute", "poss", "ball": [x, y], "carrier": player id, "p": [[x, y] x 22], "ids": [22 player ids], "off": [empty slots]}`.
Positions use the **global** frame (home attacks to the right, 0-100 on both axes), unlike events which use the acting team's frame.
`ids` lets a frame list whoever is on the pitch (substitutions); the simulator omits it and keeps a fixed order (11 home, then 11 away).

## Checking a feed
```python
from gamepulse.feed import validate_stream
validate_stream(feed)   # raises ContractError listing the first problems
```
It checks event types, outcomes, coordinate ranges, players present in the line-ups, increasing ids and a clock that never goes back.
Writing this check found a bug in our own simulator (the half-time tick reset the clock backwards).

## Feeds we have
| Feed | Source | What it provides |
|---|---|---|
| `SimulatorFeed` | our tactical simulator | everything, plus player positions in `frame.p` |
| `WyscoutFeed` | public Wyscout event dataset (Pappalardo et al., 2019, CC BY 4.0) | real matches, events only |
| `SportecFeed` | Sportec Open DFL dataset (Bassek et al., 2025, CC BY 4.0, with the authorization of the DFL) | a real Bundesliga match: events and the positions of all 22 players and the ball (frames every 2 s), the provider's own xG |

### How Sportec events are mapped
`Play` -> `pass` (receiver and end point from the next action), `ShotAtGoal` and `Penalty` -> `shot` (+ `goal`, with the provider's xG),
`TacklingGame` -> `tackle` for the player without the ball, `Foul` -> `foul`, `Caution` -> `card`, `BallClaiming` and team changes ->
`possession_change`. Coordinates are mirrored per half so that the home team always attacks to the right.

### How Wyscout events are mapped
| Wyscout | Contract |
|---|---|
| `Pass` (tag 1801 accurate or not) | `pass`; the receiver is the next teammate to touch the ball within 8 s |
| `Shot`, free-kick shots, penalties (tags 101 goal, 2101 blocked, 1801 on target) | `shot` and, for goals, `goal`; **xG is estimated from the shot position** (Wyscout has none) |
| tag 102 (own goal) | `goal` for the other team, `meta.own_goal` |
| `Duel` / ground defending duel (tags 703 won, 701 lost) | `tackle` |
| `Foul` with tags 1701, 1703 (red), 1702 (yellow) | `foul` and `card` |
| `Save attempt` without the goal tag | `save` |
| change of team between two ball events | `possession_change` |

Not available from this source: player positions, pressure events, tactics. Teams and players are **pseudonymised** ("Home Team",
"Home #7"); real names never reach the UI, the overlays or the logs.

## Evidence that the pipeline does not cheat
On 180 real matches from five leagues, the stream satisfies the contract and the goals rebuilt from the events equal the official
score every time (`tests/test_feed.py` checks five matches; the full run is reproducible with `tools/fetch_wyscout.py`). The same
`Orchestrator` then produces explained moments and insights on a real match with no change.
