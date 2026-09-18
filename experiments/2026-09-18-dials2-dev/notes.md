# 2026-09-18-dials2-dev

- What changed: dial cap restricted to key dials on avatar games (clicks never capped) after
  `2026-09-18-dials-breadth-dev` (cap on everything) fell to 4.
- Result vs baseline: 5 median levels, RHAE 0.39, vs 9 for `2026-09-18-predicted-edges-dev`.
  Lost: cn04 [0,1,1] -> [0,0,0], su15 [1,1,1] -> [0,1,0], tu93 [1,2,2] -> [0,0,1]. Won by the
  cap: cn04 ACTION5 710 -> 144 and re86 503 -> 194 re-tests.
- Keep or drop: keep the cap and breadth-first (ablations `ablate-nocap`, `ablate-nobreadth`
  both 5: neither flag is the cause). The drop is re-measured with the fixed bar detector in
  `2026-09-18-detector-fix-dev`.

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [0, 0, 0]           0       0.0     1000     276   14.81
ft09   [0, 0, 0]           0       0.0     1000    63.7    4.53
g50t   [0, 0, 0]           0       0.0     1000    37.3   10.24
ka59   [0, 0, 0]           0       0.0     1000     249    6.57
lp85   [1, 1, 1]           1      2.22     1000    18.7    2.01
ls20   [0, 0, 0]           0       0.0     1000   886.7    20.7
m0r0   [0, 0, 0]           0       0.0     1000    55.3   12.79
r11l   [1, 1, 1]           1      4.76     1000   208.7    4.78
re86   [0, 0, 0]           0       0.0     1000     226   41.62
s5i5   [0, 0, 0]           0       0.0     1000    74.3    2.02
sb26   [0, 0, 0]           0       0.0     1000     320   11.95
sc25   [0, 0, 0]           0       0.0     1000   491.7   10.89
sk48   [0, 0, 0]           0       0.0     1000   519.7   13.13
sp80   [1, 1, 1]           1      0.03     1000   207.3   18.97
su15   [0, 1, 0]           0       0.0     1000     211    5.43
tu93   [0, 0, 1]           0       0.0     1000      31    8.12
vc33   [2, 2, 2]           2      0.04     1000   143.7    4.87
wa30   [0, 0, 0]           0       0.0     1000     147   10.46
TOTAL  games=18 seeds=3 sum_median_levels=5 mean_median_score=0.39 actions/level=3176.5 wall=611.7s fallbacks=0
```
