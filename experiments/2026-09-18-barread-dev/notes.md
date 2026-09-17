# 2026-09-18-barread-dev

- What changed: deaths are expiry when the learned bar cells read as drained in the last frame (clock rule kept as fallback)
- Result vs baseline (5 median levels, 0.38): identical to countdown-indep (6 median levels): all public bars drain at a constant rate so the clock already covered them. Offline: determinism violations vanish on the six budget games.
- Keep or drop: keep (correctness, no regression). Current best on dev: 6-7 median levels, RHAE ~0.39.

```
(see results.json)
```
