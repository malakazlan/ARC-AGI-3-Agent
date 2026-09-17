# ARC-AGI-3 Agent (ARC Prize 2026)

Offline agent for the ARC Prize 2026 ARC-AGI-3 Kaggle competition. It enters an unseen grid
game with no instructions, learns what its actions do by interacting, infers the goal, and
clears levels in as few actions as possible.

- Plan and schedule: [docs/ROADMAP.md](docs/ROADMAP.md)
- Verified environment facts: [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)
- Decisions: [docs/DECISIONS.md](docs/DECISIONS.md), progress: [docs/PROGRESS.md](docs/PROGRESS.md)
- Working rules for contributors and tooling: [CLAUDE.md](CLAUDE.md)

## Setup (Linux or WSL2 Ubuntu, Python 3.12)

```
make setup          # venv, pinned deps, vendored framework
make verify-local   # 2-game smoke test
make play-local     # every public game
make test           # unit tests
make notebook       # build the Kaggle notebook (never hand-edit it)
```

Kaggle submission needs a token at `.kaggle/access_token` and your username in
`notebooks/kernel-metadata.json`. `make submit` pushes; the human clicks Submit on Kaggle.

License: MIT-0. Third-party licenses: [THIRD_PARTY.md](THIRD_PARTY.md).
