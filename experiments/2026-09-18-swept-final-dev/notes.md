# 2026-09-18-swept-final-dev

- What changed (world model, all from trace autopsies): (1) passability reasons over the
  whole swept path of a multi-cell step, a blocked press blames the first footprint that is
  not known to pass, a move votes passes for every colour crossed, a death votes once per
  colour; (2) avatar identity is colour+size (a ring whose gap turns keeps one identity), the
  translation matcher pairs shape-changed objects by colour, size and box, the vacated floor
  tile that echoes the avatar's move is dropped, election ties go to the rarer then bigger
  object; (3) a (position, key) press that ended the game is never planned again.
- Result vs baseline (`2026-09-18-rules-final-dev`, 11 / 1.20): **13 median levels, RHAE 1.36**.
  cn04 0 -> [1,1,1]; tu93 [0,2,2] -> [3,3,2] (L2 in 23 actions vs human 16, L3 147 vs 34);
  m0r0 [1,0,0] (one seed, new); sc25 [2,0,0] -> 0 (flaky both ways); the rest unchanged.
- Keep or drop: keep.

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [1, 1, 1]           1      0.05     1000   382.7   31.88
ft09   [0, 0, 0]           0       0.0     1000    46.7     7.9
g50t   [0, 0, 0]           0       0.0     1000    50.3   24.12
ka59   [0, 0, 0]           0       0.0     1000   133.3   17.28
lp85   [1, 1, 1]           1      2.22     1000    14.7    2.63
ls20   [2, 2, 2]           2     10.71     1000     168   49.64
m0r0   [1, 0, 0]           0       0.0     1000    54.3   33.41
r11l   [1, 1, 1]           1      4.76     1000   289.7    7.02
re86   [0, 0, 0]           0       0.0     1000     257   22.35
s5i5   [0, 1, 1]           1       0.0     1000   156.7    3.13
sb26   [0, 0, 0]           0       0.0     1000      45   19.13
sc25   [0, 0, 0]           0       0.0     1000   412.7   10.83
sk48   [0, 0, 0]           0       0.0     1000   193.7   21.37
sp80   [1, 1, 1]           1      0.01     1000   118.3    19.1
su15   [1, 1, 1]           1      0.01     1000   375.3    8.03
tu93   [3, 3, 2]           3      2.86     1000      28   25.44
vc33   [2, 2, 2]           2      3.79     1000   316.3    5.01
wa30   [0, 0, 0]           0       0.0     1000   328.7   10.04
TOTAL  games=18 seeds=3 sum_median_levels=13 mean_median_score=1.36 actions/level=1421.1 wall=955.0s fallbacks=0
```
