# 2026-09-18-step1-validation (offline, no agent change)

- What was built: `find_translation` (object-level: segment both frames, match by colour +
  shape + size, read the shared displacement), `AvatarModel` (per-key vector votes, avatar
  template with continuity tracking, blocked-move outcomes), `ClickEffects` keyed by object
  signature (colour + shape + size; a relative diff consistent 3 times is global), and
  `eval/validate_models.py` which replays recorded traces through both.
- Gate (design 3.1): avatar and key map within 20 actions in at least 8 of 9 games; predicted
  move consistent with the observed one in at least 90% of moves.
- Result on `2026-09-18-prior-traces` (seed 0, 1000 actions per game):

```
game   moves explained known@ consistent blocked  keymap
cn04     840      100%      3 100% of 964     134  {1: (-3, 0), 3: (0, -3), 4: (0, 3)}
g50t     644       98%      4 100% of 856     235  {1: (-6, 0), 2: (6, 0), 4: (0, 6)}
ka59     570       96%      3 100% of 889     351  {1: (-3, 0), 2: (3, 0), 3: (0, -3), 4: (0, 3)}
ls20     986       31%      3 100% of 733     441  {1: (-5, 0), 2: (5, 0), 3: (0, -5), 4: (0, 5)}
m0r0     675       64%     10  79% of 520     237  {1: (-5, 0), 3: (0, -4), 4: (0, 4)}
re86     822       92%      3 100% of 862     114  {1: (-3, 0), 2: (3, 0), 3: (0, -3), 4: (0, 3)}
sc25     765       45%      8  92% of 695     358  {3: (0, -4), 4: (0, 4)}
sk48     610       54%    214 100% of 482     167  {1: (-6, 0), 2: (6, 0), 3: (0, -6), 4: (0, 6)}
sp80     852       75%      3 100% of 840     215  {1: (-4, 0), 2: (4, 0), 3: (0, -4), 4: (0, 4)}
tu93     497       98%    125  85% of 817     345  {1: (6, 0), 2: (-6, 0), 3: (0, 6), 4: (0, -6)}
wa30     880       76%      8  73% of 777     135  {1: (-4, 0), 2: (4, 0), 3: (0, -4), 4: (0, 4)}
```

  Key map within 20 actions: 9 of 11 (all 9 design targets; sk48 and tu93 late). Consistency
  at least 90%: 8 of 11. "Blocked" = the key pressed, the frame changed elsewhere, the avatar
  stayed: that is the passability signal for step 2. The three weak games have avatars whose
  appearance changes as they move (wa30, m0r0) or a cursor over a changing board (tu93).
  Step sizes are 3 to 6 cells per key press, never 1; a planner must use the learned vector.

- Click effects by signature (share of clicks whose outcome a global effect predicted correctly
  before the click; an upper bound on re-tests that can be skipped or simulated):

```
game   clicks predicted correct  sigs global
ft09      988       490     398    27      5
lp85     1000       929     927    31     11
sb26      435       414     414    12      4
vc33      970       110      96    84     33
r11l      962         0       0    15      1
s5i5      972         3       1    67      2
su15      939         0       0    15      1
```

  Where clicks act on the object clicked (lp85 93%, sb26 95%, ft09 40%) the signature predicts
  the outcome; where the effect depends on position or timing (r11l aiming, su15 keypad, s5i5
  timing) it predicts nothing, as expected from the click-position probe.

- Re-test share on click games today (from `experiments/action_accounting.json`): s5i5 88%,
  su15 87%, vc33 89% and 86%, r11l 73%, lp85 19%. Merge criterion for step 2 is under 20% on
  both keyboard and click games, reported separately.
- Keep or drop: keep as the step-1 module set; nothing is wired into the agent yet.
