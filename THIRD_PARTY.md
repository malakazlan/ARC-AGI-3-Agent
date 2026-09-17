# Third-party code and dependencies

Our code: MIT No Attribution (see `LICENSE`). Everything below is what the agent or the dev
loop depends on, with the license as reported by `pip show` on 2026-09-17.

## Runtime on Kaggle (must be offline-installable from the competition wheel dir)

| Package | Version | License | Why |
|---|---|---|---|
| arc-agi | 0.9.9 | MIT | Game engine client, local + gateway wrappers |
| arcengine | 0.9.3 | MIT | FrameData, GameAction, GameState, base game |
| numpy | 2.5.3 | BSD-3-Clause (+0BSD, MIT, Zlib, CC0 parts) | Grid math |
| pydantic | 2.13.5 | MIT | Pulled in by arc-agi |
| python-dotenv | 1.2.3 | BSD-3-Clause | Pulled in by the agents framework |
| requests | 2.34.2 | Apache-2.0 | Pulled in by arc-agi |
| flask, matplotlib, pillow | 3.1.3 / 3.11.2 / 12.3.0 | BSD-3 / matplotlib (PSF-style) / MIT-CMU | Pulled in by arc-agi; unused by the agent |

Kaggle provides `arc-agi` and `python-dotenv` wheels in
`/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels`. Anything else the
agent imports must already be in the Kaggle image or be attached as a dataset of wheels.

## Vendored / copied code

| Source | License | Where |
|---|---|---|
| arcprize/ARC-AGI-3-Kaggle-Starter | MIT (per repo) | `Makefile`, `scripts/*.py`, `agent/my_agent.py` (starting point), `docs/STARTER_README.md` |
| arcprize/ARC-AGI-3-Agents | MIT | Cloned into `vendor/` by `make setup`, not committed |
| Kaggle sample "Stochastic Goose" (DriesSmit/ARC3-solution) | see notebook header | Read for reference only, in `reference/` (not committed), nothing copied |

## Dev-only

| Package | Version | License |
|---|---|---|
| kaggle | 2.2.4 | Apache-2.0 |
| pandas | 3.0.5 | BSD-3-Clause |
| pyarrow | 25.0.1 | Apache-2.0 |
| pytest | 9.0.2 | MIT |

Update this file whenever a dependency is added. Adding one to the Kaggle runtime also needs
an offline install path (wheel dataset) recorded in `docs/DECISIONS.md`.
