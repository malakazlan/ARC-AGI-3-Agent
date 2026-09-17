# Decisions log

One line per decision: date, decision, reason, evidence. Newest at the bottom.

- 2026-09-17 — Dev runtime is WSL2 Ubuntu (Python 3.12 via uv, GNU make). Reason: Kaggle is Linux; no Windows shims. Evidence: owner decision; `make setup` passes in WSL.
- 2026-09-17 — Global time budget assumed 6 h for all games, design for 100+ hidden games. Reason: limit not public; community reports 6 to 9 h. Evidence: owner; `docs/ENVIRONMENT.md` section 6.
- 2026-09-17 — Count RESET as an action in every budget; never send RESET unless state is NOT_PLAYED or GAME_OVER. Reason: gateway counting unconfirmed; RESET right after a level-up wipes progress locally. Evidence: `docs/ENVIRONMENT.md` sections 4 and 5.
- 2026-09-17 — Dev/holdout split is seeded (20260917), 30% holdout, stratified by input tag, holdout frozen; new public games go to dev. Reason: stable evaluation. Evidence: `eval/make_split.py`, `eval/split.json`.
- 2026-09-17 — Dependencies pinned to the versions `make setup` produced (arc-agi 0.9.9, arcengine 0.9.3, numpy 2.5.3). Reason: reproducibility. Evidence: `pyproject.toml`, `THIRD_PARTY.md`.
