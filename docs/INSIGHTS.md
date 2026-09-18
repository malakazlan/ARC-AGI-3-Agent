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
- 2026-09-18 (engine click probe from level starts; death probe on traces) — One click per
  object is the wrong action space in two ways. Where it matters: r11l is an aiming game (24
  background cells, 24 outcomes) and su15 has a keypad that segmentation fuses into one object
  (9 cells, 9 outcomes). Where it wastes: on ft09, lp85 and sb26, 40 to 88% of clicks hit
  object classes that never change anything. Deaths are also class-shaped: on sp80, 34 of 37
  deaths come from ACTION5 from 37 different states. Humans learn "that kind of thing does
  nothing / kills" after two or three tries and stop; the explorer re-learns it per state.
- 2026-09-18 (engine click probe) — s5i5 changes on every click, anywhere, with one outcome:
  its bars move by themselves each action and the only decision is when to click. Timing games
  need the phase in the state, which contradicts bar masking; parked.
- 2026-09-18 (`2026-09-18-prior-dev`, traced seed) — Class-level action effects transfer
  across states and levels: "this kind of thing does nothing" cut wasted clicks on sb26 from
  67% to 1% and on su15 from 16% to 2%, and median dev levels went 6-7 -> 9. Two limits
  showed up at once. (1) When the frontier is empty of live classes the agent is blind: ft09
  and lp85 level 2 stay at 80-98% no-ops, so the winning action is not among "one click per
  object" at all. (2) A commit action that both wins and kills (sp80 ACTION5, 19% kill rate)
  cannot be judged by class; whether it kills depends on where things are. That is a
  state-conditional effect, i.e. a small predictive model over object relations, not a prior.
- 2026-09-18 (`eval/action_accounting.py` on 11 won levels) — Learning a level's mechanics
  costs about 18 actions, human scale; 77% of our actions re-test a known action class in a
  new state. The gap to humans is not perception or discovery, it is that we do not carry what
  we learned from one state to the next. Anything that predicts a transition instead of
  executing it attacks the biggest term directly.
- 2026-09-18 (avatar and win probes on traces) — In 9 of 11 keyboard games one multi-colour
  blob moves by a consistent vector per key (once the energy bar is excluded from the diff);
  the key-to-direction map is game-specific (m0r0, sc25). Winning clicks target one colour per
  game and vc33 uses the same colour on levels 1 and 2. Agentness and a carried goal are
  cheap to detect and are exactly what the tutorial level is designed to teach.
- 2026-09-18 (`2026-09-18-step1-validation`) — Seeing motion at object level is what makes it
  robust: matching segmented objects by colour, shape and size reads the true displacement
  where a cell-level rule confuses a uniform block moving one cell with its own width. Avatars
  step 3 to 6 cells per key, never 1, so "adjacent cell" is the wrong unit; the learned vector
  is. A blocked key with the frame changing elsewhere is the cheapest passability fact there
  is. Where clicks act on the thing clicked, an object signature predicts the outcome nearly
  perfectly (lp85 93%, sb26 95%); where position or timing decides, it predicts nothing.
- 2026-09-18 (step 2, `2026-09-18-planner2-dev`) — Controllability is the right definition of
  "avatar": on sp80 the model first latched onto drifting bars that move on every step; once
  the avatar had to be the object whose displacement depends on the key, mispredictions went
  from 80 to 0 and level 1 took 74 actions instead of 559. Two limits of colour-level
  passability showed up: on m0r0 and ls20 the same colour both passes and blocks (blocking is
  a property of objects or tracks, not cells), and a deterministic policy dies at identical
  step counts for non-budget reasons, so clocks must never decide expiry. The remaining
  re-tests are non-move keys and clicks tested per state: the planner must predict those too.
- 2026-09-18 (owner's first-contact play of ls20 L1-L5, `docs/HUMAN_PLAY.md`) — Three things a
  human does that the agent does not. (1) Goal by similarity: a region that changes under our
  actions (the bottom-left panel) resembles a static region (the top box); the hypothesis
  "make them equal" follows from the resemblance, not from a win. (2) Tools are property
  dials: touching an object changes a property of the avatar shown in the panel (orientation,
  colour); an effect model keyed by object signature captures exactly that. (3) Rules are
  free after level 1: zero actions on known rules, about two per new mechanic, the rest is
  navigation with an energy check. Level 1 cost the human about one touch per object plus
  the walk; ours costs hundreds because every touch is re-tested per state. The
  predicted-state planner plus a "make region A equal region B" hypothesis type is the direct
  translation of this play.
- 2026-09-18 (`2026-09-18-predicted-edges-dev`) — Skipping a predictable action must not drop
  its edge: without predicted edges the graph lost connectivity and exhausted early (8 median
  levels); with them, 9 and cn04's first median win. The deeper lesson: prediction alone cannot
  remove "known mechanic, new state" actions, which are 75% of what we do, because without a
  goal every new state is worth a visit. The owner's ls20 notes say the same from the other
  side: after level 1 a human spends zero actions on known rules because the goal tells them
  which states matter. The next lever is the goal, not more prediction.
- 2026-09-18 (step 3, ls20 autopsies with the rule policy) � Level 1 of ls20 falls from 887 to
  23 actions once four things a human takes for granted are in the loop. (1) Resemblance is
  scale-free: the target glyph is drawn at 1x in a 7x7 box, the panel at 2x in a 10x10 box;
  pairing by frame colour and comparing normalized shapes finds the pair where box-size
  matching did not. (2) The exit is the target display itself: the matched avatar walks into
  the box (two presses), no separate exit object exists. (3) The avatar drawn inside the target
  is not a change of the target: progress must be held while the avatar overlaps a display,
  otherwise the policy reads "mismatch" and walks back to the dial (this alone cost 4 wasted
  round trips). (4) Small touching pieces of different colours are one object: the rotator is
  a 0/1 icon that segmentation splits in three; probing its pieces as separate tools and
  "exits" rotated the panel away from the match twice. Verified: with all four, one touch,
  one walk, two presses.
- 2026-09-18 (ls20 level 2 frames) � Not every death is a GAME_OVER. On ls20 an empty energy
  bar restarts the level in place: a full-frame flash of the bar's colour over five animation
  frames, avatar and panel back at the level start, one digit of the bottom-right attempts
  counter consumed, state still NOT_FINISHED. Level 2 also drains about two bar cells per
  action and offers refill objects drawn in the bar's colour. Nothing in the explorer sees this:
  its budget and death logic key on GAME_OVER, so the rule policy walked a 17-step path to the
  exit on an empty bar and was reset mid-way, four times. The energy is a resource the planner
  must read, and the flash-then-start-state pattern is how a silent death is recognised.
- 2026-09-18 (bar detector on a toy with no bar) � The sequence-based bar detector, needed to
  find ls20's refilling bar, masked the player's own first steps on a toy with no bar: two
  deterministic attempts leave the start at the same offsets, and the "first change" comparison
  with a tolerance of 2 cannot tell that from a drain. Two priors fixed it without losing any
  real bar (identical masks on all 18 dev games, ls20 856 to 105 states): a bar drains as a
  front that sweeps monotonically along its long axis, and a cell the avatar has walked over is
  never a bar. The second is world-model-informed perception: once the avatar is known,
  perception should use it.
