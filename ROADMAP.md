# ROADMAP — ARC-AGI-3 Agent (Sep 17 → Nov 8, 2026)

## What we are building (one paragraph)
An offline agent that enters an unseen 64x64 grid game with no instructions, learns what its actions
do by interacting, infers the win condition, clears levels, and does it in as few actions as possible.
Core = deterministic exploration over a state graph + action-effect learning + goal inference +
cross-level memory. Learned models and a local LLM are optional plugins, added only if they measurably
help and fit Kaggle's offline runtime budget.

## Fixed dates
- Sep 30: Milestone 2 (optional; notebook must be public + open source by then to be eligible)
- Oct 26: entry + team-merger deadline
- Nov 2: final submissions (pick 2)
- Nov 8: paper deadline
- Dec 4: results

## Standing rules
- 1 Kaggle submission per day. Submit daily once Baseline 1 exists.
- Never tune on holdout. Median of 3 seeds. Changes < 5% are noise.
- No game-specific code. Every module must generalize.
- Everything behind a config flag, everything measured, everything logged in experiments/.

---

## Phase 1 — Pipeline (Sep 17–19)
Claude Code:
- make setup/list-games/verify-local/play-local with random agent; save games.json
- dev/holdout split (70/30, seeded), LICENSE (MIT-0), THIRD_PARTY.md, pyproject with pins
- make notebook builds; Makefile works on WSL
Human:
- Move dev to WSL2. Accept Kaggle rules. Create Kaggle token → .kaggle/access_token
- Set kernel-metadata.json username
- Play every public game yourself on three.arcprize.org; note actions per level and what the goal was.
  This is your human baseline intuition; write it in docs/HUMAN_PLAY.md
Learn:
- Frame format, actions 1–7, GAME_OVER vs level reset vs full reset semantics (ENVIRONMENT.md)
Exit: random agent runs end to end locally and the notebook builds.

## Phase 2 — Baseline 1: graph explorer (Sep 19–23)
Claude Code:
- arc3/ package scaffold with interfaces + tests on synthetic grids
- State graph keyed by frame hash; per state: tested/untested legal actions
- Prune no-op actions; mark GAME_OVER edges; avoid known-bad edges
- Choose action = shortest path to nearest untested (state, action) pair (arXiv 2512.24156)
- On level win: store path; replay shortest known path when re-entering a known state
- Global time budget in is_done(); fail-safe random fallback
- eval/benchmark.py → experiments/<id>/results.json; make bench
Human:
- Read arXiv 2512.24156 (graph paper) and Blind Squirrel README
- First Kaggle submission (~Sep 21) even if weak. Confirm score > 0 and runtime OK.
Learn:
- Why brute-force exploration caps efficiency; how graph size explodes without masking
Exit: Baseline 1 numbers on dev (levels, actions/level, wall time). Logged.

## Phase 3 — Perception + smarter exploration (Sep 24–30)
Claude Code:
- Object segmentation (connected components by color), object attributes (color, size, bbox, shape)
- Frame diff → which objects moved/changed
- Volatility mask: cells that change without action (timers, animations) excluded from state hash
- Click targeting (ACTION6): prefer small, rare-colored, button-like objects; skip object types whose
  clicks never change anything (dead-signature, from Reki)
- Action-effect table: per action → observed effect type (moves agent, toggles, no-op) per state class
- Novelty bonus: prefer transitions that reveal new objects/regions
Human:
- Decide Milestone 2: if Baseline scores anything on LB, make notebook public by Sep 30 (free upside)
- Daily submissions; keep a submissions log (date, version, LB score, notes)
Learn:
- Object-centric representations; count-based/novelty exploration; Go-Explore
Exit: dev levels up vs Baseline 1; state-graph size down; holdout run once.

## Phase 4 — Goal inference + memory + efficiency (Oct 1–8)
Claude Code:
- Win-signal analysis: diff the frames before levels_completed increments; hypothesize win condition
  (object reached region, colors matched, count reached)
- Progress signals: partial-goal detectors used to bias exploration (rank actions that move toward
  hypothesized goal)
- Cross-level memory: reuse action-effect table, goal hypothesis, dead-signatures on next level
- Cross-game memory (mechanism-level only: "ACTION1–4 were movement in 80% of games")
- Efficiency: replay shortest path; avoid re-exploring; commit to a plan once goal hypothesis confident
Human:
- Read Tsividis et al. (theory-based RL) and Chollet "On the Measure of Intelligence"
- Design review: which continual-learning idea from your research fits here (what transfers across
  levels, what must be forgotten)
Learn:
- Goal inference from sparse signals; hypothesis testing loops
Exit: actions per level down on levels 2+; later levels reached more often. Holdout run.

## Phase 5 — Learned helpers (Oct 9–15)
Claude Code (ablation for each, keep only if it helps):
- Action-effect predictor: small CNN predicting "will this action change the frame" (StochasticGoose)
- Value model: distance-to-win from state graph, trained online after each win (Blind Squirrel)
- Both must train in seconds on T4 and fall back cleanly if disabled
Human:
- GPU pod for parallel benchmark runs; verify same numbers on T4-class hardware
Learn:
- Online training under tiny budgets; when learned priors beat hand rules
Exit: measured delta per helper on dev + holdout. Drop what doesn't help.

## Phase 6 — Optional local LLM reasoner (Oct 16–21) — GO/NO-GO decision at start
Go only if: Baseline+helpers plateau AND a quantized model (Qwen/Gemma ~27–31B, or smaller) fits
Kaggle GPU + time budget with margin. Evidence: Milestone 1 top 3 were all local LLM agents.
Claude Code:
- Reasoner plugin: given object summary + action-effect table + diff history, propose goal
  hypothesis and next 1–4 actions; called sparingly (every N steps or when stuck)
- Offline model weights as Kaggle dataset; wheelhouse for vLLM/llama.cpp; hard timeouts
Human:
- Test model throughput on Kaggle T4/RTX6000 before committing
Exit: LB delta vs no-LLM version. If not clearly better, ship without it.

## Phase 7 — Freeze + paper prep (Oct 22–28)
- Freeze features. Robustness: exceptions, time guards, memory, 100+ game roster simulation
- Full ablation table on dev + holdout (3 seeds)
- Repo cleanup, README, THIRD_PARTY.md, reproduce-from-scratch instructions
- Notebook public under open-source license
- Team merge decision before Oct 26 if useful

## Phase 8 — Final (Oct 29–Nov 8)
- Oct 29–Nov 2: pick 2 final submissions (best LB + most robust)
- Nov 3–8: paper (method, ablations, what transfers, failure analysis). Submit to paper track.

---

## Decisions needed from you now
1. WSL2 for dev? (recommended yes)
2. Attempt Milestone 2 (Sep 30)? Costs nothing beyond making the notebook public early.
3. Holdout size: 30% of public games OK?
4. Team: solo, or open to merging before Oct 26?
5. Compute: which pod/GPU for benchmarks, and will you mirror T4 runs to check Kaggle fit?

## What you personally must do every week
- Click Submit daily; log LB score
- Review each phase report; approve next phase
- Play/re-watch replays of games the agent fails; write what a human sees that the agent misses
- Keep docs/DECISIONS.md honest
