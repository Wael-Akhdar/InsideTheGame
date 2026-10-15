# Realism findings: where the simulator matches real football and where it does not

Measured on 1,446 league matches (Wyscout public dataset, CC BY 4.0) and 7 Bundesliga matches with full tracking (Sportec Open DFL
dataset, CC BY 4.0, with the authorization of the DFL). Aggregates only. This is the honest state of the simulator on `main`.

## What matches (see CALIBRATION.md and MOVEMENT.md)
Passes, pass accuracy, pass length, forward-pass share, shots, goals, shot conversion and fouls per team-match are within tolerance of
the real values. Team depth, width, compactness and the distance between teammates are within a few metres of real tracking.

## Player placement against real tracking (`python -m gamepulse.validation`)
Each real frame is given to the model with only the formation, the ball and who has it; real players are matched to predicted slots.
| Model | Mean error per player |
|---|---|
| fixed formation shape, ignores the ball | 20.2 m |
| ball-aware shape (on main) | 13.6 m |
| same, parameters fitted on other matches and tested on unseen ones | 12.9 m (team shape gap 3.0 m to 1.6 m) |
| reference: per-team static template fitted on the very frames it is tested on | 19.7 m |
| reference: per-slot linear dependence on the ball, fitted in-sample | 12.2 m |
The model is close to what a per-team, in-sample linear fit can do. What is left (individual runs, marking, pressing) needs a model
that looks at opponents, not only at the ball.

## Where the ball goes: real vs simulator (`python -m gamepulse.spatial`, 16 comparisons, 14 within tolerance; was 1 of 14 at the start)
| Quantity | Real | Simulator |
|---|---|---|
| forward / backward / lateral passes | 48 / 20 / 32% | 48 / 22 / 30% |
| pass accuracy from the own / middle / final third | 84 / 87 / 74% | 86 / 86 / 77% |
| mean shot distance, shots from inside the box | 18.6 m, 57% | 19.8 m, 59% |
| passes starting in the own third | 30% | 27% |
| passes starting wide (more than 25 from the centre line) | 50% | 49% |
| spread of pass start positions across the pitch (std of y) | 28.8 | 28.5 |
| passes per defender / midfielder / forward, % of the team's passes | 10.9 / 10.9 / 6.6 | 10.9 / 11.7 / 7.1 |
| passes starting in the final third | 22% | 32% |
| passes starting in the last 20 units before goal | 7% | 16% |
| defenders' median distance behind the ball when their team has it | 8.8 m | 16.9 m |
| kilometres run by an outfield player in a match | 10.0 | 7.0 (movement inside a tick is not modelled) |
What fixed the biggest gaps: accuracy by (third the pass starts in, third it ends in), taken from real passes (backward and sideways passes
are safe, passes into the final third are not); a defender who goes to the ball where a failed pass lands (real: 87% of such balls are won in
the defending team's own third); a stronger shooting propensity inside the box; passes weighted towards the full width of the pitch and towards
the back line's circulation. The values were tuned with `tools/tune_flow.py` (bounded search with a penalty for leaving the starting point; fixed seeds).
Forwards were the largest gap. Part of it was the measure: Wyscout files most wingers as midfielders (real line-ups average 4.05 defenders, 3.84
midfielders, 2.1 forwards), so the shares are now compared per player. Per player, forwards were still too involved; two changes from real tracking cut it to a quarter: a per-line position correction
(`tools/build_shape_correction.py`: in real matches the forwards stand about 10 m behind the ball in the final third and the midfielders 20 m, not on it;
leave-matches-out placement error 13.57 -> 13.10 m) and off-ball drift of every player (real players spread about 14 m around the model's target, which
gives the carrier options ahead of and behind the ball). Still open: forwards still make 25% of the passes (real: 14%), the ball still travels in a narrower band than in real matches, and a tactic's
style moves the numbers less than in real football (a possession preset shoots 9 times per match, real possession teams 13).
Coaches should read the Lab as a comparison of tactics under one model, not as a prediction of real results.

## Defending: is there a block in front of the attack?
Real tracking (7 Bundesliga matches) counts the outfield defenders goal-side of the ball when it is in their half: 3.6 when the ball is 10-20
units from their goal, 4.9 at 20-33, 6.4 at 33-50. The simulator had 1.9 / 3.0 / 4.3: attacks met too few defenders. Three rules fixed most of it:
the back line keeps goal-side of the ball, defending players close the gap to their position at full rate, and the defending side keeps running
back while the ball travels (one move per action was not enough). Now 3.1 / 4.1 / 5.2 (web/realism.json).

## Team level (`python -m gamepulse.strength`)
A strong team does not play like a weak one. A Maher / Dixon-Coles Poisson model (attack and defence per team, home advantage) fitted on every
league season gives each team a strength in log-goal units (champions about +1.2, 10th about -0.07, 20th about -0.9). Grouping the 2,892 real
team-matches by strength gap gives what a gap does to a match; the simulator's squad quality was scaled on goals only, then everything else was
compared:
| Strength gap | Wins real / sim | Goals for real / sim | Goals against real / sim | Pass share real / sim | Shot share real / sim | Pass accuracy real / sim |
|---|---|---|---|---|---|---|
| much weaker (-1.07) | 10 / 13% | 0.78 / 0.80 | 2.20 / 2.42 | 41.5 / 47.5% | 38.5 / 35.0% | 80.0 / 80.6% |
| even (0) | 30 / 39% | 1.15 / 1.32 | 1.15 / 1.07 | 50 / 50% | 50 / 51% | 80.7 / 82.6% |
| much stronger (+1.07) | 71 / 69% | 2.20 / 2.20 | 0.78 / 0.61 | 58.5 / 53.2% | 61.5 / 66.2% | 85.0 / 85.0% |
Quality acts mostly through finishing and goalkeeping (real strong teams score more of their shots), and through passing and the defending side's
reading of the game. What is left: a stronger simulated side gets slightly too many shots and not enough of the ball (53% against 58.5%). Real data shows why: a
stronger side does not pass faster (18.6 to 19.5 passes per minute of possession at every strength gap), it keeps the ball longer, and its
possessions end almost only on a failed pass, a shot or a clearance. In the simulator it reaches the final third too often (34% of its passes
against 24%) and shoots too soon. Tried without a held-out gain: clearances as their own event, fewer tackles won, a deep-block effect,
lines that drop when a side rarely has the ball, real pass destinations by zone, a joint evolution-strategy fit (branch `realism-wip`).
Coaches choose a level for each side, named after league positions (title contender, European places, ..., relegation battle), in the live match
and in the Lab.

## Formations (`gamepulse/strength.py`)
Read from the starting line-ups of the 1,446 real matches (number of defenders, midfielders and forwards as filed by Wyscout), once the strength
gap is accounted for, the formation alone moves the share of the passes very little: 4-4-2 +0.4, 4-3-3 +0.3, 4-5-1 -0.6, 5-3-2 -2.1, 5-4-1 -1.1,
3-5-2 +0.8, 3-4-3 +1.9 points (standard errors 0.3 to 0.8). A 20-match Premier League study (Bradley et al. 2011) reported 44% for 4-5-1 teams,
which the larger data does not confirm once strength is accounted for. The simulator stays in the same small range but does not reproduce the
sign for back-three systems.

## Do different tactics give different games? (`python -m gamepulse.styles`)
The tables above are averages over all teams, which says nothing about style. This check compares the spread of 78 real teams (season
averages, 10th to 90th percentile) with the spread across 60 random tactics in the simulator (all five instructions drawn between 0.05 and
0.95, formation drawn, against a balanced opponent):
| Metric | Real teams | Simulated tactics |
|---|---|---|
| share of the match's passes | 42.5 to 58.6% | 45.0 to 58.3% |
| pass accuracy | 77.7 to 86.2% | 78.4 to 88.2% |
| shots per match | 8.8 to 14.3 | 7.0 to 13.0 |
| passes per match (random tactics) | 350 to 537 | 354 to 470; a patient, fast, pressing tactic reaches 533, a direct slow one 337 |
Directness moves the pass share from 46% to 58% and the accuracy from 80% to 87%; pressing and tempo move the number of passes (365 to 481 across
tempo). A real team's range also contains differences in player quality, which the simulator does not have (all squads are equal), so a simulated range
that matches the real one with tactics alone is a strict test. Known limits: simulated tactics reach further than real teams in territory (mean pass
start 47 to 56 against 45 to 49.5) and in pass length (17 to 22 m against 19 to 22 m), and real high-possession teams shoot more than the simulated
possession preset (13.5 against 9): in the simulator, keeping the ball does not by itself create chances.
`tests/test_styles.py` fails if a patient and a direct tactic stop producing different games (10 points of pass share, 4 points of accuracy).

## What was tried and why it is not on main
Branch `realism-experiments` holds the work: a data prior built from real passes (where passes go from each zone, shot rate and pass
accuracy by zone), a per-line positioning model fitted with a shape-fidelity term, and automatic tuning of the passing and shooting
parameters. It brings direction shares, midfield share, accuracy and pass volume close to real, but it lowers goals to 0.4 per team
(real 1.2) because shots are taken from slightly worse locations, and it leaves the ball distribution too central. It was parked
rather than merged (the flow fixes above were rebuilt on `main` from its findings: realistic shot locations kept goals at 1.2). A next step would be to model build-up from the back explicitly (goal kicks, centre-backs, long switches) and to make
final-third passes harder, then recalibrate shots with the fitted xG model.
