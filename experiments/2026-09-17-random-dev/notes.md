# 2026-09-17-random-dev

- What changed: control run. Same budget as Baseline 1 (dev split, 18 games, 3 seeds, 1000
  choices per game) with the legal-uniform random policy instead of the graph explorer.
- Result: sum of median levels 2 (r11l 1, sp80 1). Mean median local RHAE 0.27 / 100.
  Baseline 1 got 5 and 0.38. The explorer wins on levels; scores are noise at this level of
  efficiency because both take hundreds of actions per level.
- Keep or drop: reference only. Not a candidate.

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [0, 0, 0]           0       0.0     1000       0    1.58
ft09   [1, 0, 0]           0       0.0     1000       0    4.21
g50t   [0, 0, 0]           0       0.0     1000       0    5.36
ka59   [0, 0, 0]           0       0.0     1000       0    1.86
lp85   [0, 1, 0]           0       0.0     1000       0    2.29
ls20   [0, 0, 0]           0       0.0     1000       0    2.46
m0r0   [0, 0, 0]           0       0.0     1000       0    1.77
r11l   [1, 1, 1]           1      0.03     1000       0    5.54
re86   [0, 0, 0]           0       0.0     1000       0    2.12
s5i5   [0, 0, 0]           0       0.0     1000       0     1.8
sb26   [0, 0, 0]           0       0.0     1000       0   12.04
sc25   [0, 0, 0]           0       0.0     1000       0    4.06
sk48   [0, 0, 0]           0       0.0     1000       0    2.14
sp80   [1, 1, 1]           1      4.76     1000       0    3.96
su15   [0, 0, 0]           0       0.0     1000       0    2.73
tu93   [0, 0, 0]           0       0.0     1000       0    3.86
vc33   [0, 0, 0]           0       0.0     1000       0    1.92
wa30   [0, 0, 0]           0       0.0     1000       0    2.01
TOTAL  games=18 seeds=3 sum_median_levels=2 mean_median_score=0.27 actions/level=6750.0 wall=185.2s fallbacks=0
```
