# 2026-09-17-baseline1-dev

- What changed: first measured agent. Graph explorer (untested-here, else BFS to frontier, else
  random legal), raw frame hash as state key, clicks on the 64 smallest segmented objects.
  Budget: 1000 choices per game, 3 seeds, dev split (18 games).
- Result: sum of median levels 5 / 18 games (lp85 1, r11l 1, sp80 1, vc33 2). Mean median
  local RHAE 0.38 / 100. 0 fallbacks, 0 inconsistent edges. 234 s total on a 4-core laptop.
  Levels that were won took 160 to 340 actions against human baselines of 7 to 40, so the
  per-level scores are tiny even where levels fall.
- Keep or drop: keep as Baseline 1. Control: see `2026-09-17-random-dev` (same budget, random
  legal policy).
- Observation: most games create almost one new state per action (states about 850 per 1000
  actions on cn04, ka59, ls20, re86, wa30). Either timers or animation cells are making every
  frame unique, or those are large movement games. Volatility masking (roadmap Phase 3) is the
  first thing to test.

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [0, 0, 0]           0       0.0     1000   857.3    3.14
ft09   [0, 0, 1]           0       0.0     1000     204     4.1
g50t   [0, 0, 0]           0       0.0     1000     544    5.08
ka59   [0, 0, 0]           0       0.0     1000   845.7    3.84
lp85   [1, 1, 0]           1      0.01     1000    20.3    1.98
ls20   [0, 0, 0]           0       0.0     1000   861.3    3.03
m0r0   [1, 0, 0]           0       0.0     1000   632.7    5.98
r11l   [1, 1, 1]           1      2.12     1000   854.7    8.08
re86   [0, 0, 0]           0       0.0     1000   968.3    1.68
s5i5   [0, 0, 0]           0       0.0     1000   620.7    2.61
sb26   [0, 0, 0]           0       0.0     1000     198    7.64
sc25   [0, 0, 0]           0       0.0     1000   808.7    4.59
sk48   [0, 0, 0]           0       0.0     1000   658.7    5.07
sp80   [1, 1, 1]           1      4.76     1000     662    6.01
su15   [0, 0, 0]           0       0.0     1000     157    4.27
tu93   [0, 0, 0]           0       0.0     1000   518.3    3.53
vc33   [2, 1, 2]           2      0.03     1000     446    5.64
wa30   [0, 0, 0]           0       0.0     1000   841.7    1.72
TOTAL  games=18 seeds=3 sum_median_levels=5 mean_median_score=0.38 actions/level=3600.0 wall=233.9s fallbacks=0
```
