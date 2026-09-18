# 2026-09-18-clickfx2-dev

- What changed (click model, from the ft09 and lp85 autopsies): the step bar is masked out
  of recorded click effects; a signature's rule dies on its first contradiction and then
  predicts per instance only; a rule is executed once before it is trusted (verify first);
  an exhausted frontier executes predicted edges, then re-tests the best candidate, before
  any random click; the 64-click cap keeps one instance of every signature (only when the
  cap binds: reordering below the cap changed vc33's walk, 12 seeds, L2 median 40 -> 190).
- Result vs baseline (`2026-09-18-reach-dev`, 13 / 1.33): **14 median levels, RHAE 1.35**.
  ft09 0 -> [1,1,1] (L1 in 151-183 actions, human 43); s5i5 [0,1,1] same; su15 [1,1,1] same;
  vc33 [2,3,2] 3.79 (unchanged); g50t and sc25 one lucky seed each; the rest identical.
  Ablation (6 seeds, 5 click games): the mask is a trade (su15 6/6 -> 2/6 without verify-first
  and cap-bound ordering, s5i5 2/6 -> 6/6, ft09 faster); with the final configuration su15
  4/6, s5i5 3/6, ft09 6/6, vc33 as before. Kaggle public score of the previous kernel: 0.30.
- Keep or drop: keep.

```
game   levels/seed    med lv med score  actions  states  wall s
cn04   [1, 1, 1]           1      0.05     1000     422   51.02
ft09   [1, 1, 1]           1      0.22     1000   693.3    9.69
g50t   [0, 1, 0]           0       0.0     1000    50.7   48.73
ka59   [0, 0, 0]           0       0.0     1000   168.7   30.07
lp85   [1, 1, 1]           1      2.22     1000      26    5.49
ls20   [2, 2, 2]           2     10.71     1000     168   79.93
m0r0   [0, 0, 0]           0       0.0     1000    58.7   54.27
r11l   [1, 1, 1]           1      4.76     1000   305.3   11.75
re86   [0, 0, 0]           0       0.0     1000    44.7   21.55
s5i5   [0, 1, 1]           1       0.0     1000   129.7    4.64
sb26   [0, 0, 0]           0       0.0     1000   236.3   33.63
sc25   [0, 2, 0]           0       0.0     1000   369.3   22.72
sk48   [0, 0, 0]           0       0.0     1000   132.3   37.05
sp80   [1, 1, 1]           1      0.01     1000     127   27.32
su15   [1, 1, 1]           1      0.01     1000     331   11.17
tu93   [3, 3, 3]           3      2.47     1000    34.7   41.36
vc33   [2, 3, 2]           2      3.79     1000   237.7    6.48
wa30   [0, 0, 0]           0       0.0     1000     161   11.02
TOTAL  games=18 seeds=3 sum_median_levels=14 mean_median_score=1.35 actions/level=1200.0 wall=1523.7s fallbacks=0
```
