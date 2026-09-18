# 2026-09-18-ablate-nocap-dev (ablation: `dial_cap: false`)

- What changed: nothing in code; the dial cap (stop pressing a confirmed key dial in every new
  position) switched off, everything else as in 2026-09-18-dials2-dev.
- Result: dev 3 seeds, 1000 choices: **5 median levels**, RHAE 0.39. Same games won as with the
  cap on (lp85 1, r11l 1, sp80 1, vc33 2). Compare 2026-09-18-dials2-dev (cap on): 5 / 0.39.
- Verdict: the dial cap is not what dropped the bench from 9 (predicted-edges) to 5. Neither is
  breadth-first (2026-09-18-ablate-nobreadth-dev: 5). Both flags stay on; the drop came from the
  other changes that shipped with them (the sequence-based bar detector and the avatar election
  changes) and is investigated on those.
