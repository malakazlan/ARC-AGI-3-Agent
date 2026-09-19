# 2026-09-19-trackA-dev

- What changed: first full run of the Track A step-1 build (reach skips unreachable places,
  frame openings, collect give-up, restart recognition and blame, avatar parts) with the
  reach gate off and the restart rule in its first form.
- Result vs baseline (`2026-09-19-route-dev`, 17 / 1.37): 15 / 1.59. su15 collapsed to 14
  states on every seed: its illegal pulls animate and revert to the first frame, which the
  restart rule read as a level restart and blamed on the click; lp85 L1 19 -> 73 actions for
  the same reason; ls20 seed 2 lost L2 without the gate; tu93 [4,4,2]; vc33 and ft09 faster.
- Keep or drop: superseded by `2026-09-19-trackA2-dev` (restart rule limited to a confident
  avatar that jumped home, gate bounded to 20 explorer actions per level, avatar parts off).

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [1, 1, 1]           1      0.05     1000   333.7   38.71
ft09   [1, 1, 1]           1      0.31     1000   710.7    7.28
g50t   [0, 1, 0]           0       0.0     1000     110   32.17
ka59   [0, 0, 1]           0       0.0     1000   179.7    32.1
lp85   [1, 1, 1]           1      0.15     1000      26    3.94
ls20   [2, 2, 1]           2      9.62     1000   139.3    61.1
m0r0   [0, 0, 1]           0       0.0     1000      80   45.68
r11l   [1, 1, 1]           1      4.76     1000   305.3    8.42
re86   [0, 0, 0]           0       0.0     1000    79.7   17.99
s5i5   [1, 1, 1]           1      0.01     1000   245.7    4.08
sb26   [0, 0, 0]           0       0.0     1000     237    23.7
sc25   [1, 0, 1]           1      0.31     1000   440.3   24.75
sk48   [0, 0, 0]           0       0.0     1000   252.7   18.74
sp80   [1, 1, 1]           1      0.04     1000   237.7   32.17
su15   [0, 0, 0]           0       0.0     1000      14    5.09
tu93   [4, 4, 2]           4      8.46     1000   132.7   29.93
vc33   [2, 2, 2]           2      4.87     1000     256    4.96
wa30   [0, 0, 0]           0       0.0     1000   398.3   33.65
TOTAL  games=18 seeds=3 sum_median_levels=15 mean_median_score=1.59 actions/level=1227.3 wall=1273.4s fallbacks=0
```
