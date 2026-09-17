# Insights

General lessons about the games, one entry per lesson, with the experiment that produced it.
Implementation details belong in DECISIONS.md, not here. Mark unverified beliefs as such.

- 2026-09-17 (`2026-09-17-baseline1-dev`) — Systematic frontier exploration beats random on
  levels (5 vs 2 median levels on 18 dev games at 1000 actions) but not on efficiency: won
  levels cost 160 to 340 actions against human baselines of 7 to 40. Exploring everything is
  the wrong objective once the mechanics are known; the agent needs a goal, not a bigger map.
- 2026-09-17 (`2026-09-17-baseline1-dev`) — On roughly a third of the dev games almost every
  action produces a never-seen state (about 850 states per 1000 actions), so the frontier
  never shrinks. Hypothesis, unverified: timers or animation cells are in the state key. The
  cheapest check is an offline pass over recorded frames counting cells that change with no
  action effect.
- 2026-09-17 (`2026-09-17-traces-dev`, trace analysis) — **Killed:** the "timer/animation cells
  poison the state key" hypothesis. Zero cells change on 50% or more of steps in any dev game;
  masked and raw state counts are identical on all 18. The technical report agrees: "the
  environment's state does not change asynchronously from the agent's actions". The state
  explosion is genuine: movement games produce one new state per step (0% no-ops on ls20,
  re86, wa30, r11l, sp80), and click games where most clicks change something do the same
  (cn04 90% click hit rate). The opposite failure exists too: on ft09, lp85, sb26, su15 the
  frontier exhausts (67 to 98% no-ops) and the explorer spins on random legal actions.
- 2026-09-17 (technical report, sections 2.2 and 4.3) — Humans win by treating the tutorial
  level as instruction: they identify the controllable object and the goal in a handful of
  actions, then execute. Random or exhaustive play is designed to fail: environments are
  validated so a random policy wins a level less than 1 in 10,000 times, and the official
  leaderboard cuts a level off at 5x the human median actions. Efficiency is therefore a
  completion requirement, not a bonus.
- 2026-09-17 (offline probe on `2026-09-17-traces-dev`) — **Revised:** the volatility idea was
  right in spirit, wrong in form. Nine dev games (cn04, g50t, ka59, m0r0, re86, s5i5, tu93,
  wa30, partly ls20) carry a countdown row on the top or bottom border whose cells change at
  identical offsets after every reset: an energy bar. Each cell changes once per attempt, so a
  frequency threshold never sees it. Masking those cells collapses unique states (g50t 549 to
  65, ka59 844 to 104, s5i5 661 to 33, tu93 505 to 38). Same games die at a fixed cadence
  (51, 76, 101, 130, 201 steps), i.e. a per-attempt action budget, not a lethal action. Two
  general mechanics follow: budgets are visible as a monotone border indicator, and death at
  the budget boundary says nothing about the last action.
- 2026-09-18 (offline determinism probes on `2026-09-17-traces-dev`) — Masking the bar alone
  breaks determinism: the same masked state and action once leads onward and once to
  GAME_OVER, because the bar was empty. Counting steps does not fix it (g50t deaths alternate
  at 83 and 129 steps: energy cost differs per action). Reading the indicator does: in every
  budget game the bar is fully drained in the frame before death (fraction 1.00), and once
  such deaths are treated as expiry the violations vanish on cn04, ka59, m0r0, s5i5, tu93 and
  re86. General lesson: a HUD element is a resource readout; use its value, not the clock.
  Residual violations on g50t, sc25, sp80 exist even on raw frames, so those games have hidden
  state or randomness and need a different idea.
