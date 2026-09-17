# Kickoff plan (phased)

Source: kickoff prompt from the project owner, 2026-09-17. Stop after each phase with a short report
(what was done, what was verified, open questions). Do not skip verification steps.

## Phase 0 — Understand before touching code
1. Read https://docs.arcprize.org/llms.txt, then Actions, Game Schema, Scoring Methodology, Local vs
   Online, ARC Prize 2026 starter pages.
2. Bring https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter into this repo (keep Makefile + scripts).
   Read `agent/my_agent.py`, `scripts/play_local.py`, `scripts/build_notebook.py`.
3. `make pull-sample`, read the official sample agent.
4. Write `docs/ENVIRONMENT.md` with cited facts; mark unknowns UNKNOWN, never guess.

## Phase 1 — Working pipeline
5. `make setup`, `make list-games`, `make verify-local`, `make play-local` with the random starter.
   Confirm score 0.0, no crash. Save the game list to `eval/games.json`.
6. `eval/split.json`: deterministic dev/holdout split (~70/30, seeded).
7. `notebooks/kernel-metadata.json` username placeholder `<KAGGLE_USERNAME>`; `make notebook` builds.
   Never run `make submit`.
8. `LICENSE` (MIT-0), `THIRD_PARTY.md`, `.gitignore`, `pyproject.toml` pinned, pytest config.

## Phase 2 — Scaffold the architecture (interfaces only, tests first)
9. `arc3/` package per CLAUDE.md: perception, world_model, explore, goal, plan, memory,
   reasoner (stub, disabled), agent.py, config.py.
10. Unit tests on synthetic 8x8 grids: frame diff, object segmentation (connected components by
    color), volatility mask, state hashing (stable under masked cells).
11. Wire `agent/my_agent.py` to `arc3.agent.Agent` with a global time budget and fail-safe random
    fallback. `make verify-local` must pass.

## Phase 3 — Baseline 1: graph explorer (no learning)
12. State graph keyed by masked frame hash; per state track tested/untested legal actions; prune
    no-change actions; mark GAME_OVER edges; choose the action with shortest path to an untested
    (state, action) pair (arXiv 2512.24156); on level win record the path and replay shortest known
    path when re-entering a known state.
13. `eval/benchmark.py` + `make bench`: agent on a split, N seeds, writes
    `experiments/<id>/results.json` (levels, actions per level, wall time, summary table).
14. `make bench SPLIT=dev SEEDS=3`. Report numbers = Baseline 1. Log in PROGRESS.md and DECISIONS.md.

## Phase 4 — Diagnostics for blind submissions
15. JSON-lines diagnostics per game (levels, actions, states discovered, time, fallbacks) in notebook
    output.
16. Verify the built notebook installs nothing from the internet and runs the two-game smoke offline.

Stop and report. Later phases (action-effect learning, goal inference, cross-level memory, optional
local LLM reasoner) are planned after Baseline 1 numbers exist.

## Workflow notes
- Branch per experiment (`exp/<name>`), merge only if kept. `main` is always Kaggle-buildable.
- Dev locally for speed; Kaggle only for the daily hidden-set probe.
- Weekly: run holdout once, update PROGRESS.md, re-rank the roadmap.
- Paper: keep DECISIONS.md and experiment folders clean; they become method and ablation sections.
