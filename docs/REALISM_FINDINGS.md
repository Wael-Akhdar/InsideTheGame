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

## Where the ball goes: real vs simulator (`python -m gamepulse.spatial`, 14 comparisons, 9 within tolerance; was 1 of 14 at the start)
| Quantity | Real | Simulator |
|---|---|---|
| forward / backward / lateral passes | 48 / 20 / 32% | 48 / 22 / 30% |
| pass accuracy from the own / middle / final third | 84 / 87 / 74% | 86 / 86 / 77% |
| mean shot distance, shots from inside the box | 18.6 m, 57% | 18.8 m, 63% |
| passes starting in the own third | 30% | 27% |
| passes starting wide (more than 25 from the centre line) | 50% | 44% |
| spread of pass start positions across the pitch (std of y) | 28.8 | 26.6 |
| share of passes made by defenders / midfielders / forwards | 44 / 42 / 14% | 41 / 34 / 25% |
| defenders' median distance behind the ball when their team has it | 8.8 m | 16.9 m |
| kilometres run by an outfield player in a match | 10.0 | 7.0 (movement inside a tick is not modelled) |
What fixed the biggest gaps: accuracy by (third the pass starts in, third it ends in), taken from real passes (backward and sideways passes
are safe, passes into the final third are not); a defender who goes to the ball where a failed pass lands (real: 87% of such balls are won in
the defending team's own third); a stronger shooting propensity inside the box; passes weighted towards the full width of the pitch and towards
the back line's circulation. The values were tuned with `tools/tune_flow.py` (bounded search with a penalty for leaving the starting point; fixed seeds).
Forwards were the largest gap (a third of the passes); two changes from real tracking cut it to a quarter: a per-line position correction
(`tools/build_shape_correction.py`: in real matches the forwards stand about 10 m behind the ball in the final third and the midfielders 20 m, not on it;
leave-matches-out placement error 13.57 -> 13.10 m) and off-ball drift of every player (real players spread about 14 m around the model's target, which
gives the carrier options ahead of and behind the ball). Still open: forwards still make 25% of the passes (real: 14%), the ball still travels in a narrower band than in real matches, and a tactic's
style moves the numbers less than in real football (a possession preset shoots 9 times per match, real possession teams 13).
Coaches should read the Lab as a comparison of tactics under one model, not as a prediction of real results.

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
