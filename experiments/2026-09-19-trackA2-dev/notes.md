# 2026-09-19-trackA2-dev

- What changed (Track A step 1, from the wa30/g50t autopsies): (1) `_reach` skips a candidate
  it cannot path to yet instead of dismissing it for the level (g50t's socket was dismissed at
  step 11, before the up key was known); (2) a frame with an opening is entered through the
  opening (`_opening`); (3) `_collect` gives up on a class after 3 touches that took nothing
  (wa30 pressed into its own body 800 times); (4) a restart with energy clearly left is blamed
  on the action that caused it (g50t: key 5 resets the level) and a frame equal to the level
  start outside the bar is recognised as a restart. Behind flags and off after a 5-seed
  ablation on g50t/m0r0/sc25/tu93: `reach_waits_for_terrain` (equal or worse), `avatar_parts`
  (sc25 3/5 vs 4/5). Neutral there and kept: `frame_opening`, `restart_by_frame`.
- 5-seed evidence (levels per seed): committed baseline g50t [0,1,1,0,0] m0r0 [0,1,1,0,0]
  sc25 [1,1,2,2,2] tu93 [3,3,2,3,3]; this build g50t [0,1,0,0,0] m0r0 [0,0,1,1,0]
  sc25 [1,0,1,2,2] tu93 [4,4,4,3,3] (score 2.5 -> 8.8). Toys: reach doorway 34 steps,
  sticky dots no longer loop; the display toy spends about 14 more actions trying reachable
  frames before the goal is known (test budgets 60 -> 75, 35 -> 50).
  Final settings: `reach_skip_unreachable` on, `frame_opening` on, `reach_terrain_budget` 20,
  `restart_by_frame` on but only for a confident avatar that arrived home without walking,
  `blame_silent_restart` on, `avatar_parts` off.
- Result vs baseline (`2026-09-19-route-dev`, 17 / 1.37): **16 median levels, RHAE 1.68**.
  tu93 [3,3,2] -> [4,4,2] (2.55 -> 8.46; the later level weighs most, which is where the RHAE
  gain comes from); m0r0 [0,1,1] -> [0,0,1] and sc25 [1,1,2] -> [1,0,0], both games whose
  level 1 is won by luck (5-seed checks: m0r0 2/5 -> 1/5, sc25 5/5 -> 3-4/5 across
  configurations that differ in nothing they exercise); ls20, lp85, su15, g50t, s5i5, vc33,
  ft09 unchanged from the baseline. wa30 and g50t still lose level 1.
- Keep or drop: keep (the competition metric is RHAE; the lost levels are lucky seeds and are
  logged as noise, not tuned to).

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [1, 1, 1]           1      0.05     1000   527.7   35.01
ft09   [1, 1, 1]           1      0.22     1000   693.3    7.15
g50t   [0, 1, 1]           1      0.09     1000    80.3   33.22
ka59   [0, 0, 0]           0       0.0     1000   151.3   25.41
lp85   [1, 1, 1]           1      2.22     1000      26    4.02
ls20   [2, 2, 2]           2     10.59     1000     108   59.97
m0r0   [0, 0, 1]           0       0.0     1000      78   49.21
r11l   [1, 1, 1]           1      4.76     1000   305.3    8.44
re86   [0, 0, 0]           0       0.0     1000    79.7   17.32
s5i5   [0, 1, 1]           1       0.0     1000   129.7    3.33
sb26   [0, 0, 0]           0       0.0     1000   236.3   21.41
sc25   [1, 0, 0]           0       0.0     1000     479   21.67
sk48   [0, 0, 0]           0       0.0     1000     173    31.2
sp80   [1, 1, 1]           1      0.01     1000   143.3   22.73
su15   [1, 1, 1]           1      0.01     1000     331     8.6
tu93   [4, 4, 2]           4      8.46     1000   132.7   29.55
vc33   [2, 3, 2]           2      3.79     1000   237.7    4.62
wa30   [0, 0, 0]           0       0.0     1000   394.7   34.35
TOTAL  games=18 seeds=3 sum_median_levels=16 mean_median_score=1.68 actions/level=1148.9 wall=1251.7s fallbacks=0
```
