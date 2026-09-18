# Design: goal and planning layer (for review)

Status: proposal, 2026-09-18. Nothing here is built. Every claim below cites a measurement in
`experiments/` or a probe on recorded traces; predictions are marked as such.

## 1. The problem, stated formally

- Observation: a 64x64 colour grid after every action; a level-up is visible only as
  `levels_completed` incrementing; death as `GAME_OVER` with an empty frame.
- Actions: up to 5 key actions, a click on any of 4096 cells, sometimes undo.
- Cost: every action sent counts. Score per level is `(human / ours)^2`, capped at 1.15, and
  the official leaderboard cuts a level off at 5x human. Human baselines on dev levels we win
  are 7 to 78 actions.
- Unknown at the start of a game: which object we control, what each key does, what stops or
  kills us, and what the goal is. Known from the technical report: the environment never
  changes without an action, level 1 is a tutorial, later levels compose the same mechanics.

What we do today (explorer + countdown mask + action prior) treats every distinct frame as a
new state and tests known actions again in each one. That is the whole cost.

## 2. Evidence

**Action accounting on the 11 won levels** (`eval/action_accounting.py`, seed 0, 1000 actions):

| category | actions | share |
|---|---|---|
| learn (first 3 tries of an action class) | 198 | 4% |
| retest (known class, new state) | 3580 | 77% |
| navigate (plan steps, resets) | 502 | 11% |
| waste (no-ops, deferred picks, deaths) | 350 | 8% |

Learning costs about 18 actions per level, which is human scale. Re-testing is 77% of everything.

**Avatar probe** (traces of `2026-09-18-prior-traces`, energy bar masked, any colours): share of
state-changing moves explained by one blob translating by one vector, and the dominant vector per
action:

| game | moves | explained (>=0.8) | A1 | A2 | A3 | A4 |
|---|---|---|---|---|---|---|
| cn04 | 840 | 100% | up 100% | down 100% | left 100% | right 100% |
| re86 | 822 | 97% | up | down | left | right |
| sp80 | 852 | 96% | up 71% | down 94% | left 100% | right 96% |
| wa30 | 880 | 93% | up 85% | down 89% | left 78% | right 78% |
| sc25 | 765 | 92% | diagonal moves; direction map differs |
| ls20 | 986 | 86% | up 100% | mixed | left 100% | right 100% |
| ka59 | 570 | 100% | up | down 82% | left 97% | right 73% |
| m0r0 | 675 | 100% | up | down 56% | left | left 97% (A4 is not "right" here) |
| g50t | 644 | 70% | | | | |
| sk48 | 610 | 35% | | | | |
| tu93 | 497 | 1% (49% at >=0.5) | cursor plus board changes |

So an avatar exists and is detectable from a handful of moves in 9 of 11 keyboard games, and the
key-to-direction map is game-specific (m0r0, sc25) and must be learned, not assumed.

**Win probe** (what the winning action did): click games win by clicking a specific colour
(lp85 colour 8, r11l 15, s5i5 4, su15 3, vc33 colour 9 on both level 1 and level 2). Movement
wins: g50t's avatar moved into colours 9 and 5; sp80 won by the commit key ACTION5.

**Click-position probe** (engine, from level starts): position within an object matters on r11l
(24 background cells, 24 outcomes) and on su15's keypad (9 cells, 9 outcomes); it does not on
s5i5, vc33, lp85, ft09, sb26. Hidden state or randomness exists on g50t and sc25 (violations on
raw frames).

## 3. Design

Four mechanisms, each behind a config flag, each with its own kill metric.

### 3.1 Avatar detection and global action effects (learned once per game)

- After each key action that changed the frame, run the translation test used in the probe
  (bar cells excluded, any colours): find the vector `d` and the cell set `A` such that the diff
  is explained by `A` moving by `d` (threshold 0.8).
- Avatar = the cell set that moves in at least 3 of the first 5 explained moves. Per action id
  keep a histogram of vectors; the effect of a key is its dominant vector once it has 3 votes.
- Passability model, per colour: when a key with a known vector produces no change, the colours
  in the cells the avatar would have entered get a "blocks" vote; when it produces a non-expiry
  death, they get a "kills" vote; when it produces a level-up, a "goal" vote. Three votes decide,
  a contradiction resets that colour to unknown.
- These are game-level facts, kept across levels (the memory module), re-validated on the first
  moves of each new level; a mismatch relearns from scratch for that level.
- Click games: no avatar. Their global effects are the action prior's class statistics, which
  already transfer across levels.

Kill metric: on the 9 games above, avatar and direction map recovered within 20 actions of level
start in at least 8; predicted next frame matches the observed one in at least 90% of moves.

### 3.2 Abstract state and a planner instead of re-testing

- Abstract state = (avatar position, the rest of the masked grid). Two frames that differ only in
  where the avatar is are different states, but the transitions between them are *predicted*
  from the passability model, not tested.
- Planner: A* (unit cost) over predicted moves on the current grid, targets given by section 3.3
  or, without a goal, by the explorer's frontier (nearest cell whose passability is unknown, or
  nearest state with untested non-move actions). This replaces the current BFS over tested edges
  for movement; the explorer remains the policy for everything the model cannot predict.
- Runtime check: every executed move compares predicted and observed frames. A mismatch marks
  the entered colour unknown, records the transition in the graph as today, and, after 3
  mismatches in a level, disables planning for that level (fall back to the current explorer).
  This is the "same state + same action = same result" assumption checked, not assumed.

Kill metric: retest share on won levels falls from 77% to under 20%; median dev levels do not
drop.

### 3.3 Win-condition hypothesis from the pre-win frame, carried to level 2+

- At every level-up record: the winning action's class; for a move, the colours the avatar
  entered; for a click, the colour and size class clicked; the object inventory delta between
  level start and pre-win frame (bar masked).
- Hypotheses, ranked: `reach colour X` (avatar), `click colour X` (clicks), `remove all colour Y`
  (inventory delta), `commit when <condition>` (key 5/7 wins; condition left to section 3.4).
- On the next level: plan straight for the top hypothesis (A* to the nearest cell of colour X;
  click colour-X objects first). Budget for the attempt: 3x the previous level's winning path
  length. If it does not win, demote the hypothesis and hand control back to the explorer, which
  still records the eventual win to refine the hypothesis.
- Evidence this transfers: vc33 wins levels 1 and 2 by the same colour; the report says later
  levels compose earlier mechanics.

Kill metric: on games where we win level 1, level 2 is reached with fewer actions than level 1
in at least half the cases (today tu93 L2 took 130 vs 491; vc33 L2 took 286 vs 222).

### 3.4 State-conditional commit actions (sp80-type), later

ACTION5 on sp80 kills 19% of the time and wins otherwise, from states that differ in avatar
position. A class prior cannot judge it; a small predictor over avatar-relative features
(what is under, beside and below the avatar) can. This is the Blind Squirrel value-model idea at
toy scale (logistic regression, trained online after each death or win). Built only after 3.1 to
3.3 are measured.

### 3.5 Click candidates where position matters

From the probe: per-cell candidates for objects up to 16 cells (keypads), plus a coarse lattice of
background cells (every 8th cell) when the class prior says background clicks change things
(r11l). Kept behind a flag; measured separately.

### 3.6 Orchestration per level

```
DISCOVER  (first ~20 actions): each key once from the start, translation test, avatar, vectors;
          click games: one click per class until the prior has 3 tries per class
PLAN      goal hypothesis known and passability model consistent: A* to the goal
EXPLORE   otherwise: today's graph explorer, with the planner supplying movement
          between frontier states instead of tested edges
```

Any exception anywhere falls through to the current explorer, then to random legal, as today.

## 4. Predicted actions per level after 3.1 to 3.3 (prediction, not measurement)

Lower bound = learn + navigate from the accounting table (re-tests and waste removed). Upper
bound = twice that plus today's waste (goal hypothesis wrong once, some mismatches). Human
baselines from `eval/games.json`.

| game | level | human | today | learn | navigate | predicted range | RHAE at lower bound |
|---|---|---|---|---|---|---|---|
| lp85 | 1 | 17 | 21 | 16 | 0 | 16 to 33 | 1.13 |
| r11l | 1 | 22 | 11 | 3 | 0 | 11 (already under human) | 1.15 cap |
| g50t | 1 | 78 | 703 | 15 | 10 | 25 to 155 | 1.15 cap |
| m0r0 | 1 | 30 | 489 | 13 | 3 | 16 to 152 | 1.15 cap |
| vc33 | 1 | 7 | 222 | 19 | 4 | 23 to 48 | 0.09 |
| vc33 | 2 | 18 | 286 | 16 | 18 | 34 to 73 | 0.28 |
| s5i5 | 1 | 20 | 658 | 33 | 32 | 65 to 141 | 0.09 |
| su15 | 1 | 22 | 666 | 22 | 43 | 65 to 150 | 0.11 |
| tu93 | 1 | 19 | 491 | 12 | 154 | 166 to 341 | 0.01 |
| tu93 | 2 | 16 | 130 | 0 | 2 | bounded by plan length, ~10 to 30 | 0.3 to 1.15 |
| sp80 | 1 | 39 | 953 | 49 | 236 | 285 to 645 (needs 3.4) | 0.02 |

Reading the table: three levels would reach human efficiency, two more would come within 2x, and
the games whose navigation is dominated by deaths (sp80, tu93 level 1) need section 3.4 as well.
Games we do not win today are not in the table; the design's second-order effect on them is
through 3.3 and 3.5 and is not predicted here.

## 5. Risks

- Multi-avatar or avatar-less movement games (tu93's cursor plus board): detection fails
  gracefully into today's explorer; measured by the 3.1 kill metric.
- Hidden state (g50t, sc25 violate determinism on raw frames): the runtime check disables
  planning per level; no worse than today.
- Goal hypotheses that are true by coincidence: demotion after one failed attempt bounds the
  cost to 3x the previous winning path.
- Kaggle fit: A* on a 64x64 grid is microseconds; memory adds one grid per level. Nothing new
  is installed.

## 6. Build order (each step is one experiment with dev numbers before the next)

1. Avatar and action-effect detector as a pure module, validated offline on the 11 traced
   keyboard games against the probe numbers above, then online with the kill metric of 3.1.
2. Passability model and A* between frontier states with the runtime check; measure retest share
   and dev levels (kill metric of 3.2).
3. Win hypothesis capture and replay on level 2+ (kill metric of 3.3).
4. Click candidates where position matters (3.5), then state-conditional commits (3.4).
