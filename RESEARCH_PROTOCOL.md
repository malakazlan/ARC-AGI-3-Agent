# RESEARCH_PROTOCOL.md — how we work on this agent

Add to CLAUDE.md: "Follow docs/RESEARCH_PROTOCOL.md for every non-trivial change."

## Mindset
We are not implementing a spec. We are searching for the mechanism that makes an agent solve unseen
games in near-human action counts. Every step: what do we know, what do we believe, how do we check.
The score is the ground truth. Elegance, features, and lines of code are not.

## The loop (mandatory for every experiment)

1. **Diagnose first.** Before proposing anything, read the last benchmark results and per-game traces.
   State in numbers what is failing and where (which games, which levels, actions wasted on what).
2. **Ground it.** Cite the fact or source behind the fix: a measured trace, a doc page, a paper, a prior
   winner's write-up, or "my hypothesis, unverified". Never present a guess as a fact.
3. **Hypothesis.** One sentence: "If we change X, metric Y moves by roughly Z because W."
   Name the metric that would prove it wrong.
4. **Cheapest test.** Find the smallest experiment that can kill the hypothesis. Often a script on
   recorded traces, not a full benchmark. Prefer offline analysis of logged trajectories.
5. **Run.** Dev split only, 3 seeds. Record config diff, numbers, wall time in experiments/<id>/.
6. **Judge honestly.** Keep / drop / needs more. < 5% is noise. Report negative results too.
7. **Think again.** After the result, ask: what does this reveal about the games? Update
   docs/INSIGHTS.md with the general lesson, not the implementation detail.
8. **Decide.** One line in docs/DECISIONS.md.

## Thinking hard, when to do it
- Before choosing an algorithm: write the problem formally (state, actions, cost, what is unknown).
  Then ask which known method fits that formulation and why the alternatives do not.
- When a result surprises you: stop, do not patch. Pull traces, look at frames, find the real cause.
- When stuck: list 3 different mechanisms humans use for this situation, pick the cheapest to test.
- Always compare to the human number for that level. That gap is the only target.

## Parallel research (use it)
- Independent hypotheses run in parallel: one git worktree per experiment
  (`git worktree add ../exp-<name> -b exp/<name>`), one subagent per worktree, each running its own
  `make bench SPLIT=dev`. Main branch stays clean.
- Subagent roles that work well:
  - Analyst: reads traces and results, produces diagnosis and ranked hypotheses. Writes no code.
  - Builder: implements one hypothesis behind a flag, writes tests, runs bench.
  - Reviewer: checks for game-specific hacks, holdout leakage, Kaggle-fit violations, and unmeasured
    claims. Blocks the merge if any are found.
- Merge only after the Reviewer passes and the number beats the current baseline on dev.
- Never run more parallel benchmarks than CPU cores allow; state expected wall time first.

## Reporting format (every phase / experiment report)
- Diagnosis (numbers)
- Hypothesis and its source
- What was built (short)
- Result table: baseline vs new, dev, 3-seed median, wall time
- Verdict: keep / drop / more
- Insight: one general lesson about the games
- Next 3 hypotheses ranked by expected gain vs cost

## Anti-patterns (stop if you see yourself doing these)
- Adding features without a failing diagnosis behind them.
- Tuning until a number goes up without understanding why.
- Looking at holdout results while iterating.
- Hardcoding anything that looks like a specific public game.
- Writing a lot of code before running the cheapest possible test.
