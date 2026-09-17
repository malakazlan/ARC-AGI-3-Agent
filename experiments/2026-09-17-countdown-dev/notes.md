# 2026-09-17-countdown-dev

- What changed: countdown-cell mask (same offset every attempt, connected groups) + clock-based budget expiry; no action-independence test yet
- Result vs baseline (5 median levels, 0.38): sum median levels 7 vs 5 baseline; tu93 0->2, vc33 stable 2. But r11l seed 1 collapsed to 1 state and g50t showed 57-71 inconsistent edges: over-masking (replayed prefixes look like bars).
- Keep or drop: superseded by the independence rule

```
(see results.json)
```
