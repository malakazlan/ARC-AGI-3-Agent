# Prior work, read against our traces (2026-09-18)

For each source: method, core assumption, where it breaks on what we have measured, what we
take. "Our traces" means the dev benchmarks (`experiments/2026-09-18-*`), the action
accounting (`experiments/action_accounting.json`, 2026-09-18 evening: ls20 L1 25 actions 0%
true waste, sp80 L1 928 actions 51% true waste, su15 L1 444 actions 75%, tu93 L1 496 actions
44%), and the ls20 autopsies in `docs/INSIGHTS.md`.

## 1. Tufa Labs, "The Duck" (Milestone 1, 1st) — tufalabs.ai/research/duck-harness, github.com/Tufalabs/duck-harness

- Method: a 27B local LLM in a Python REPL; every observation is a Python variable, the model
  writes code, inspects grids as image plus ASCII, acts; oldest messages evicted so play never
  stops. Score 1.60 +/- 0.45 over 25 public games, 20 passes each.
- Core assumption: a pre-trained model already holds the priors (objects, buttons, keys,
  counters) and the reasoning; the harness must only avoid getting in its way.
- Action efficiency: it comes from the model reasoning before acting (few actions per step of
  thought), not from any search. The organisers' summary of the write-up: "hand-crafted tools
  actually hurt the model; letting it improvise worked better", and the gains came "from
  multimodality and better base models, not hand-built tools".
- Where it breaks on our traces: not applicable directly (no LLM in our loop), but its lesson
  is: a tool that forces a fixed interpretation on every frame costs more than it saves. Our
  analogue is the dial cap, which cost su15 and tu93 a level each while saving re-tests.
- What we take: keep mechanisms as filters on evidence (mask this, prune that), not as forced
  plans; measure every mechanism by levels, not by the metric it was built to move.

## 2. sonpham-org/arc-3 (instrumented Duck fork, 501 commits of experiments)

- Method: same harness, plus a reproduction matrix on GCP spot instances; 927 playable games.
- Findings that matter to us:
  - Noise: "The 25-game mean is noise-dominated. Its ~95% range on a fixed config is roughly
    0.45–2.67", one game (ft09) "swings the 25-game average by ±1.0 on its own"; they score
    ex-ft09 and "replicate anything promising 2–3×".
  - No-impact detection is "the one clear win (+55% ex-ft09, 21 vs 15 levels at equal action
    budget). It stops an explore action whose only board change is the game's deterministic
    HUD/moves band, killing wasted wall-presses."
  - A state-graph planning tool lost: "the plan-rejection block fired zero times, so we paid the
    query-turn cost … for nothing".
- Core assumption: the HUD band is deterministic and separable from the board; actions whose
  only effect is there are wasted.
- Where it breaks on our traces: we mask only the energy bar, and only after detection; on
  click games the counters and step displays still split states (su15 375 states, sp80 202,
  r11l 290 at 1000 actions), and 320 of su15's 444 level-1 actions are re-tests into states
  already in the graph. Our benchmark decisions at ±1 level over 3 seeds are inside their
  noise band (tu93 [0,2,2], g50t [0,0,1], sc25 [2,0,0] in one run).
- What we take: (a) a general no-impact rule: an action whose only change lies in a region that
  changes on every action regardless of key is a no-op for the graph; (b) report an
  ex-flaky metric and use 5 seeds before keeping or dropping anything worth less than 2 levels.

## 3. Reki (Milestone 1, 2nd) — arcprize.org/blog/arc-prize-2026-milestone-1

- Method: Gemma-4-31B vision model returning one JSON action per step; reflection memory
  refreshed every ~10 steps; a 1–4 action plan queue; JSON self-repair; every trick behind an
  environment variable for ablation.
- The two rules that are not LLM-specific: "a numpy click heuristic with hardcoded rules
  favoring small, rare-colored button-like shapes" for fallback and exploratory clicks, and a
  "dead-signature" rule: "when clicking a type of object never changes anything, stop wasting
  clicks on it for the rest of the level".
- Core assumption: buttons are small, rare and distinct; an object type's response to a click
  is a property of the type, not of the state.
- Where it breaks on our traces: our click candidates are object anchors ordered by a prior
  over (colour, size band) classes and the prior only defers a class after 3 no-op tries per
  class per game. We do not order by rarity or size the way Reki does, and on su15 (a keypad)
  clicks that change nothing keep being re-tested in every new state (338 re-tests, 320 into
  known states).
- What we take: rarity and size in the click ordering (the rule policy already uses this for
  touch targets, the explorer does not for clicks); dead signature per level, keyed by object
  type, applied before the graph frontier logic.

## 4. Blind Squirrel (Preview, 2nd) — github.com/wd13ca/ARC-AGI-3-Agents

- Method: a state graph of every state, action and successor; a rules-based "valid actions
  model" that treats contiguous same-colour shapes as the clickable set (4,102 actions
  reduced to shapes); an action-value ResNet-18 trained at the end of each level on graph
  distances to the win. Author's own note: "A glaring inefficiency in my code is that I am
  continuously regenerating predictions for the same state rather than caching them."
- Core assumption: deterministic games; the value of an action is learnable from the
  distance-to-win of states seen on the way to a level-up.
- Where it breaks on our traces: end-of-level training needs a win first; our zero-level
  games (cn04, re86, m0r0, wa30, sc25, sk48, ka59, g50t, ft09, sb26 in the final bench) give
  it nothing to train on. Its shape-as-button prior we already have.
- What we take: after a win, the path to the win is a labelled trajectory; we store it
  (`level_paths`) but do not use it yet to rank actions on the next level. A cheap version is
  the distance-to-win ordering of action classes, no network.

## 5. Rudakov, Shock, Cowley 2025, "Graph-Based Exploration for ARC-AGI-3" — arXiv 2512.24156 (Preview, 3rd)

- Method: segmentation into same-colour components; status-bar detection and masking; five
  priority tiers of click candidates by size, morphology and colour salience, status bars in
  the lowest tier; state hash of the masked frame; a level graph with per-action priority,
  outcome and distance to the nearest frontier; hierarchical selection: untested action at
  priority ≤ p here, else shortest path to a state with one, else p += 1. Median 30/52 levels
  on six games in an 8-hour, 96,000-step budget; 19 levels at 4,000 interactions.
- Their per-level numbers (Table 1) are the honest baseline for exhaustive exploration: ls20
  L1 124 steps, L2 3,200, L3 never; vc33 L1 9, L2 7, L3 36, L4 321, L6 69,000; ft09 L3 20,000.
- Core assumption: deterministic, fully observable, the mechanics will be found by covering
  untested state-action pairs; "some puzzle mechanics remained undetected" is their own
  failure note, and "performance degraded on games with extremely large state spaces (ft09
  levels 6+, ls20 levels 3+)".
- Where it breaks on our traces: the same place it broke for them. Our explorer is this
  algorithm with an action prior; it plateaued at 9 median levels and cannot reach ls20 L2
  (886 states at 1000 actions before the rule policy). Exhaustive coverage scales with the
  state space, and ls20's energy bar and rotator make it a product space.
- What we take: their status-bar tier ordering (try everything else before HUD-like segments)
  and the reset-marking bug they report (a reset-inducing action must be marked tested, or
  the frontier logic loops on it) as a test case for our graph.

## 6. Tsividis et al. 2021, EMPA — arXiv 2107.12544

- Method: theories are VGDL programs: object classes with dynamic types, interaction rules
  triggered only by contact between class pairs (stepBack, destroy, pickUp, teleport,
  changeResource, …), termination conditions of the form count(class) == 0. Bayesian
  inference over theories; the planner runs best-first search in an imagined simulator with
  intrinsic rewards for goals, subgoals (a count moving the right way) and goal gradients
  (distance to the relevant object), with Iterative Width novelty pruning and a
  metacontroller choosing long-term, short-term or stall planning.
- Exploration objective: "the most informative events are always agent-object and
  object-object interactions for classes of objects that have not previously been observed
  in contact", so the explorer "sets exploratory goals of generating interactions between
  every pair of classes whose interactions have not yet been observed", resets those goals
  when the agent's state (resources) changes, and treats reducing any class count to zero as
  an exploratory goal because that is the only state informative about termination rules.
  "Crucially, this sense of curiosity is not myopic; EMPA often generates long-ranging plans
  whose sole purpose is to generate informative interactions."
- Results: within an order of magnitude of human efficiency on 79 of 90 games; ablating
  theory-based exploration to epsilon-greedy "fail[s] dramatically"; ablating subgoals or
  goal gradients loses whole games. Humans and EMPA touch deadly objects a handful of times;
  DDQN thousands.
- Core assumptions: contact causes everything; classes behave uniformly; win is a count
  reaching zero; the avatar and the walls are given.
- Where it breaks on our traces: the contact assumption holds for the avatar games (ls20
  dials are touched) but not for click games and key dials (cn04's ACTION5 rotates something
  at a distance; re86 likewise). The count-to-zero termination misses ls20 (a resemblance
  condition) but matches what we see on sb26 and lp85-like collect games. Our exploration
  objective is "untested state-action pair nearest first", which is exactly what EMPA calls
  myopic: it re-tests a known mechanic in every new position (75% of actions before the rule
  policy) instead of "touch every class once".
- What we take: (1) the exploration target is class pairs not yet seen in contact, plus the
  avatar's resource state as a reset condition for those goals; (2) subgoal = a count moving
  in the goal's direction, goal gradient = distance to the relevant class, which is the
  missing piece of our ls20 L3 planning (design v2 section 6 is a paraphrase of this); (3)
  termination hypotheses as count(class)==0, next to our T1.

## 7. Dubey et al. 2018, "Investigating Human Priors for Playing Video Games" — arXiv 1802.10217

- Method: one platformer, 120 people per version, masks that remove one prior at a time.
  Numbers (time, deaths, unique states): original 1.8 min, 3.3, 3,011; masked semantics
  4.3 min, 11.1, 7,205; masked object identity (distractor blocks everywhere) 7.7 min, 20.2,
  12,232; masked affordances 4.7 min, 10.7, 7,031; masked similarity 7.6 min, 14.8, 11,715;
  changed ladder interaction 3.6 min, 6, 5,942; gravity reversed about 3 min; all object
  priors removed 20 min and 40 deaths, trajectories "almost completely random".
- Taxonomy, most to least important: the concept of an object (distinct entities are
  interesting and are sub-goals for exploration); visual similarity (things that look the
  same behave the same); semantics and affordances; how to interact with objects.
- Core assumption: priors are what let a human turn 3,000 states into a plan; without them a
  human is an RL agent.
- Where it breaks on our traces: we have the object prior (segmentation, salient targets) and
  the similarity prior in a weak form (rules keyed by exact colour+shape+size signature: a
  glyph drawn at 2x is a different signature, an icon split by segmentation is three
  signatures; both cost us on ls20 until fixed by hand). We have no affordance prior (a
  hollow frame is a display, a line of cells is a bar, a small rare thing is a button, a
  thing drawn in the bar's colour refills it: each was added after an autopsy, none is
  derived from a general rule). Their "distractor blocks" manipulation is what su15's keypad
  and sp80's board look like to us: many small distinct things, most of them irrelevant.
- What we take: the ranking. Object concept and similarity come first, so the class notion
  (colour plus scale-free shape, pieces merged) has to be the key of every rule, tool and
  prior; affordance rules stay as hypotheses tested by one touch, not as facts.

## 8. Kansky et al. 2017, Schema Networks — arXiv 1706.04317

- Method: entities with binary attributes; a schema is a conjunction over a local window of
  neighbouring entity-attributes plus an action, predicting one attribute next step; schemas
  are learned greedily by LP relaxation from few frames; self-transition variables keep
  attributes unless a schema changes them; planning is max-product inference backward from a
  clamped reward variable, with backtracking. Zero-shot transfer across Breakout variants
  after training on one; A3C fails on every variant.
- Core assumptions: local causes (a window around the entity), deterministic, entities and
  attributes given by a vision system.
- Where it breaks on our traces: local windows explain contact games; they do not explain a
  dial in one corner rotating a glyph in another (ls20, cn04), nor a click at (x, y) toggling a
  cell elsewhere (su15, r11l), which are our re-test sink. Backward planning from a goal is
  what our exploit mode does by hand for one template.
- What we take: the form of a rule: condition (class of the touched thing, avatar state)
  → effect on one attribute of one object, with an explicit "stays the same unless a rule
  fires" default. That is the `rules.store` we have, minus the explicit conditions and the
  default; and "explaining away": one effect, several possible causes, keep all until a
  touch discriminates.

## 9. Diuk, Cohen, Littman 2008, OO-MDP and DOORmax — ICML 2008

- Method: objects of classes with attributes; relations between objects (touchN/S/E/W, on)
  are Boolean terms; a condition is a conjunction of terms; an action's effect on an attribute
  (increment, set-to) fires under a condition, at most one effect type per action-attribute,
  effects invertible. DOORmax learns condition-effect pairs from single observations (the
  condition is the AND of what held when the effect was seen, generalised by "*" where
  observations disagree), keeps failure conditions (no change), and predicts "unknown" until
  certain (KWIK). Taxi 10x10: 821 steps vs 19,866 for factored R-max; Pitfall's first screen
  learned in one run of 494 actions.
- Core assumptions: deterministic; effects are functions of relations between class
  instances, so one wall teaches all walls; the designer provides the relations.
- Where it breaks on our traces: our passability is per colour, not per (avatar, object)
  relation, so on m0r0 and ls20 the same colour both passes and blocks (blocking is a property
  of the object or the track) and the planner mismatches (ls20 76 mismatches in the last
  run); our tools are keyed by exact signature, so a rule learned on a 3-cell icon does not
  fire on the same icon at another size. We also never keep failure conditions: a key that
  did nothing in state s is retried in s' because the graph is per state, not per condition.
- What we take: the learning rule verbatim for tools: condition = (class touched, avatar
  resource state) generalised by disagreement, effect = one property change, failure
  conditions kept; predict "unknown" rather than guessing, and let "unknown" be what
  exploration targets. This is the smallest formalism that makes a rule transfer from level 1
  to level 4.

## Cross-cutting

- Every strong source separates three things we still mix: what changes on its own (HUD,
  bars, animations), what changes because of our action (effects, keyed by class), and what
  is the goal (a termination condition or a resemblance to be closed). Our accounting shows
  the cost of mixing them: re-tests into known states are 320 of 444 actions on su15.
- Every strong source explores by class, not by state: touch each kind once (EMPA), stop
  clicking a kind that never responds (Reki), learn one wall for all walls (DOORmax). Our
  explorer explores by state, which is why it needs a goal to stop.
- Nobody plans energy. EMPA's `agentState` and `changeResource` are the closest; ls20 L3's
  consumable refills are ours to solve.
