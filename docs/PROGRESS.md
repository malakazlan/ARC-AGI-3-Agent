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
