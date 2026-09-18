# Insights

General lessons about the games, one entry per lesson, with the experiment that produced it.
Implementation details belong in DECISIONS.md, not here. Mark unverified beliefs as such.

- 2026-09-17 (`2026-09-17-baseline1-dev`) â€” Systematic frontier exploration beats random on
  levels (5 vs 2 median levels on 18 dev games at 1000 actions) but not on efficiency: won
  levels cost 160 to 340 actions against human baselines of 7 to 40. Exploring everything is
  the wrong objective once the mechanics are known; the agent needs a goal, not a bigger map.
- 2026-09-17 (`2026-09-17-baseline1-dev`) â€” On roughly a third of the dev games almost every
  action produces a never-seen state (about 850 states per 1000 actions), so the frontier
  never shrinks. Hypothesis, unverified: timers or animation cells are in the state key. The
  cheapest check is an offline pass over recorded frames counting cells that change with no
  action effect.
- 2026-09-17 (`2026-09-17-traces-dev`, trace analysis) â€” **Killed:** the "timer/animation cells
  poison the state key" hypothesis. Zero cells change on 50% or more of steps in any dev game;
  masked and raw state counts are identical on all 18. The technical report agrees: "the
  environment's state does not change asynchronously from the agent's actions". The state
  explosion is genuine: movement games produce one new state per step (0% no-ops on ls20,
  re86, wa30, r11l, sp80), and click games where most clicks change something do the same
  (cn04 90% click hit rate). The opposite failure exists too: on ft09, lp85, sb26, su15 the
  frontier exhausts (67 to 98% no-ops) and the explorer spins on random legal actions.
- 2026-09-17 (technical report, sections 2.2 and 4.3) â€” Humans win by treating the tutorial
  level as instruction: they identify the controllable object and the goal in a handful of
  actions, then execute. Random or exhaustive play is designed to fail: environments are
  validated so a random policy wins a level less than 1 in 10,000 times, and the official
  leaderboard cuts a level off at 5x the human median actions. Efficiency is therefore a
  completion requirement, not a bonus.
- 2026-09-17 (offline probe on `2026-09-17-traces-dev`) â€” **Revised:** the volatility idea was
  right in spirit, wrong in form. Nine dev games (cn04, g50t, ka59, m0r0, re86, s5i5, tu93,
  wa30, partly ls20) carry a countdown row on the top or bottom border whose cells change at
  identical offsets after every reset: an energy bar. Each cell changes once per attempt, so a
  frequency threshold never sees it. Masking those cells collapses unique states (g50t 549 to
  65, ka59 844 to 104, s5i5 661 to 33, tu93 505 to 38). Same games die at a fixed cadence
  (51, 76, 101, 130, 201 steps), i.e. a per-attempt action budget, not a lethal action. Two
  general mechanics follow: budgets are visible as a monotone border indicator, and death at
  the budget boundary says nothing about the last action.
- 2026-09-18 (offline determinism probes on `2026-09-17-traces-dev`) â€” Masking the bar alone
  breaks determinism: the same masked state and action once leads onward and once to
  GAME_OVER, because the bar was empty. Counting steps does not fix it (g50t deaths alternate
  at 83 and 129 steps: energy cost differs per action). Reading the indicator does: in every
  budget game the bar is fully drained in the frame before death (fraction 1.00), and once
  such deaths are treated as expiry the violations vanish on cn04, ka59, m0r0, s5i5, tu93 and
  re86. General lesson: a HUD element is a resource readout; use its value, not the clock.
  Residual violations on g50t, sc25, sp80 exist even on raw frames, so those games have hidden
  state or randomness and need a different idea.
- 2026-09-18 (engine click probe from level starts; death probe on traces) â€” One click per
  object is the wrong action space in two ways. Where it matters: r11l is an aiming game (24
  background cells, 24 outcomes) and su15 has a keypad that segmentation fuses into one object
  (9 cells, 9 outcomes). Where it wastes: on ft09, lp85 and sb26, 40 to 88% of clicks hit
  object classes that never change anything. Deaths are also class-shaped: on sp80, 34 of 37
  deaths come from ACTION5 from 37 different states. Humans learn "that kind of thing does
  nothing / kills" after two or three tries and stop; the explorer re-learns it per state.
- 2026-09-18 (engine click probe) â€” s5i5 changes on every click, anywhere, with one outcome:
  its bars move by themselves each action and the only decision is when to click. Timing games
  need the phase in the state, which contradicts bar masking; parked.
- 2026-09-18 (`2026-09-18-prior-dev`, traced seed) â€” Class-level action effects transfer
  across states and levels: "this kind of thing does nothing" cut wasted clicks on sb26 from
  67% to 1% and on su15 from 16% to 2%, and median dev levels went 6-7 -> 9. Two limits
  showed up at once. (1) When the frontier is empty of live classes the agent is blind: ft09
  and lp85 level 2 stay at 80-98% no-ops, so the winning action is not among "one click per
  object" at all. (2) A commit action that both wins and kills (sp80 ACTION5, 19% kill rate)
  cannot be judged by class; whether it kills depends on where things are. That is a
  state-conditional effect, i.e. a small predictive model over object relations, not a prior.
- 2026-09-18 (`eval/action_accounting.py` on 11 won levels) â€” Learning a level's mechanics
  costs about 18 actions, human scale; 77% of our actions re-test a known action class in a
  new state. The gap to humans is not perception or discovery, it is that we do not carry what
  we learned from one state to the next. Anything that predicts a transition instead of
  executing it attacks the biggest term directly.
- 2026-09-18 (avatar and win probes on traces) â€” In 9 of 11 keyboard games one multi-colour
  blob moves by a consistent vector per key (once the energy bar is excluded from the diff);
  the key-to-direction map is game-specific (m0r0, sc25). Winning clicks target one colour per
  game and vc33 uses the same colour on levels 1 and 2. Agentness and a carried goal are
  cheap to detect and are exactly what the tutorial level is designed to teach.
- 2026-09-18 (`2026-09-18-step1-validation`) â€” Seeing motion at object level is what makes it
  robust: matching segmented objects by colour, shape and size reads the true displacement
  where a cell-level rule confuses a uniform block moving one cell with its own width. Avatars
  step 3 to 6 cells per key, never 1, so "adjacent cell" is the wrong unit; the learned vector
  is. A blocked key with the frame changing elsewhere is the cheapest passability fact there
  is. Where clicks act on the thing clicked, an object signature predicts the outcome nearly
  perfectly (lp85 93%, sb26 95%); where position or timing decides, it predicts nothing.
- 2026-09-18 (step 2, `2026-09-18-planner2-dev`) â€” Controllability is the right definition of
  "avatar": on sp80 the model first latched onto drifting bars that move on every step; once
  the avatar had to be the object whose displacement depends on the key, mispredictions went
  from 80 to 0 and level 1 took 74 actions instead of 559. Two limits of colour-level
  passability showed up: on m0r0 and ls20 the same colour both passes and blocks (blocking is
  a property of objects or tracks, not cells), and a deterministic policy dies at identical
  step counts for non-budget reasons, so clocks must never decide expiry. The remaining
  re-tests are non-move keys and clicks tested per state: the planner must predict those too.
- 2026-09-18 (owner's first-contact play of ls20 L1-L5, `docs/HUMAN_PLAY.md`) â€” Three things a
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
- 2026-09-18 (`2026-09-18-predicted-edges-dev`) â€” Skipping a predictable action must not drop
  its edge: without predicted edges the graph lost connectivity and exhausted early (8 median
  levels); with them, 9 and cn04's first median win. The deeper lesson: prediction alone cannot
  remove "known mechanic, new state" actions, which are 75% of what we do, because without a
  goal every new state is worth a visit. The owner's ls20 notes say the same from the other
  side: after level 1 a human spends zero actions on known rules because the goal tells them
  which states matter. The next lever is the goal, not more prediction.
- 2026-09-18 (step 3, ls20 autopsies with the rule policy) — Level 1 of ls20 falls from 887 to
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
- 2026-09-18 (ls20 level 2 frames) — Not every death is a GAME_OVER. On ls20 an empty energy
  bar restarts the level in place: a full-frame flash of the bar's colour over five animation
  frames, avatar and panel back at the level start, one digit of the bottom-right attempts
  counter consumed, state still NOT_FINISHED. Level 2 also drains about two bar cells per
  action and offers refill objects drawn in the bar's colour. Nothing in the explorer sees this:
  its budget and death logic key on GAME_OVER, so the rule policy walked a 17-step path to the
  exit on an empty bar and was reset mid-way, four times. The energy is a resource the planner
  must read, and the flash-then-start-state pattern is how a silent death is recognised.
- 2026-09-18 (bar detector on a toy with no bar) — The sequence-based bar detector, needed to
  find ls20's refilling bar, masked the player's own first steps on a toy with no bar: two
  deterministic attempts leave the start at the same offsets, and the "first change" comparison
  with a tolerance of 2 cannot tell that from a drain. Two priors fixed it without losing any
  real bar (identical masks on all 18 dev games, ls20 856 to 105 states): a bar drains as a
  front that sweeps monotonically along its long axis, and a cell the avatar has walked over is
  never a bar. The second is world-model-informed perception: once the avatar is known,
  perception should use it.
- 2026-09-18 (energy on ls20 L2/L3, toys) — Energy is a resource with three things to read and
  one to plan. Read: (1) the bar within the first attempt: a line whose cells switch off in
  spatial order at a steady cadence while different keys are pressed, then grown to the whole
  object it belongs to at the level start (a refill mid-attempt shifts the cross-attempt
  schedule, so only the bar's front ever agrees across attempts); (2) the rate, as cells lost
  per action over the last stretch without a rise (L1 one cell, L2 two, L3 four per action);
  (3) refills, as objects drawn in the bar's colour whose touch makes the bar rise. Plan: a leg
  is affordable when its length plus a reserve to the nearest refill fits the bar, and a
  detour once chosen is walked to the end, because re-deciding every step dithers between
  "refill" and "dial" until the bar is empty. With this ls20 L2 is won in 45 actions. L3 is
  not: its refills are consumed on use (two rings, each worth one bar), so the level has a hard
  budget of about 63 actions and the dial-refill-dial round trips spend it. The next lever is
  the subgoal plan from design v2 section 6 (order dial, colour dial, exit by path cost with
  the energy projected along the whole route), not more reading.
- 2026-09-18 (bisect of the 9 -> 5 drop) — At the dial commit, switching the dial cap off
  alone restored cn04, su15 and tu93 (4 median levels on the three); at HEAD only both flags off
  together restore su15 and tu93, and cn04 is lost since the "two votes per key" election
  change (flaky at one level on one or two seeds before it). Lesson: a flag added together
  with other changes cannot be ablated at a later commit and blamed; ablate at the commit that
  introduced it. Defaults are now both off; the cap's re-test savings on cn04/re86 were an
  accounting metric, the levels are the score.
- 2026-09-18 (ls20 L3 frame) — Level 3 adds a colour dial: a five-colour 3x3 icon. Every ls20
  tool is a compact multi-colour icon that segmentation splits into pieces, and every refill is
  drawn in the bar's colour. Two priors that generalise: small touching pieces of different
  colours are one object; the colour of a resource's display is the colour of the objects that
  restore it.
- 2026-09-18 (tu93 autopsy, `2026-09-18-swept-final-dev`) — Three assumptions in the world
  model were one-cell-step assumptions, and 13 of the 16 keyboard games step 2 to 7 cells.
  (1) A blocked press was blamed on the landing cells' colour; the obstacle was the wall in
  between, so corridors were learned as walls. The press stops at the first obstacle along
  the sweep, so that footprint takes the blame and a successful move clears every colour it
  crossed. (2) The avatar's exact shape key changed as its ring turned, so its motion was
  never matched and a one-cell mark riding on it, or the floor tile it vacated (moving by the
  opposite vector), got elected instead. Identity for election is colour and size; the
  vacated tile is the more numerous of two objects that swap places. (3) A plan that walked
  into the pursuer and ended the game was replanned identically after every reset, because
  the planner knew positions and colours but not deaths. A (position, key) that ended the
  game is forbidden in later plans. Together: tu93 0-2 -> 3 levels, cn04 recovered,
  dev 11 -> 13 median levels, RHAE 1.20 -> 1.36.
- 2026-09-18 (trace probes, `eval/trace_probes.py`) — On the current agent's traces, 19% of
  actions change nothing, 12% change only the step bar, 4% are clicks on a class that never
  responded. Of the 10 level-ups recorded, count-to-zero holds before 3, a region became
  uniform before 4, two frames became equal before 2 (vc33), a class count dropped before 1.
  The waste on g50t (90% bar-only) is not a rule problem: the agent ping-pongs between two
  positions because it has no goal, which is the template problem again.
- 2026-09-18 (click games, ft09 and lp85 autopsies) - Two ways a click game's frontier
  collapses while the level is unexplored. (1) A wrong generalisation: the effect model kept
  only the last few observations per object signature, so twelve legend tiles that ignore
  clicks taught it that the eight playable tiles of the same colour and shape are no-ops;
  every playable click became a predicted self-loop, the frontier was "exhausted" after 5
  states and 80% of the budget went to random clicks on the background. A generalisation
  must die on its first contradiction (KWIK) and be verified once before it is trusted: a
  contradicted signature now predicts per instance, the bar is masked out of the recorded
  effect, and predicted edges are executed before the agent ever clicks at random. ft09: 5 ->
  700 states and level 1 won on every seed. (2) A candidate cap by size: 74 objects and a
  64-click cap ordered small-first dropped the only two arrow buttons on lp85 level 2; the
  cap now keeps one instance of every signature. The rule behind both: never let a shortcut
  remove the last untested representative of a class.
- 2026-09-18 (same build, the ablation) - Two cautions. The bar mask is a trade, not a free
  win: su15's "gravity" clicks change nothing unless something movable is within reach, so a
  no-op rule over the signature is wrong there (6/6 -> 2/6 before verify-first, 4/6 after)
  while s5i5 and ft09 gain; the fix is context in the click signature, not dropping the mask.
  And candidate order below the cap is not free either: reordering vc33's four buttons
  changed its level-2 walk from a median of 40 actions to 190 over 12 seeds, without any
  code path that should depend on order. Treat every ordering change as a behavioural change
  and measure it on 6+ seeds.
