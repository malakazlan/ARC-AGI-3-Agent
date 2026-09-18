# 2026-09-18-reach-dev

- What changed: T2 reach and T5 collect templates in the rule policy. Reach candidates are
  hollow frames the avatar fits in, then avatar-coloured rare objects, then other rare small
  objects; each is entered once and verified by a level-up (`reach_tried`). A touched object
  that vanishes with no other effect is a consumable; the policy collects all instances of a
  consumable class before retrying reach targets. The explorer probes unknown keys in place
  instead of ping-ponging toward "unknown terrain (0 left)".
- Result vs baseline (`2026-09-18-swept-final-dev`, 13 / 1.36): **13 median levels, RHAE 1.33**.
  tu93 [3,3,2] -> [3,3,3] (median score 2.86 -> 2.47, L3 slower); re86 states 257 -> 45 and
  wa30 329 -> 197 (fewer wasted positions, still no win); m0r0 lost its one lucky seed; the
  rest identical. Within noise on the total; no public dev game is a pure reach game yet, so
  the template is validated on toys only (reach 25 steps, collect 102, carry-over 40).
- Keep or drop: keep (no loss, tu93 steadier, needed groundwork for T5 count-to-zero).

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [1, 1, 1]           1      0.05     1000     425   38.16
ft09   [0, 0, 0]           0       0.0     1000    46.7    8.08
g50t   [0, 0, 0]           0       0.0     1000    51.3   36.01
ka59   [0, 0, 0]           0       0.0     1000   169.3   23.24
lp85   [1, 1, 1]           1      2.22     1000    14.7    3.01
ls20   [2, 2, 2]           2     10.71     1000     168   59.72
m0r0   [0, 0, 0]           0       0.0     1000    80.3   36.84
r11l   [1, 1, 1]           1      4.76     1000   289.7    9.25
re86   [0, 0, 0]           0       0.0     1000    44.7   14.96
s5i5   [0, 1, 1]           1       0.0     1000   156.7    3.45
sb26   [0, 0, 0]           0       0.0     1000      45   23.28
sc25   [0, 0, 0]           0       0.0     1000   378.7   14.11
sk48   [0, 0, 0]           0       0.0     1000   210.7   25.68
sp80   [1, 1, 1]           1      0.01     1000    93.3   21.65
su15   [1, 1, 1]           1      0.01     1000   375.3    9.14
tu93   [3, 3, 3]           3      2.47     1000    34.7   35.83
vc33   [2, 2, 2]           2      3.79     1000   316.3    5.19
wa30   [0, 0, 0]           0       0.0     1000     197   11.68
TOTAL  games=18 seeds=3 sum_median_levels=13 mean_median_score=1.33 actions/level=1421.1 wall=1137.8s fallbacks=0
```
