# Progress

Schedule: `docs/ROADMAP.md`. Step detail: `docs/KICKOFF.md`. Facts: `docs/ENVIRONMENT.md`.

## 2026-09-17 — Phase 0 done, Phase 1 done

- Starter kit in repo, framework vendored, engine verified locally.
- `docs/ENVIRONMENT.md` written with cited facts; the surprises are in its section 8.
- WSL2 Ubuntu provisioned (Python 3.12.14, make 4.4.1). `make setup` passes.
- Random starter on all 25 public games: 0 levels everywhere, score 0.0, no crash,
  58 s wall for 25 games x 81 actions (about 40 ms per action including engine load).
- Split: 25 games, 18 dev / 7 holdout, stratified by tag, seed 20260917.
- Notebook builds; contains one offline pip install (competition wheel dir) and only the
  gateway URL.
- Current best: none. Baseline 1 (graph explorer) is next.

Dev machine: i5-7300HQ, 4 cores, 7.7 GB RAM in WSL. Benchmarks with many seeds will need a pod.

## 2026-09-17 — Phase 2 done (scaffold, tests first)

- `arc3/` package: perception (frame diff, 4/8-connected segmentation, volatility mask,
  masked state hash), config dataclass, engine-agnostic orchestrator with RESET rules,
  legal-action random policy, fail-safe fallback, shared deadline. Other subpackages are
  interfaces only.
- 50 tests, all on synthetic grids or the offline engine, 9 s.
- `agent/my_agent.py` is a thin adapter; `make verify-local` and `make play-local` pass with
  0 fallbacks across 25 games. The legal-random agent cleared 1 level on one game by luck
  (200 actions per game, 50 s wall).
- Notebook bundles `arc3/` (17 cells). `scripts/pod_bench.sh` bootstraps Colab or a pod.
- Next: Phase 3, Baseline 1 graph explorer plus `eval/benchmark.py` and `make bench`.

## 2026-09-17 — Phase 3 done: Baseline 1 measured

- Graph explorer implemented test-first (73 tests, 13 s). `eval/benchmark.py` + `make bench`
  write `experiments/<id>/{results.json,config.yaml,notes.md}`.
- **Baseline 1, dev split, 18 games x 3 seeds, 1000 choices per game, 5 min wall:**
  sum of median levels **5** (lp85 1, r11l 1, sp80 1, vc33 2; ft09 and m0r0 won a level on one
  seed each). Mean median local RHAE **0.38 / 100**. 0 fallbacks, 0 inconsistent edges.
- Random-legal control under the same budget: sum of median levels **2**, mean median RHAE **0.27**
  (`experiments/2026-09-17-random-dev`). Explorer beats random on levels; scores are noise.
- Diagnosis: on a third of the games nearly every action yields a new state (about 850 states
  per 1000 actions), so the frontier never shrinks. Volatility masking is the next experiment.
- `scripts/pod_bench.sh` verified from scratch in a clean Linux container.

## 2026-09-18 — Research loop on the explorer (countdown bars)

- Tooling: trace recording in the benchmark, offline analyzer (`eval/traces.py`), contact-sheet
  renderer (`scripts/render_traces.py`). Looked at the games; read the winners and the report.
- Killed: timer/animation volatility (0 cells). Found: energy bars on 9 dev games that made every
  step a new state, plus fixed per-attempt budgets that were being blamed on the last action.
- Built (tests first): countdown-cell detector with an action-independence rule, bar-read expiry.
- Numbers, dev, 3 seeds, 1000 choices per game: baseline 5 median levels -> 7 (first mask,
  over-masked) -> 6 (independence rule) -> 6 (bar-read, identical). RHAE 0.38 -> 0.39.
  Games with levels: vc33 2 (all seeds), r11l 1, sp80 1, lp85 1, tu93 1 (2 on two seeds).
- Open: r11l/sp80 die about 33 times per 1000 actions from a commit action; s5i5 and tu93 have
  under 40 real states and still no win, suggesting our one-click-per-object candidates miss the
  winning clicks; ls20 has a cyclic bar the detector does not model; g50t and sc25 have hidden state.

## 2026-09-18 — Action-effect prior

- Dev, 3 seeds, 1000 choices per game: **9 median levels** (baseline 5, countdown 6-7).
  RHAE 0.37, flat: won levels still cost hundreds of actions. Wall 5.4 min.
- Confirmed on sb26 and su15 (wasted clicks gone), failed on ft09/lp85 (dead frontier) and
  sp80 (state-conditional deaths). See `docs/INSIGHTS.md`.
- Kaggle readiness unchanged: notebook builds; Phase 4's offline notebook dry run not done yet.

## 2026-09-18 — Phase 4 dry run and action accounting

- `scripts/dry_run_notebook.py`: executes the built notebook's cells into a scratch tree, starts
  the toolkit gateway in competition mode, runs the notebook's own `main.py --agent myagent`
  against it with the repo off sys.path. **PASS**: 25 games, exit 0, 0 tracebacks, 0 fallbacks,
  one ARC3DIAG line per game, 78 s at 150 actions per game. Ready for the first submission.
- `eval/action_accounting.py` on the 11 won levels (seed 0): learn 4%, retest 77%, navigate
  11%, waste 8% of 4630 actions. Learning alone is 198 actions, about 18 per level, i.e. human
  scale. Re-testing known mechanics in every new state is what costs the score.

## 2026-09-18 — Step 1 of the goal/planning layer (offline validated)

- Built and validated offline, not yet wired in: object-level translation finder, avatar model
  (key vectors, continuity tracking, blocked outcomes), click effects by object signature,
  `eval/validate_models.py`. 122 tests.
- Gate met: key map within 20 actions on 9 of 11 keyboard games; move predictions consistent
  in 100% on 7 games, 92% sc25, 85% tu93, 79% m0r0, 73% wa30. Click outcomes predictable by
  signature on lp85 93%, sb26 95%, ft09 40%; not on r11l, su15, s5i5 (position or timing).
- Next: step 2, passability per colour + A* between frontier states with the mismatch check;
  merge metric re-test share < 20% (keyboard and click reported separately) and median actions
  per won level down 2x.

## 2026-09-18 — Step 2 (movement planner), checkpoint

- Built: passability per colour, controllability-based avatar, BFS over predicted positions,
  mismatch reset with logging, partial strokes, bar-only expiry. 143 tests.
- Dev: 9 median levels, RHAE 0.37 (flat). sp80 seed 0: 559 -> 74 actions for level 1 with 0
  mispredictions. Overall re-test share still ~75%: non-move keys (cn04 A5 710/1000, re86 503)
  and clicks are tested per state; m0r0/ls20 passability undecidable by colour.
- Merge criterion not met; plan is to extend prediction to key and click effects by signature
  and plan over predicted states (owner decision pending).

## 2026-09-18 — Step 2 closed

- Effects by signature and predicted edges added; rate-based planner reset; 153 tests.
- Dev: 9 median levels, RHAE 0.37. cn04 first median win. Re-test share ~75%, dominated by
  predictable actions into never-visited states (cn04/re86 ACTION5 ~500 each), which only a
  goal can make unnecessary. Owner's ls20 play notes recorded in `docs/HUMAN_PLAY.md`.
- Next: step 3, win hypotheses (reach colour, click colour, remove all, make region A equal
  region B) carried across levels and planned over predicted states.

## 2026-09-18 � Step 3 (rule policy), checkpoint

- Built behind `policy: rules` (`arc3/agent_v2.py`, `arc3/rules/`): events from diffs, rule
  store, scale-free display resemblance, discovery by touching salient objects (compound
  icons), T1 match_display exploit with the target display as exit, goal carried across
  levels. Bar detector fixed for refilling bars without masking the player's trail. 192 tests.
- ls20 level 1: 23 actions (was 887 with the explorer; acceptance <= 60 met). Level 2 not yet:
  the level restarts silently when the energy bar empties (no GAME_OVER), which nothing
  detects; energy and refills are the next mechanic.
- Dev benches running: rule policy vs explorer (no-regression check) and the explorer with the
  fixed detector (to locate the 9 -> 5 drop: cn04, su15, tu93).

## 2026-09-18 � Step 3, energy and level carry-over

- Added: silent-restart recognition, single-attempt bar detector with object growth, energy
  model (remaining, rate, affordability with a refill reserve), refill discovery by the bar's
  colour, refill commitment, two-property match report with property-directed dials and delta
  probes, mask carried across levels. 201 tests. Defaults switched to the rule policy with the
  dial cap and breadth-first off.
- ls20: L1 25 actions, L2 45 actions (3/3 seeds in the earlier bench for L1). L3 not won: its
  refills are consumable and the dial round trips exhaust a ~63-action budget; needs the
  subgoal plan of design v2 section 6.
- The 9 -> 5 drop of the morning is explained (dial cap and breadth-first together; cn04 lost
  at the election change) and su15/tu93 are recovered by the new defaults.

## 2026-09-18 � Step 3 closed for the day

- Dev, 3 seeds, 1000 actions: **11 median levels, RHAE 1.20** with the rule policy as default
  (explorer best 9 / 0.37 this morning). ls20 L1 25 and L2 45 actions on all seeds (human
  22 / 123), su15 and tu93 recovered, s5i5 level 1 new; cn04 lost since the election change.
- Notebook rebuilt and dry-run PASS on the local competition-mode gateway (25 games, 7 levels,
  0 fallbacks, 0 tracebacks). `make submit` is the owner's step.
- Open: ls20 L3 (consumable refills, needs the subgoal plan), click games' true waste (su15
  75%, sp80 51%), tu93's sensitivity to the opening order, cn04.

## 2026-09-18 � Evening: research pass and world-model fixes

- Docs: `docs/PRIOR_WORK.md` (9 sources against our traces), `docs/BOTTLENECKS.md` (8 failure
  classes, ranked builds), `docs/GAMES.md` and `docs/GAME_CENSUS.md` (what is known and
  measured about all 25 public games), `eval/trace_probes.py` (waste rules and win templates).
- Built from the tu93 autopsy: swept-path passability, shape-tolerant avatar identity with
  the vacated-tile filter, lethal presses forbidden in plans. 206 tests.
- Dev, 3 seeds: **13 median levels, RHAE 1.36** (morning 9 / 0.37; midday 11 / 1.20).
- Parallel benchmark runner: `make bench` uses 4 workers.
- Next by the bottleneck ranking: the count-to-zero goal template (win probe: 3 of 10 wins),
  the click dead-signature rule, then the subgoal plan with energy for ls20 L3.

## 2026-09-18 - Night: reach and collect templates

- Built T2 reach (hollow frame -> avatar-coloured rare object -> other rare object, verified by
  level-up) and T5 collect (a touched object that vanishes with no other effect is a
  consumable; take every instance, then retry the reach targets). Explorer probes unknown
  keys in place. 209 tests; reach toy 25 steps, collect toy 102, carry-over 40.
- Dev, 3 seeds: **13 median levels, RHAE 1.33** (`2026-09-18-reach-dev`; tu93 [3,3,3],
  otherwise within noise of 1.36). Kept.
- Next: click dead-signature rule (trace probe: 4% dead clicks, 12% bar-only), then the
  energy subgoal plan for ls20 L3.
- 2026-09-18 - First Kaggle submission (kernel v1, the 13 / 1.36 agent) scored **0.30 public** (id 56332856, COMPLETE). This is the baseline every later submission is judged against.

## 2026-09-18 - Late: click model and the route planner

- Click model (KWIK-style): effects generalised by signature die on the first contradiction,
  are verified once before being trusted, exclude the step bar, and an exhausted frontier
  verifies predictions before clicking at random. Dev, 3 seeds: **14 median levels, RHAE
  1.35** (`2026-09-18-clickfx2-dev`); ft09 won on every seed; the vc33 slowdown of the first
  version was traced to candidate order and removed (cap-bound diversity only).
- Route planner (`arc3/plan/route.py`): ordered stops with the energy projected along the
  route, refills inserted where it runs dry; wired into the display exploit. ls20 L3 now
  presses the rotator twice in a row instead of walking to a refill between presses, but the
  level still needs the colour tool and the conveyors (a move onto a colour-1 strip carried
  the avatar 20 cells for free): transport learning is the next build.
- Fixes on the way: a walk plan is dropped when the avatar stops moving (ls20 pressed into a
  wall five times); the bar's last cell no longer counts against the rarity of same-shaped
  refills.
