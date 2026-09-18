# 2026-09-18-predicted-edges-dev (step 2 continued: effects by signature, predicted edges)

- What changed: `effects` flag. Click effects by object signature (colour+shape+size) and
  non-move key effects by avatar appearance, as relative diffs; a signature consistent 3 times
  is global. Predictable actions that are no-ops or lead to a state already in the graph are
  not executed; they enter the graph as edges marked `predicted` so BFS keeps its connectivity,
  and execution later overwrites them. Same for predictable moves (vacated cells filled with the
  learned floor colour). Planner disabling is now rate-based (>= 3 mispredictions and >= 25% of
  checked predictions) and counted per event, not per cell.
- Result: dev 3 seeds, 1000 choices: **9 median levels**, RHAE 0.37. cn04 level 1 won on two
  seeds (first median win on cn04), tu93 [1,2,2], s5i5 down to [0,0,1], m0r0 0 this run.
  Re-test share (accounting, seed 0): still ~75%. cn04 ACTION5 563 and re86 ACTION5 488 of
  1000: each rotation is predictable but leads to a never-visited state, which the current rule
  still visits. Click games unchanged (s5i5 844, su15 697): their effects depend on position or
  timing, not on the object signature.
- Verdict: keep (no regression, cn04 gain, connectivity restored), criterion still not met.
- Why the criterion cannot be met by step 2 alone: under an exploration objective, "known
  mechanic in a new state" is how new states get visited; prediction removes the need to visit
  only when the goal says the state is irrelevant. The accounting's "retest" mixes true waste
  (predictable, into a known state: now removed) with exploration by known mechanics (predictable,
  into a new state: still needed without a goal).
