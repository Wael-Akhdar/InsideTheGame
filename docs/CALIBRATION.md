# Simulator calibration against real match statistics

Source: Wyscout public soccer match event dataset, licence CC BY 4.0. Pappalardo et al. (2019), "A public data set of spatio-temporal match events in soccer competitions", Scientific Data 6:236, https://www.nature.com/articles/s41597-019-0247-7. Only aggregated statistics are shown; the raw data is not part of this repository. Leagues used: France, Germany, Italy, Spain (2017/18).

Regenerate with `python tools/fetch_wyscout.py && python -m gamepulse.calibration --write-doc`.

```
Real: 2892 team-matches in France, Germany, Italy, Spain (2017/18).  Simulated: 200 team-matches (Balanced vs Balanced).
metric                      real       sim
----------------------------------------------
passes / team-match        427.6     401.2   ok
pass accuracy %             82.9      82.7   ok
mean pass length (m)        20.3      19.7   ok
forward passes %            48.0      48.4   ok
shots                       11.1      11.2   ok
goals                        1.2       1.2   ok
shot conversion %           10.5      11.1   ok
fouls                       13.8      13.7   ok

pass accuracy by length (%):
             0-10m  10-20m  20-30m  30-40m  40-50m    50m+
  real          82      89      85      77      65      45
  sim           83      87      84      76      62      42

style bands (real top / bottom quartile of teams by pass share  vs  simulated Possession / Direct preset):
                 pass share  pass acc   fwd %   shots
  real high            59.3      86.6    45.4    13.5
  sim possession       56.5      86.0    40.2     9.0
  real low             42.6      79.1    50.5     9.5
  sim direct           47.5      79.1    53.2     9.8
```
