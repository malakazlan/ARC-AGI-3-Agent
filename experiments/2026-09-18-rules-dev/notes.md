# 2026-09-18-rules-dev

- What changed: `policy: rules` (the v2 rule policy wrapping the explorer) at commit bf2b721:
  scale-free display resemblance, T1 match_display with the target display as exit, progress
  held while the avatar overlaps a display, compound icons, ambient-change filter, goal carried
  across levels. No energy logic yet.
- Result vs baseline: **6 median levels, RHAE 0.56** vs 5 / 0.39 for the explorer at the same
  commit (`2026-09-18-detector-fix-dev`). ls20 [1,1,1] at ~25 actions per level 1; g50t
  [1,0,0] new; lp85, r11l, sp80, vc33 unchanged. No game lost.
- Keep or drop: keep; made the default policy in `2026-09-18-rules-defaults-dev`.

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [0, 0, 0]           0       0.0     1000     314   18.84
ft09   [0, 0, 0]           0       0.0     1000    63.7    5.08
g50t   [1, 0, 0]           0       0.0     1000    37.3   17.86
ka59   [0, 0, 0]           0       0.0     1000     256    8.04
lp85   [1, 1, 1]           1      2.22     1000    18.7    2.04
ls20   [1, 1, 1]           1       3.0     1000    58.3   43.65
m0r0   [0, 0, 0]           0       0.0     1000    63.7   21.06
r11l   [1, 1, 1]           1      4.76     1000   208.7    5.48
re86   [0, 0, 0]           0       0.0     1000   222.7    34.4
s5i5   [0, 0, 0]           0       0.0     1000    74.3    2.25
sb26   [0, 0, 0]           0       0.0     1000     320   12.25
sc25   [0, 0, 0]           0       0.0     1000   206.3   12.72
sk48   [0, 0, 0]           0       0.0     1000   562.3    15.1
sp80   [1, 1, 1]           1      0.03     1000      77    9.33
su15   [0, 0, 0]           0       0.0     1000     106    6.54
tu93   [0, 0, 0]           0       0.0     1000      55   12.06
vc33   [2, 2, 2]           2      0.04     1000   143.7    5.21
wa30   [0, 0, 0]           0       0.0     1000     174   10.34
TOTAL  games=18 seeds=3 sum_median_levels=6 mean_median_score=0.56 actions/level=2842.1 wall=726.7s fallbacks=0
```
