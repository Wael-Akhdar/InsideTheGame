# Simulator calibration against real match statistics

Source: Wyscout public soccer match event dataset, licence CC BY 4.0. Pappalardo et al. (2019), "A public data set of spatio-temporal match events in soccer competitions", Scientific Data 6:236, https://www.nature.com/articles/s41597-019-0247-7. Only aggregated statistics are shown; the raw data is not part of this repository. Leagues used: France, Germany, Italy, Spain (2017/18).

Regenerate with `python tools/fetch_wyscout.py && python -m gamepulse.calibration --write-doc`.

```
Real: 2892 team-matches in France, Germany, Italy, Spain (2017/18).  Simulated: 200 team-matches (Balanced vs Balanced).
metric                      real       sim
----------------------------------------------
passes / team-match        427.6     397.5   ok
pass accuracy %             82.9      81.3   ok
mean pass length (m)        20.3      21.3   ok
forward passes %            48.0      49.5   ok
shots                       11.1      11.8   ok
goals                        1.2       1.2   ok
shot conversion %           10.5       9.8   ok
fouls                       13.8      14.1   ok

pass accuracy by length (%):
             0-10m  10-20m  20-30m  30-40m  40-50m    50m+
  real          82      89      85      77      65      45
  sim           88      87      80      71      61      53

style bands (real top / bottom quartile of teams by pass share  vs  simulated Possession / Direct preset):
                 pass share  pass acc   fwd %   shots
  real high            59.3      86.6    45.4    13.5
  sim possession       57.3      85.7    39.4     9.2
  real low             42.6      79.1    50.5     9.5
  sim direct           50.1      79.6    50.6     9.0
```
