# 2026-09-18-planner2-dev (step 2: movement planner, controllability-based avatar)

- What changed: `planner` flag. Avatar = the object whose displacement depends on the key
  (autonomous drifters excluded); per-colour passability from executed moves (passes / blocks /
  kills, partial strokes vote blocks beyond); predictable moves are never re-tested; BFS over
  predicted positions to the nearest unknown terrain; 3 mispredictions disable planning for the
  level (logged as `planner_resets`). Expiry is now read from the bar only (the clock rule
  looped a deterministic policy into rebuilding its graph forever).
- Merge criterion (owner): re-test share < 20% and median actions per won level down 2x.
- Result: dev 3 seeds, 1000 choices: **9 median levels** (prior 9, first planner run 10), RHAE
  0.37 flat. cn04 level 1 won for the first time on one seed; tu93 median 2 -> 1.
  Accounting (seed 0): sp80 level 1 in **74 actions** (was 559, human 39) with 0 mispredictions;
  but re-test share overall is still ~75% because (a) non-move keys are re-tested per state
  (cn04 ACTION5 710 of 1000, re86 503), (b) colour-level passability is undecidable on m0r0 and
  ls20 (mixed votes: blocking there is not a cell-colour property), (c) the avatar is
  recognised late on ls20 (259), re86 (124), tu93 (111).
- Keep or drop: keep the code behind the flag (no regression, mechanism demonstrated), criterion
  **not met**. Completion needs prediction for non-move keys and clicks (effects by signature)
  and a planner over predicted states, not only positions.
