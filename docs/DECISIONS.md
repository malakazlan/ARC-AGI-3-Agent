# Decisions log

One line per decision: date, decision, reason, evidence. Newest at the bottom.

- 2026-09-17 — Dev runtime is WSL2 Ubuntu (Python 3.12 via uv, GNU make). Reason: Kaggle is Linux; no Windows shims. Evidence: owner decision; `make setup` passes in WSL.
- 2026-09-17 — Global time budget assumed 6 h for all games, design for 100+ hidden games. Reason: limit not public; community reports 6 to 9 h. Evidence: owner; `docs/ENVIRONMENT.md` section 6.
- 2026-09-17 — Count RESET as an action in every budget; never send RESET unless state is NOT_PLAYED or GAME_OVER. Reason: gateway counting unconfirmed; RESET right after a level-up wipes progress locally. Evidence: `docs/ENVIRONMENT.md` sections 4 and 5.
- 2026-09-17 — Dev/holdout split is seeded (20260917), 30% holdout, stratified by input tag, holdout frozen; new public games go to dev. Reason: stable evaluation. Evidence: `eval/make_split.py`, `eval/split.json`.
- 2026-09-17 — Dependencies pinned to the versions `make setup` produced (arc-agi 0.9.9, arcengine 0.9.3, numpy 2.5.3). Reason: reproducibility. Evidence: `pyproject.toml`, `THIRD_PARTY.md`.
- 2026-09-17 — Kaggle handle is `zlanai`; set in `notebooks/kernel-metadata.json`. Evidence: owner.
- 2026-09-17 — Attempt Milestone 2 (Sep 30): notebook goes public once Baseline 1 scores on the leaderboard. Reason: free upside. Evidence: owner.
- 2026-09-17 — Holdout stays at 30%. Team: solo for now. Benchmark pod: later; add a Colab/pod runner script now. Evidence: owner.
- 2026-09-17 — Orchestrator (`arc3/agent.py`) is engine-agnostic: Observation in, ActionChoice out; `agent/my_agent.py` is the only file touching arcengine. Reason: every module unit-testable on synthetic grids. Evidence: `tests/test_agent.py`, `tests/test_my_agent.py`.
- 2026-09-17 — Notebook ships `arc3/` as one readable `%%writefile` cell per module into `/tmp/arc3_bundle`, found via `ARC3_BUNDLE_DIR`. Reason: Kaggle copies only `my_agent.py` into the framework; readable cells keep failed daily runs inspectable. Evidence: `scripts/build_notebook.py`, `tests/test_build_notebook.py`.
- 2026-09-17 — Per-game hard cap 2000 choices and a 5.5 h process-wide deadline shared by all game threads (`process_started_at`). Reason: 100+ games in one process under a 6 h limit. Evidence: `arc3/config.py`.
- 2026-09-17 — Baseline 1 = graph explorer (arXiv 2512.24156 style): raw last-frame hash as state key, candidates = legal simple actions + one click per segmented object (smallest 64 objects first), untested-here first, else BFS to nearest frontier, else random legal; GAME_OVER edges are tested and never planned through. Reason: training-free, deterministic, measurable. Evidence: `arc3/explore/graph_explorer.py`, experiment `2026-09-17-baseline1-dev`.
- 2026-09-17 — Graph is rebuilt on every level change and capped at 5000 nodes per level. Reason: memory with 100+ concurrent games; cross-level memory is a later phase. Evidence: `arc3/config.py`.
- 2026-09-17 — Benchmarks inject config via `ARC3_CONFIG_JSON`; each run gets a fresh clock and its own scorecard run. Reason: no code path differs between bench and Kaggle except the knobs. Evidence: `eval/benchmark.py`.
- 2026-09-17 — `scripts/pod_bench.sh` verified from scratch in a clean `python:3.12-slim` container (apt tools, uv Python, make setup, run). Evidence: Docker run exit 0.
