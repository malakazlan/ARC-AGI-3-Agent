Run an experiment. Args: $ARGUMENTS = short name + hypothesis.
1. Create experiments/<date>-<name>/ with config.yaml capturing the diff from default config.
2. Run `make bench SPLIT=dev SEEDS=3`. Do not touch holdout.
3. Write results.json and notes.md (what changed / numbers vs current baseline / keep or drop).
4. Print a 5-line summary. Ask before running holdout.
