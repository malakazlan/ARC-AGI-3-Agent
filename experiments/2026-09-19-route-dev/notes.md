# 2026-09-19-route-dev

- What changed (on top of the click model, 9c73816): (1) route planner `arc3/plan/route.py`:
  the dials, the nearest untouched object when a property has no dial, and the display exit
  are ordered by an exhaustive search with the energy projected along the route and refills
  inserted where it runs dry; BFS distances over passable cells ride known transports; an
  infeasible route probes the nearest unknown instead of walking to a death. (2) Transports:
  a press that lands the avatar somewhere other than one vector away is learned as a portal
  (ls20 conveyors, 20-25 cells), used by A* and by the route BFS. (3) The matcher pairs the
  only object of its kind across any distance (the 8-cell window stays for alike objects);
  the avatar model reports "blocked" only if the avatar still stands where it was. (4) A
  contradiction halves strong passability evidence instead of erasing it (the floor's 1479
  passes vanished on one misread ride). (5) Probe ranking `arc3/rules/probes.py`: touchable
  from the avatar's region, multi-colour icons first, never a piece of the displays.
- Result vs baseline (`2026-09-18-clickfx2-dev`, 14 / 1.35): **17 median levels, RHAE 1.37**.
  m0r0 0 -> [0,1,1]; sc25 [0,2,0] -> [1,1,2] (0.28); g50t [0,1,0] -> [0,1,1]; tu93 [3,3,3] ->
  [3,3,2] (2.55, noise); everything else identical. ls20 L3 still not won: with both dials,
  both rings and one conveyor known the level needs the second conveyor (pressing up from
  tile (1,9) carries the avatar to (8,9), next to the exit); the agent finds the rainbow
  colour dial but not that ride. Post-bench attempts (every refill instance, two presses for
  a dial under the avatar, strict route walkability, whole-box exit goal) cost ls20 L2 (45 ->
  97 actions) and were reverted; recorded in `docs/INSIGHTS.md`.
- Keep or drop: keep.

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [1, 1, 1]           1      0.05     1000   527.7   47.53
ft09   [1, 1, 1]           1      0.22     1000   693.3    7.51
g50t   [0, 1, 1]           1      0.03     1000    63.3   37.46
ka59   [0, 0, 0]           0       0.0     1000     165   31.61
lp85   [1, 1, 1]           1      2.22     1000      26    5.58
ls20   [2, 2, 2]           2     10.71     1000     108   75.24
m0r0   [0, 1, 1]           1      0.01     1000    77.7   65.13
r11l   [1, 1, 1]           1      4.76     1000   305.3    10.9
re86   [0, 0, 0]           0       0.0     1000    44.7   17.56
s5i5   [0, 1, 1]           1       0.0     1000   129.7    4.11
sb26   [0, 0, 0]           0       0.0     1000   236.3   26.37
sc25   [1, 1, 2]           1      0.28     1000     326   36.36
sk48   [0, 0, 0]           0       0.0     1000   246.3   23.26
sp80   [1, 1, 1]           1      0.01     1000   143.3   28.85
su15   [1, 1, 1]           1      0.01     1000     331   12.14
tu93   [3, 3, 2]           3      2.55     1000      34   42.85
vc33   [2, 3, 2]           2      3.79     1000   237.7     5.8
wa30   [0, 0, 0]           0       0.0     1000   206.7    12.8
TOTAL  games=18 seeds=3 sum_median_levels=17 mean_median_score=1.37 actions/level=1102.0 wall=1473.2s fallbacks=0
```
