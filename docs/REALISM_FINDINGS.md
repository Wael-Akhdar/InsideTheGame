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

## Where the ball goes: real vs simulator (`python -m gamepulse.spatial`, 14 comparisons, 8 within tolerance; was 1 of 14)
| Quantity | Real | Simulator |
|---|---|---|
| forward / backward / lateral passes | 48 / 20 / 32% | 45 / 24 / 31% |
| pass accuracy from the own / middle / final third | 84 / 87 / 74% | 86 / 87 / 75% |
| mean shot distance, shots from inside the box | 18.6 m, 57% | 19.7 m, 59% |
| passes starting in the own third | 30% | 26% |
| passes starting wide (more than 25 from the centre line) | 50% | 40% |
| spread of pass start positions across the pitch (std of y) | 28.8 | 25.0 |
| share of passes made by defenders / midfielders / forwards | 44 / 42 / 14% | 34 / 33 / 33% |
| defenders' median distance behind the ball when their team has it | 8.8 m | 16.9 m |
| kilometres run by an outfield player in a match | 10.0 | 7.0 (movement inside a tick is not modelled) |
What fixed the biggest gaps: accuracy by (third the pass starts in, third it ends in), taken from real passes (backward and sideways passes
are safe, passes into the final third are not); a defender who goes to the ball where a failed pass lands (real: 87% of such balls are won in
the defending team's own third); a stronger shooting propensity inside the box; passes weighted towards the full width of the pitch and towards
the back line's circulation. The values were tuned with `tools/tune_flow.py` (bounded search with a penalty for leaving the starting point; fixed seeds).
Still open: forwards make a third of the passes (real: 14%), the ball still travels in a narrower band than in real matches, and a tactic's
style moves the numbers less than in real football (a possession preset shoots 7 times per match, real possession teams 13).
Coaches should read the Lab as a comparison of tactics under one model, not as a prediction of real results.

## What was tried and why it is not on main
Branch `realism-experiments` holds the work: a data prior built from real passes (where passes go from each zone, shot rate and pass
accuracy by zone), a per-line positioning model fitted with a shape-fidelity term, and automatic tuning of the passing and shooting
parameters. It brings direction shares, midfield share, accuracy and pass volume close to real, but it lowers goals to 0.4 per team
(real 1.2) because shots are taken from slightly worse locations, and it leaves the ball distribution too central. It was parked
rather than merged (the flow fixes above were rebuilt on `main` from its findings: realistic shot locations kept goals at 1.2). A next step would be to model build-up from the back explicitly (goal kicks, centre-backs, long switches) and to make
final-third passes harder, then recalibrate shots with the fitted xG model.
