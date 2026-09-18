# Bottlenecks (2026-09-18) — eight failure classes, the source that addresses each, the cheapest test

Evidence base: final dev bench `2026-09-18-rules-final-dev` (11 median levels, RHAE 1.20,
3 seeds), the accounting run of the same evening, and the ls20 autopsies. Games at zero
levels in that bench: cn04, ft09, g50t, ka59, m0r0, re86, sb26, sc25, sk48, wa30 (10 of 18).

| # | Failure class | Evidence | Source that addresses it | Cheapest test (offline first) |
|---|---|---|---|---|
| 1 | Re-tests of a known mechanic into an already-known state, on click and key-dial games | su15 320/444 level-1 actions, sp80 316/928, tu93 202/496 are `retest_known` (true waste); cn04 ACTION5 710/1000 before the cap | sonpham no-impact detection (+55% levels); Reki dead-signature; Rudakov status-bar tier; DOORmax failure conditions | Replay recorded traces: count actions whose only change is inside a region that changed on every action regardless of key, and actions on a signature that never changed anything this level. If those two rules cover more than half of `retest_known` on su15/sp80/tu93 the build is worth it. No agent change needed for the test. |
| 2 | No goal hypothesis outside T1 (display resemblance) | 10 of 18 dev games at zero; the rule policy delegates to the explorer on every game without a changeable-vs-static frame pair | EMPA termination conditions (count(class)==0) and subgoals; design v2 T2 (reach), T3 (collect then reach), T5 (fill or clear) | Win probe on recorded level-ups (dev traces exist for all 18 games): for each level-up, which of {a class count reached zero, the avatar reached a rare object, a region became uniform, two regions became equal} holds in the frame before it. Count how many won levels each template explains. Build the top one. |
| 3 | Leg-by-leg energy decisions | ls20 L3: two consumable refills, about 63 actions of energy, dial-refill-dial round trips exhaust it; L3 never won | EMPA planner (goals, subgoals, goal gradients, plan then re-plan on prediction error); design v2 section 6 | Simulate on the L3 start frame offline: with the known tools (rotator, colour icon, refills, target) and the energy model, does an ordered subgoal plan with energy projected along the route fit in 63 actions? If yes on paper, build; acceptance ls20 L3 ≤ 2x human. |
| 4 | Avatar election fragility | cn04 lost since MIN_VOTES 3→2; tu93 [0,2,2] and 0.02 vs 0.71 score depending on the opening order; avatar known at action 5 to 45 on ls20 depending on the opening | Dubey object and motor priors (the controlled thing is the object whose displacement follows the key); Rudakov's breadth over keys | Replay traces of all avatar games with 5 seeds each through the election code only (no agent): report `avatar_known_at` and whether the elected object is the true one. Target: known within 8 actions on every avatar game, no false elections. |
| 5 | Passability by colour, not by object relation | m0r0 and ls20: one colour both passes and blocks; ls20 76 planner mismatches in the last run; m0r0 0 levels | DOORmax relations (touchN(avatar, wall) at class level) | From traces, tabulate move outcomes by (colour ahead, object ahead's class, avatar state). If per-object classes are consistent where per-colour is not on m0r0/ls20, switch the key. |
| 6 | Volatile regions beyond the energy bar (counters, step displays, animations) split states | r11l 290 states, su15 375, sp80 202 at 1000 actions; the graph explorer needs a rebuild every time the mask changes | Rudakov status-bar masking; sonpham HUD band; our own single-attempt bar detector generalised to "changes on every action regardless of key" | Offline on traces: mask every cell whose change count equals the action count (or a fixed fraction) regardless of key, recount distinct states per game. Report the drop; then check no won level's goal region is masked. |
| 7 | Rules keyed by exact signature instead of class | ls20: 2x glyph vs 1x target, icon split into three pieces, each fixed by a special case; a tool learned at one size does not fire at another; cross-level carry-over works only when the boxes keep colour and size | Dubey similarity prior; OO-MDP classes; Schema Networks entities | Offline: re-key the rule store by (colour, scale-free shape) and replay the ls20 L1→L4 traces: does every tool touched on L1 match its counterpart on L2–L4 without a probe? Count probes saved. |
| 8 | Decisions inside the noise | tu93 [0,2,2], g50t [0,0,1], sc25 [2,0,0], cn04 [0,1,1]/[0,0,0] across runs; several keep/drop calls today rested on one level over 3 seeds | sonpham variance study (single-run A/B invalid, ex-ft09 metric, replicate 2–3x) | No build. Protocol: 5 seeds for any decision worth less than 2 median levels; report ex-flaky (games whose seeds disagree) beside the full number; the parallel bench runner makes 5 seeds cost what 3 cost today. |

## Ranking of the next builds (by evidence, not intuition)

1. **Class-level no-impact and dead-signature rules (#1, #6)**: the largest measured waste
   (44–75% of actions on three games we already win, and the same waste is what stops the
   zero-level click games from getting anywhere), the strongest external evidence (+55%
   levels at equal budget), and the test is a trace replay with no agent change.
2. **Win probe and the top-scoring template after T1 (#2)**: ten of eighteen dev games have
   no hypothesis at all; the probe on recorded level-ups tells us which template to build
   before writing it. EMPA's count-to-zero is the prior favourite.
3. **Class keys for rules and tools (#7)**: prerequisite for anything to transfer across
   levels, cheap, and it removes three special cases from the ls20 code.
4. **Subgoal plan with energy projection (#3)**: unlocks ls20 L3–L4 (the owner's acceptance
   line) but is worth one game until #2 exists.
5. **Election robustness (#4)** and **relation-level passability (#5)**: each is worth about
   one level (cn04, m0r0) and is measured offline first.
6. **Seed protocol (#8)**: adopted now, it changes how the above are judged, it is not a build.

## What this does not say

- Nothing here needs a GPU or an LLM. The workload is CPU-bound and single-process; a 16–32
  core box makes a 5-seed dev bench a 2-minute run. Colab's 2 CPU cores would not help; its
  GPU is not used.
- The two Milestone-1 winners are LLM agents; their transferable lessons are the two rules in
  #1 and the noise protocol in #8, not their models.
