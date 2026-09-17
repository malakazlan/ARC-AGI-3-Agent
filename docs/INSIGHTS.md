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
