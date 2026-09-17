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
