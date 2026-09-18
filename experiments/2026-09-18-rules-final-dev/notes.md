# 2026-09-18-rules-final-dev (final defaults: rule policy, dial cap off, breadth-first over move keys)

- What changed vs `2026-09-18-rules-defaults-dev`: breadth-first kept, but only over the move
  keys 1-4 (each direction pressed once before any repeats: elects the avatar and shows the bar
  draining under different keys); clicks and other keys go by the prior as before.
- Result: **11 median levels, RHAE 1.20** (flags off: 11 / 1.10; explorer best 9 / 0.37).
  ls20 [2,2,2] score 10.71, vc33 [2,2,2] 3.79, r11l 4.76, lp85 2.22, su15 [1,1,1],
  s5i5 [0,1,1], sp80 [1,1,1]. tu93 [0,2,2] with score 0.02 (flags off: [2,2,2], 0.71): its
  seed-0 run and its efficiency are worse with breadth-first on; g50t [0,0,1] -> 0; sc25
  [2,0,0] on one seed. cn04 stays 0 (lost at the election change, one level on 1-2 seeds before).
- Keep or drop: keep as default (RHAE is the score). tu93's sensitivity to the opening order is
  the next thing to look at on the explorer side; on the rule side, ls20 L3 (consumable refills,
  ~63-action budget) needs the subgoal plan of design v2 section 6.
