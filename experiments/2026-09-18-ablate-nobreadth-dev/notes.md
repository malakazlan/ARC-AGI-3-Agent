# 2026-09-18-ablate-nobreadth-dev (ablation: `breadth_first: false`)

- What changed: nothing in code; breadth-first class ordering (try every untried action class
  once before repeating any) switched off, everything else as in 2026-09-18-dials2-dev.
- Result: dev 3 seeds, 1000 choices: **5 median levels**, RHAE 0.37. Same games won as with it
  on (lp85 1, r11l 1, sp80 1, vc33 2); tu93 [0,0,2] flaky as before; sp80 needed 153 states
  instead of 25 (the avatar takes longer to elect without breadth-first).
- Verdict: breadth-first is not the cause of the 9 to 5 drop and helps the election; keep it.
