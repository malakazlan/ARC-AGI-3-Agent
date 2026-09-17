# 2026-09-18-prior-dev

- What changed: online action-effect prior (action_prior flag). Per class (key id, or click
  target colour + size bucket): tries, changes, deaths. Untested actions are picked by class
  score; classes dead after 3 tries or lethal after 2 deaths at >= 50% are explored last.
- Hypothesis: no-op click rate on ft09/lp85/sb26 falls under 30% and sp80 deaths under 10
  per 1000 actions.
- Result vs previous best (6-7 median levels, 0.39): 9 median levels, 0.37. New: m0r0 1 and
  lp85 1 on all seeds, s5i5 1 on two seeds, tu93 2 median, r11l level 1 faster (score 4.76).
  Kill metrics: sb26 no-ops 67% -> 1%, su15 16% -> 2% (confirmed); ft09 86% -> 80% and
  lp85 98% -> 98% (not moved: the winning action is outside the candidate set); sp80 deaths
  37 -> 31 (not moved: ACTION5 both wins and kills, class kill rate 19%, so it is correctly
  not deferred; lethality is state-conditional there).
- Keep or drop: keep. Wall 5.4 min, 0 fallbacks.

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [0, 0, 0]           0       0.0     1000    23.3    3.63
ft09   [0, 0, 0]           0       0.0     1000   115.3    5.47
g50t   [1, 0, 0]           0       0.0     1000    22.3    5.79
ka59   [0, 0, 0]           0       0.0     1000     127    3.91
lp85   [1, 1, 1]           1      1.82     1000     9.7    2.34
ls20   [0, 0, 0]           0       0.0     1000   487.3    2.71
m0r0   [1, 1, 1]           1      0.02     1000    20.7    6.15
r11l   [1, 1, 1]           1      4.76     1000     255    6.06
re86   [0, 0, 0]           0       0.0     1000     196    1.73
s5i5   [1, 0, 1]           1       0.0     1000     101    2.79
sb26   [0, 0, 0]           0       0.0     1000   305.7   19.04
sc25   [0, 0, 0]           0       0.0     1000     305    4.35
sk48   [0, 0, 0]           0       0.0     1000   146.3    5.26
sp80   [1, 1, 0]           1      0.01     1000    54.7    3.29
su15   [1, 0, 0]           0       0.0     1000     223    6.03
tu93   [2, 1, 2]           2      0.01     1000     9.3    4.14
vc33   [2, 2, 2]           2      0.04     1000   158.7    4.58
wa30   [0, 0, 0]           0       0.0     1000   175.7    2.11
TOTAL  games=18 seeds=3 sum_median_levels=9 mean_median_score=0.37 actions/level=2076.9 wall=268.2s fallbacks=0
```
