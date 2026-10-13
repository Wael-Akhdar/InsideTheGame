# Team shape: simulator vs real tracking data

Source: Sportec Open DFL dataset, Bassek, Rein, Weber, Memmert (2025), "An integrated dataset of spatiotemporal and event data in elite soccer", Scientific Data; CC BY 4.0, released with the authorization of the DFL. One Bundesliga match (positions of every player at 25 Hz, sampled at 1 Hz). Only aggregated numbers are shown; the raw data and all names stay outside the repository.

Caveat: a single match (4-2-3-1 against 4-2-3-1) is a sanity check on orders of magnitude, not a statistical benchmark. Regenerate with `python tools/fetch_sportec.py && python -m gamepulse.movement --write-doc`.

```
Real: 1 Bundesliga match, 4-2-3-1 vs 4-2-3-1, 6844 team-frames at 1 Hz.  Simulated: 20 matches, Balanced 4-2-3-1 vs itself.
Real outfield players covered 10.0 km per match (sanity check of the tracking data).

in possession
  metric                            real     sim
  team depth (m)                    35.9    36.5
  team width (m)                    47.1    43.4
  mean dist. to centroid (m)        17.7    16.7
  nearest teammate (m)              11.6    11.6
  ball to 3 nearest mates (m)        9.6     8.8
  centroid to ball (m)              18.7    16.8

out of possession
  metric                            real     sim
  team depth (m)                    32.9    34.0
  team width (m)                    37.8    40.7
  mean dist. to centroid (m)        15.2    15.4
  nearest teammate (m)              10.0    10.4
  ball to 3 nearest mates (m)       10.4    10.8
  centroid to ball (m)              19.4    16.3

```
