Verify Kaggle readiness: `make test`, `make verify-local`, `make notebook`; grep the notebook for pip
installs, URLs, or network calls; estimate per-game wall time from the last bench and multiply by an
assumed hidden roster of 100 games; confirm it fits the runtime budget with 20% margin. Report pass/fail
per check. Do not run `make submit`.
