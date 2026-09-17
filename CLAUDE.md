# CLAUDE.md — ARC-AGI-3 Agent (ARC Prize 2026)

You are the engineering partner on a research-grade agent for the ARC Prize 2026 ARC-AGI-3 Kaggle
competition. This is not conventional app code. It is an experimental system where every change must be
measured. Read this file fully before doing anything.

## 1. Mission

Build an offline agent that is dropped into an UNSEEN grid game with no instructions, discovers the
mechanics and goal by interacting, and clears as many levels as possible in as few actions as possible.

- Score = RHAE: per level `(human_actions / agent_actions)^2`, capped at 1.15; per game a weighted
  average with level index as weight (later levels count more); total = mean over games.
- Every action sent to the environment counts. Internal compute does not.
- Hidden evaluation set. Nothing game-specific may be hardcoded. Only mechanisms transfer.

Goals in priority order: (1) generalize to unseen games, (2) complete more levels, (3) fewer actions,
(4) clean paper-ready code.

## 2. Hard constraints (never violate)

- No internet at Kaggle eval time. No API models. Everything local/offline.
- Kaggle: Python 3.12, `arc-agi` package, ARC-AGI-3-Kaggle-Starter layout. Runtime budget is finite
  (assume ~6h total for all hidden games until verified). Agent must self-limit via `is_done()` and a
  global deadline.
- GPUs on Kaggle: T4 x2 / P100 / RTX 6000. Dev can use bigger GPUs, but the final agent must fit Kaggle.
- License: our code MIT-0 or CC0. Any third-party code/models must be Apache-2.0 / MIT / GPLv3 or similar
  shareable license. Record every dependency's license in `THIRD_PARTY.md`.
- Deterministic and reproducible: seeds everywhere, pinned versions, no hidden state.
- 1 leaderboard submission per day, 2 final submissions selectable, team max 8, entry/merger deadline
  Oct 26, 2026. Never submit from Claude Code; only prepare. Human clicks submit.
- Hidden roster size unknown (one team measured ~110). Design for 100+ games inside the 6h budget.
- Count RESET as an action in all budgets (gateway behavior unconfirmed).
- Dev runtime is Linux (WSL2 Ubuntu or a Docker `python:3.12` container). No mingw workarounds.

## 3. Repo layout

```
agent/my_agent.py          # Kaggle entry point. Thin. Imports from arc3/ only.
arc3/                      # Real code lives here
  perception/              # grid -> objects, diffs, volatility masks, state hashing
  world_model/             # action-effect learning, transition graph, rule hypotheses
  explore/                 # exploration policies (novelty, Go-Explore style, action pruning)
  goal/                    # win-condition inference, progress signals
  plan/                    # shortest path / replay / planners over the graph
  memory/                  # cross-level and cross-game memory
  reasoner/                # optional local LLM layer (hypotheses, plans). Pluggable, off by default.
  agent.py                 # orchestrator wiring the modules; config-driven
  config.py                # single dataclass config, all knobs, all seeded
scripts/                   # play_local, build_notebook, benchmark, replay viewer
eval/                      # local RHAE scorer, holdout split, experiment runner, results/
experiments/               # one folder per experiment: config.yaml, results.json, notes.md
tests/                     # unit tests per module + smoke test on 2 games
docs/                      # design notes, decisions log, paper drafts
notebooks/                 # auto-generated Kaggle notebook. Never hand-edit.
```

## 4. Architecture principles

- Layered: cheap deterministic mechanisms first (perception, graph, pruning, planning). Learned or LLM
  components are optional plugins behind a config flag and must degrade gracefully to the rules-only
  agent if the model is missing or the time budget is tight.
- Every module has a clear interface and can be unit-tested with synthetic grids, without the game engine.
- State key must be robust: mask volatile cells (counters, animations) before hashing, or the graph
  explodes. Treat "same state + same action = same result" as an assumption that is checked at runtime,
  not assumed blindly.
- Exploration is a budget, not free. Prefer actions that are informative (untested, high novelty,
  target salient objects). Prune no-op actions and GAME_OVER-leading actions.
- After a level is won: extract what changed just before the win, form a goal hypothesis, reuse it on the
  next level. Replay shortest known paths when a state is re-entered.
- No game IDs, level counts, color values, or coordinates hardcoded for a specific public game. If you
  are tempted, stop and write a general mechanism instead.

## 5. Development loop (do this, in this order, for every change)

1. State the hypothesis: "Change X should improve metric Y because Z."
2. Implement behind a config flag when possible.
3. Run unit tests: `make test`.
4. Run smoke: `make verify-local` (2 games, ~30s).
5. Run benchmark on the DEV split only: `make bench SPLIT=dev`. Never tune on HOLDOUT.
6. Record in `experiments/<id>/`: config, per-game levels, actions per level, RHAE estimate, wall time,
   and a 3-line `notes.md` (what changed, result, keep/drop).
7. Only if it helps on dev, run HOLDOUT once: `make bench SPLIT=holdout`. Report both.
8. Update `docs/DECISIONS.md` with a one-line decision entry.
9. Check Kaggle fit: runtime per game, memory, no network, no forbidden deps. `make notebook` must build.

If a change does not move dev or holdout, drop it. Do not keep dead code "just in case".

## 6. Evaluation rules

- Public games are split once into `dev` and `holdout` (see `eval/split.json`). Never change the split
  to make numbers look better. Never look at holdout per-game results while iterating.
- Report median over 3 seeds, not best-of-N.
- Metrics per game: levels completed, actions per completed level, local RHAE estimate (using our own
  recorded human-like baselines where known, else just action counts), wall time, peak memory.
- Local scores are a weak proxy for the hidden leaderboard. Treat improvements under ~5% as noise.

## 7. Coding standards

- Python 3.12, type hints everywhere, dataclasses for state, numpy for grids. No pandas in the agent.
- Pure functions for perception and world-model updates; side effects only in the orchestrator.
- Log compact structured diagnostics (JSON lines) that can be shipped inside the Kaggle notebook output,
  so each daily submission tells us something even without hidden logs.
- Fail safe: any exception inside a module must be caught by the orchestrator and fall back to a valid
  random legal action. A crash on Kaggle = score 0 for everything.
- Time guards: the agent checks elapsed time before every expensive step and has a hard global deadline.
- Tests: every module gets tests on synthetic grids. Smoke test runs the full agent on 2 games in CI.
- Keep functions short. Name things by what they compute, not how.

## 8. What NOT to do

- Do not add an LLM, RL training loop, or big model without a measured baseline first.
- Do not write game-specific heuristics.
- Do not hand-edit `notebooks/submission.ipynb`.
- Do not add dependencies without checking license and offline installability (wheels attached as a
  Kaggle dataset).
- Do not run long benchmarks without asking; state the expected wall time first.
- Do not claim a result you did not measure. If uncertain, say so.

## 9. Commands

```
make setup            # venv, arc-agi, kaggle CLI, framework
make list-games       # all public game ids
make play-local       # agent vs all public games
make play-local GAME=<id>
make verify-local     # 30s smoke test
make test             # pytest
make bench SPLIT=dev|holdout SEEDS=3
make notebook         # build Kaggle notebook (no push)
make submit           # push notebook to Kaggle (human runs this)
make status           # Kaggle run status
```

## 10. Reference material (read before designing a module)

- Docs index: https://docs.arcprize.org/llms.txt (actions, game schema, scoring, local-vs-online)
- Scoring: https://docs.arcprize.org/methodology.md
- Graph exploration paper (3rd, preview): https://arxiv.org/abs/2512.24156
- Blind Squirrel code (2nd, preview): https://github.com/wd13ca/ARC-AGI-3-Agents
- Milestone 1 winners (local LLM agents): https://arcprize.org/blog/arc-prize-2026-milestone-1
- Technical report: https://arcprize.org/media/ARC_AGI_3_Technical_Report.pdf
- Background: Go-Explore; Tsividis et al. "Human-Level RL through Theory-Based Modeling, Exploration,
  and Planning"; Chollet "On the Measure of Intelligence".

## 11. Working style with the human

- Short, direct answers. Bullets. No long frameworks.
- Always state: what you changed, how you measured it, the numbers, and the risk.
- Flag weak ideas and rule violations immediately.
- Prioritize by expected score gain vs effort. Deadline: submissions Nov 2, 2026; paper Nov 8.
- Keep `docs/DECISIONS.md` and `docs/PROGRESS.md` current; they feed the paper.
- Git: never add Claude as co-author or mention it in commits or anywhere. Short commit messages.
- Verified environment facts: `docs/ENVIRONMENT.md`. Schedule and phase gates: `docs/ROADMAP.md`
  (authoritative). Step-level detail for Phases 1-4: `docs/KICKOFF.md`.
