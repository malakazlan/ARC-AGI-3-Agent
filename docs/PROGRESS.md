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
