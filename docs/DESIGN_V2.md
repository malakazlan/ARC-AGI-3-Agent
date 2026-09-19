# DESIGN_V2 — Prior-driven discovery + rule-store exploitation

Status: lead design for review. Builds on arc3/ perception, avatar model, accounting, bench.
Old agent stays as control. v2 runs behind `agent=v2`.

## 0. The claim
Every ARC-AGI-3 game is a deterministic rule system with a detectable goal. A human wins with few
actions because they (a) assume that, (b) act on what is different, (c) read the change, (d) map the
change onto a small library of goal patterns, (e) verify, (f) reuse. v2 makes each step explicit,
costed, and measured.

## 1. Universal priors (hard-coded, game-agnostic)
P1 Determinism: same state + same action = same result. Violations are logged, not assumed.
P2 A goal exists and `levels_completed` is its only certain signal. GAME_OVER is negative.
P3 Something is controllable (avatar) OR actions act on the world directly (click/keyboard puzzles).
P4 Rare things matter: objects with rare signature (colour, shape, size) are candidates for goal,
   tool, or exit. Uniform, large regions are walls/floor.
P5 Change matters: what changed after an action is the information; unchanged = no information.
P6 Obstacles are cost or death until proven otherwise. Never assume value.
P7 Resources exist: a bar or counter that drifts monotonically is a resource; things that restore it
   are refills.
P8 Later levels reuse earlier rules plus a small delta.

Where P4 fails: puzzles with many identical tiles (sort/fill/toggle games). Covered by goal
templates T4-T6 below, not by salience.
Where P1 fails: timing games (s5i5). Accept the loss; do not bend the architecture for them.

## 2. Rule store (per game, persists across levels; a compact prior set persists across games)
```
tools:        signature -> {move_key(vec), dial(k, prop), rotator, transporter(edge), refill,
                            lethal, no_op, unknown}
displays:     [(changeable_panel, static_panel, props_compared)]
goal:         {template, params, progress_fn, confidence}
passability:  per-cell bool with colour prior
avatar:       signature, key->vec map
deaths:       [(state_summary, action)]  -> lethal signatures
level_paths:  shortest winning action sequence per level
cross_game:   P(key i is movement), P(click effect by object rarity), template hit-rates
```

## 3. Perception (reuse + extend)
- Segment objects; signature = (colour set, shape hash up to rotation/reflection, size bucket).
- Diff after each action -> list of events: moved(obj, vec), prop_changed(obj, prop, old, new),
  appeared(obj), disappeared(obj), death, level_up, none.
- Salience(obj) = rarity(signature) * small(size) * static * not_avatar. Top-k = probe targets.
- Resource bar: region changing monotonically without action, or per action at fixed rate.

## 4. Discovery mode (no goal hypothesis yet)
Goal: form a goal hypothesis in as few actions as possible.
```
loop:
  if avatar unknown: press each key once (<=5 actions), elect avatar by controllability
  target = argmax over (salient objects, untested keys, click candidates)
           of  expected_info_gain / action_cost
        expected_info_gain: untested signature=1, partially known=0.5, known=0
        action_cost: path length (avatar games) or 1 (click)
  execute, read events
  update tools[signature] from events (dial: same prop cycles; transporter: |vec|>1;
                                       refill: resource up; lethal: death)
  run hypothesis generator on events (section 5)
  if best hypothesis confidence >= tau: switch to exploit
  if no untested targets and no hypothesis: fall back to frontier explorer, keep logging
```
Budget guard: if discovery exceeds B actions (start B=80) with no hypothesis, drop tau and take the
best template available.

## 5. Goal hypothesis library (ordered by prior; each has progress_fn and verify)
T1 match_display: a changeable object C resembles a static object S (same shape family or same
   size/box) but differs in props -> goal: C.props == S.props. progress = matched/total props.
   verify: when progress==1, go to exit-like object (rare, boxed, edge) or wait for level_up.
T2 reach: avatar reaches rare static object X. progress = 1 - dist/dist0. verify: level_up on
   arrival.
T3 collect_then_reach: count of signature K decreases when touched -> collect all, then T2.
T4 make_uniform: after actions, a region trends toward one colour/pattern -> goal: all same.
   progress = fraction uniform.
T5 fill_or_clear: count of signature K trends monotonic across actions -> drive to 0 or max.
T6 unlock_sequence: an object changes only after another changed -> ordered dependencies;
   progress = stages done.
Resemblance test (T1): for changed C and each static S, score = shape_match(rot/refl) +
colour_family + size_match + boxed(S). Best S above threshold -> hypothesis.
Scoring: confidence = prior(template) * evidence; evidence rises when progress_fn increases
after actions predicted to help, falls when it does not. Multiple hypotheses kept, best executed.

## 6. Exploit mode (goal hypothesis exists)
```
level start (>=2): segment; match signatures to tools -> known; unknown -> delta list
subgoals = ordered by (progress gain, path cost); include refill if projected resource < margin
plan = A* over avatar positions (or over predicted states for click games), edges:
       move keys (learned vec), transporters (cost 0), dials (k presses), passability per-cell
execute step; read events
  mismatch: update that edge/cell, re-plan (disable planner only if same edge fails twice)
  death: mark lethal signature, RESET (level reset keeps progress), re-plan around it
  delta object on path or blocking: probe it once, update tools, re-plan
  progress stalls for M actions: demote hypothesis, next best or back to discovery
level_up: store path, store any new tools, carry goal to next level
```

## 7. Cross-game memory (within one Kaggle run)
Update cross_game priors after each game: which keys were movement, template hit-rates,
click-effect-by-rarity. Use only as tie-breakers in discovery ordering. Never as hard rules.

## 8. Safety
Global deadline; per-game action cap; any exception -> random legal action; never plan through
lethal edges; RESET only after death or when provably stuck.

## 9. Metrics (report all, every bench)
- actions_to_hypothesis (discovery cost), hypothesis_correct_rate (did level_up follow)
- re-test share (target <20%), actions per won level vs human (target <=2x on L2+)
- planner mismatches per level, deaths per level, delta probes per level
- levels, RHAE

## 10. Acceptance
- ls20: L1 <= 60 actions, L2-L4 <= 2x human, 3/3 seeds.
- Dev: RHAE up vs old agent, no game regresses > 1 level.
- Holdout once, after dev passes.

## 11. Build order (each step: tests first, synthetic grids, then bench)
1. Rule store + event extraction from diff + signature tools (dial, transporter, refill, lethal).
2. Hypothesis library T1-T3 + resemblance test + discovery policy.
3. Exploit planner over rule store; delta probing; mismatch handling.
4. T4-T6 for non-avatar games. 5. Cross-game priors. 6. Tune tau, B, M on dev only.

## 12. Known risks
- Resemblance false positives (decorative panels). Mitigation: verify-by-exit costs one path; demote
  on failure.
- Click games with 4096 targets: discovery ordering by salience is the only lever; if it fails,
  we're back to exhaustive. Measure on ft09/lp85.
- Multi-property goals where one property is hidden until another is set (T6). Progress stalls
  will catch it late; acceptable for now.

## 13. Track B: goal naming by a local VLM (offline experiment)
Question: can a local vision-language model served by vLLM name the goal of an unseen level
from a few frames plus our world-model summary? Measured offline only; nothing is wired into
the agent until the numbers say so. Code: `arc3/reasoner/{summary,prompt,render,client}.py`,
harness `eval/reasoner_eval.py`, truth `eval/goal_truth.json`, dry run `make reasoner-dry`.

- Inputs per query: the last `--frames` (default 3) grids of the first level, rendered as PNG
  with the fixed 16-colour palette at 8 px per cell, plus `world_summary` (grid size, the 8
  most salient objects, avatar if known, key vectors, tools, energy bar, deaths, level, the
  template list with one-line meanings). Queries at trace indices `--steps 0,3,6,10`, using
  only what the frames show at that point (no learned vectors or tools yet).
- Output per query: JSON `{"template": match_display|reach|collect|count_to_zero|make_uniform|other,
  "goal": one sentence, "progress": what to measure, "next": next sub-goal}`; parsed tolerantly
  (fences, prose), recorded raw in `eval/results/reasoner_<model>.json`.
- Metric: per dev game `named_within_10` = some query at step <= 10 names the truth template;
  also `first_correct_step`. Headline = fraction of dev games named within 10. Truth comes from
  the coverage table in `docs/GAMES.md`.
- Decision: >= 50% named within 10 -> wire the VLM as a level-1 fallback that proposes a
  template when discovery stalls, with the planner executing (the model never picks actions);
  < 30% -> drop Track B and keep the rules-only discovery. In between: try a bigger model or
  more frames once, then decide.
- Kaggle fit: RTX 6000 24 GB or 2xT4 16 GB; a 7B-class VLM at fp16 or AWQ, 10-30 calls per game,
  a few seconds each, inside the 6 h budget for 100+ games; weights attached as a Kaggle dataset,
  offline install; permissive licence only (Qwen2.5-VL line is Apache-2.0), recorded in
  `THIRD_PARTY.md`. Degrades to the rules-only agent when the model is missing or time is tight.
