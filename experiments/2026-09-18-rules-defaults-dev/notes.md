# 2026-09-18-rules-defaults-dev (rule policy + energy, dial cap and breadth-first both off)

- What changed: defaults `policy: rules`, `dial_cap: false`, `breadth_first: false`; on top of
  `2026-09-18-rules-dev`: silent-restart recognition, single-attempt bar detector grown to its
  object, energy model with refill detours and commitment, two-property match report with
  property-directed dials and delta probes, mask carried across levels.
- Result: **11 median levels, RHAE 1.10** (previous best 9 / 0.37 with the explorer; rule policy
  without energy 6 / 0.56). ls20 [2,2,2] (score 8.29), tu93 [2,2,2] (0.71), vc33 [2,2,2]
  (3.79), su15 [1,1,1], s5i5 [0,1,1] new, lp85 1, r11l 1, sp80 1. Lost vs the 9-level run: cn04
  (flaky at one level, lost at the election change). Per-level scores are capped only per
  level, so the RHAE here is dominated by ls20 L2 (45 actions vs the 123 baseline).
- Keep or drop: keep. Note: with breadth-first fully off the explorer can press one key
  repeatedly on a fresh level (ls20 L1 took 157 actions on seed 0 in the accounting run,
  because the single-attempt bar detector needs two different keys); the follow-up
  `2026-09-18-rules-final-dev` keeps breadth-first over the move keys only.
