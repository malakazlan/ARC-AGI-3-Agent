# The public games: what is known, what we measured, what a new game will look like (2026-09-18)

Sources: the ARC-AGI-3 technical report (arXiv 2603.24621), the human dataset post
(arcprize.org/blog/arc-agi-3-human-dataset), Rudakov et al. (arXiv 2512.24156), the executable
world-model paper (arXiv 2605.05138), Tycho (arXiv 2607.28287), the arc-code write-up
(github.com/jerber/arc-code), Symbolica's post, the owner's own play (`docs/HUMAN_PLAY.md`),
and our census of the offline cache (`scripts/game_census.py`, `docs/GAME_CENSUS.md`).
Game names are never published by the foundation; the informal names below come from
third-party write-ups.

## 1. What the foundation says every game is built from

From the technical report, section 3.4, these are the design constraints, i.e. the only
things an agent may rely on for a game it has never seen:

- Core Knowledge priors only: objectness (coherent, persistent entities that move, collide,
  are occluded), basic geometry and topology (symmetry, rotation, inside/outside,
  connectedness, holes), basic physics (gravity, momentum, bouncing), agentness (some
  objects act with intent). "Environments never use numbers, letters, recognizable
  real-world clip-art (like flowers or keys), or cultural conventions."
- Novelty: every environment must be distinct from existing video games and from every other
  environment (a shared program solving two games must not be much shorter than two programs).
- Tutorial first level, then "difficulty through composition": later levels compose the
  mechanics of earlier ones; single-mechanic games are an anti-pattern; at least six levels.
- Each frame carries "a status bar displaying the number of steps remaining before an
  automatic level restart. When the step counter reaches zero, the current level resets to its
  initial state" (Rudakov et al., confirmed by our ls20 frames: the flash-and-restart with no
  GAME_OVER). The report's Figure 3 calls this "the three-life mechanic of the level".
- The private set (55 + 55 games) "cover[s] a broader and more diverse set of mechanics with
  limited overlap with the mechanics found in the public environments"; the public set "does
  not comprehensively represent the mechanics found in the private set."
- Random play must not solve a non-tutorial level more than 1 in 10,000 times; ls20 level 1 is
  exactly 1 in 355 for a random policy.

Consequence for us: mechanisms must be keyed on things derivable from frames (objects,
classes, motion, counts, resemblance, a draining line), never on names, colours or layouts.

## 2. Per-game knowledge

Columns: split; levels; human baseline per level (upper-median first-run, from
`eval/games.json`); action set; what third parties describe; what coding agents scored
(RHAE of the executable-world-model paper, "EWM", one or two runs; Symbolica's day-one where
given); our final dev bench (median levels of 3 seeds, 1000 actions).

| game | split | lv | human per level | actions | description (third parties) | EWM RHAE | ours |
|---|---|---|---|---|---|---|---|
| ar25 | holdout | 8 | 32, 50, 75, 37, 89, 159, 233, 73 | keys 1-5, click, undo | avatar moves 3 cells per key (census); nothing published | 100 | not run |
| bp35 | holdout | 9 | 21, 48, 44, 38, 33, 87, 86, 131, 163 | keys 3-4, click, undo | 191 objects on the first frame, animation on every step (census); agents "abandoned level 8 declaring undiscovered mechanics" (arc-code) | 0.6 | not run |
| cd82 | holdout | 6 | 55, 8, 41, 21, 23, 23 | keys 1-5, click | a brush stamping its colour into a canvas region, a HUD counter (Tycho); humans who pass level 2 mostly finish (human dataset) | 86.5 | not run |
| cn04 | dev | 6 | 29, 54, 85, 300, 208, 113 | keys 1-5, click | avatar 3 cells per key, ACTION5 rotates something at a distance (our traces); Symbolica 97.6% | 31 (62 / 0.01, two runs) | 0 (flaky 1) |
| dc22 | holdout | 6 | 59, 102, 67, 98, 324, 578 | keys 1-4, click | avatar 2 cells per key, 35 objects (census) | 29 | not run |
| ft09 | dev | 6 | 43, 12, 23, 28, 65, 37 | click | "Elementary Logic" (docs); every click animates (51 of 60 steps); a click-constraint solver finishes 6/6 in 75 actions (search result) | 52 | 0 |
| g50t | dev | 7 | 78, 175, 179, 230, 96, 54, 67 | keys 1-5 | avatar 6 cells per key, animation on most steps (census) | 28 | 0 (one seed 1) |
| ka59 | dev | 7 | 28, 109, 51, 51, 33, 132, 326 | keys 1-4, click | Sokoban: steer a box, push objects into pens (arc-code) | 0.01 | 0 |
| lf52 | holdout | 10 | 32, 81, 60, 71, 205, 148, 244, 109, 164, 225 | keys 1-4, click, undo | peg solitaire; level 6+ scrolls a world wider than the screen; red pieces are mobile walls, red-green leapfrog (arc-code) | 14.7 | not run |
| lp85 | dev | 8 | 17, 38, 31, 16, 41, 60, 26, 159 | click | 37 objects, our explorer wins level 1 in about 15 actions | 100 | 1 |
| ls20 | dev | 7 | 22, 123, 73, 84, 96, 192, 186 | keys 1-4 | "Locksmith": avatar (a key) 5 cells per step, energy bar drains per step, rotator dial turns the key, colour dial recolours it, refills, conveyors, exit box opens when key matches (owner's play, arc-code, Goertzel); L1 random win 1/355 | 27 | 2 |
| m0r0 | dev | 6 | 30, 111, 203, 26, 500, 237 | keys 1-5, click | two characters moving as mirror images, both must reach the target dot (arc-code); only 4 objects on frame 1 | 1.1 | 0 |
| r11l | dev | 6 | 22, 33, 51, 26, 52, 49 | click | 10 of 10 humans solve it (human dataset); animation on most clicks | 14.3 | 1 |
| re86 | dev | 8 | 26, 42, 86, 108, 189, 139, 424, 241 | keys 1-5 | steer shapes 3 cells per key to cover coloured boxes, ACTION5 switches the active shape, purple bar counts moves, four boxes of one colour form a plus (arc-code, report Figure 4) | 33 | 0 |
| s5i5 | dev | 8 | 20, 89, 106, 54, 162, 38, 86, 83 | click | 28 objects, no animation (census) | 8.2 | 1 (0/1/1) |
| sb26 | dev | 8 | 18, 28, 18, 19, 31, 23, 58, 18 | key 5, click, undo | animation on every step, no bar found (census) | 92.7 | 0 |
| sc25 | dev | 6 | 36, 6, 32, 83, 143, 50 | keys 1-4, click | a 79-line solver sufficed for a coding agent (arc-code); a 128-cell mask (two bars?) | 0 | 0 (one seed 2) |
| sk48 | dev | 8 | 61, 177, 101, 103, 230, 181, 125, 92 | keys 1-4, click, undo | "correct mechanics, unresolved objective": agents model the transitions and never find the goal (Tycho) | 0.75 | 0 |
| sp80 | dev | 6 | 39, 58, 25, 148, 96, 152 | keys 1-5, click | "roughly simulates fluid dynamics" (foundation); 2 of 12 humans solved it; avatar 4 cells per key; deaths at fixed cadence | 4.8 | 1 |
| su15 | dev | 9 | 22, 42, 26, 115, 36, 31, 8, 40, 41 | click, undo | a keypad; clicks animate; 75% of our actions are re-tests into known states | 3.6 | 1 |
| tn36 | holdout | 7 | 32, 72, 26, 40, 30, 55, 62 | click | 48 objects, our explorer wins level 1 inside 60 actions (census) | 0.01 | not run |
| tr87 | holdout | 6 | 54, 58, 40, 45, 71, 146 | keys 1-4 | avatar 7 cells per key, 37 hollow frames on frame 1 (census); the foundation's Duke harness scores 97% on a variant, Opus 4.6 alone 0% | 100 | not run |
| tu93 | dev | 9 | 19, 16, 34, 42, 123, 80, 14, 23, 111 | keys 1-4 | a 21x21 block maze, a magenta bar of a 50-move budget shown as a quantised 64-cell line, a pursuer from later levels (arc-code, Tycho) | 78 | 2 |
| vc33 | dev | 7 | 7, 18, 44, 61, 131, 34, 152 | click | "Orchestration" (docs); level 6 needs 10x the actions of level 1 (report) | 8.6 | 2 |
| wa30 | dev | 9 | 71, 119, 183, 98, 368, 68, 79, 442, 415 | keys 1-5 | avatar found only at action 21, two key vectors (census); nothing published | 0 | 0 |

Two things stand out. The coding agents (EWM, Tycho, arc-code, Schema) reach 85–100% on
this set by writing a per-game program at test time; their failure games (bp35, ka59, m0r0,
sc25, sk48, sp80, su15, tn36, wa30, vc33 for EWM) are the same ones that are hard for us. And
the games where a human's first run is short (r11l, sb26, tu93, vc33 L1, lp85) are the ones
our explorer already wins; the games with long human baselines (cn04 L4 300, m0r0 L5 500,
wa30 L8 442, re86 L7 424) are where the score lives, because later levels weigh more.

## 3. What the census says an agent can know about any game, without a name

Measured on all 25 games from the first frame and 60 probe actions of our default agent:

- Action set: 8 games are click-only, 6 are keys-only, 11 mix keys and clicks. This is given
  by the engine before the first action.
- Avatar and step size: on 13 of the 16 games with move keys the avatar is elected within 2
  to 9 actions, with the step size (2 to 7 cells) read from the displacement. Late or partial
  on bp35 (19), wa30 (21, two vectors), sc25 and sk48 (two vectors), tr87 (two vectors),
  m0r0 (two vectors, two mirrored characters).
- A draining line: a 59 to 138-cell bar is found within 60 actions on 21 of 25 games (the
  engine's step-budget bar; none on lf52, m0r0, sb26). This is the resource that resets the
  level silently, so the energy model applies almost everywhere, not only on ls20.
- Animation: on ft09, r11l, su15, bp35, sb26, lf52, tu93, g50t, sk48 most actions return
  several frames; a click game whose clicks animate is a different family from one whose
  clicks toggle in place (s5i5, lp85, vc33).
- Object counts on frame 1 range from 4 (m0r0) to 191 (bp35); small rare objects (the
  candidates a human touches first) from 0 to 181.

These five facts, all computed at run time, are what our mechanisms key on. A hidden game
will present the same kinds of facts; the agent's job is the same: elect the avatar or
the click set, find the bar, touch each class of object once, read what changed, form the
goal from the change, plan.

## 4. How a hidden game gets handled, mechanism by mechanism

| the game shows | the agent does | status |
|---|---|---|
| move keys available | press each once, elect the object whose displacement follows the key, read the step size | works on 13/16 games within 9 actions |
| clicks available | click small rare objects first, stop on a class that never responds | ordering by rarity exists for touches, not yet for clicks; dead-signature rule not yet built |
| a line of cells switching off in order under different keys | mask it from the state, read remaining energy and the rate, budget walks, look for refills drawn in its colour | works on 21/25 games for the mask; budgeting verified on ls20 |
| a flash and the level's start frame | count a death, end the attempt, blame nothing | built |
| a touched object changes a property of another region | record a tool: this class changes that property | built (dials by property) |
| a changed region resembles a static one | goal: make them equal; use dials by mismatched property; walk into the static one | built (T1); ls20 L1-L2 |
| a class count drops when touched | goal: drive the count to zero, then reach the remaining rare object | not built (T2, T3, T5); this is the next template by the win-probe test |
| two objects move together / mirrored | treat the pair as one avatar with a joint state | not built (m0r0) |
| a region wider than the screen scrolls | track the offset, stitch a map | not built (lf52 level 6+) |
| a pursuer moves toward the avatar | plan against its motion | not built (tu93 later levels) |

The general algorithm is the loop at the top of design v2: explore by class until a goal
hypothesis exists, then plan under the energy budget, verify by the level-up, carry the rule
store to the next level, and demote the hypothesis on contradiction. What the public set
teaches is which perceptual cues are reliable (section 3) and which goal templates recur
(resemblance, count-to-zero, reach); what it cannot teach is the private set's new mechanics,
which is why every rule is a hypothesis tested by one touch, never a fact.


## 5. Coverage table from the VISTA notes (2026-09-18, second pass)

Source: the final `GUIDE.md` of the VISTA agent (Claude Opus 5) on every public game, mined
from vista-research.github.io replay data and stored verbatim in `docs/vista_guides/`
(`summary.json` has per-level agent actions and the action at which the agent first wrote a
goal into its notes). VISTA's per-level actions are the tightest known non-human baseline
(7,542 actions for 183 levels vs 17,135 human). Goal templates are design v2 section 5: T1
match (make A equal B), T2 reach, T3 collect then reach, T4 make uniform, T5 fill or clear
(count to target), T6 unlock sequence. Tool types are ours: move_key, dial (property cycles on
touch or key), transporter, refill, lethal, click-select (choose the active object), place
(put the selected thing on a slot), push/carry, commit key, plus the new ones below.

| game | goal as VISTA states it | template | tools the agent used | goal first written at action | our status |
|---|---|---|---|---|---|
| ar25 | pieces of 24px blocks moved in 24px steps (assembly; guide lacks a one-line goal) | not classified | move_key (3 cells), click-select, undo | 4 | no template |
| bp35 | bubble rises on its own; reach the pink cross | T2 reach + physics (drift) | move_key (L/R only), click, undo | 17 | T2 not built; autonomous drift not modelled |
| cd82 | a press stamps rows of the selected colour into the canvas; make the canvas match | T1 match (paint) | ring cursor (8 positions), fire press (key 5 / click) | 7 | T1 built for framed displays only; press tool not built |
| cn04 | select a piece, move/rotate it; win when every prong is paired in a joint | T5 count (unpaired prongs) to zero | click-select, move_key, rotate key (5), grow button | 16 | T5 not built; rotate-by-key = dial partly; select not built |
| dc22 | walk a dot to the yellow goal; right-panel buttons toggle blocks (terrain) | T2 reach + T6 unlock | move_key (2 cells), click buttons that change terrain | 14 | T2/T6 not built |
| ft09 | dials are 3x3 mini-maps of neighbours; colour every tile to its target | T1 match per tile (a target pattern) | click cycles a tile's colour (dial) | 1 | dial built for touch; click-dial and derived targets not built |
| g50t | plug the cable/player into the goal socket (blue ring open on one side) | T2 reach with orientation | move_key (6 cells), rotate (key 5?) | 12 | T2 not built |
| ka59 | every piece rests on its matching goal outline; pieces slide/launch | T1 match positions (T5 unplaced to zero) | click-select, move_key, launch | 14 | not built; push/launch not modelled |
| lf52 | peg solitaire; exactly one green peg remains; level 6+ scrolls | T5 clear to one | click jumps; scrolling viewport | 11 | T5 not built; scrolling not modelled |
| lp85 | (guide is level-local; click puzzle on a block grid) | not classified | click | 5 | no template (our explorer wins L1 by exploration) |
| ls20 | carried glyph must match the goal box glyph, then enter it; energy, rotator, colour dial, refills | T1 match + T2 enter | move_key (5), dial x2, refill, conveyor, energy | 3 | built (L1, L2 won); L3+ needs the energy subgoal plan |
| m0r0 | both mirrored agents in the same cell; red cells lethal; keys hold doors open; blocks pushable | T2 reach (joint state) + T6 keys/doors | move_key (both agents), click-select block + push, lethal, key/door | 2 | not built: mirrored pair, keys/doors |
| r11l | put each blob's centre on its matching ring centre | T1 match positions | click to move blobs | 4 | not built (we win L1 by exploration) |
| re86 | shapes are line sets; cover the four same-colour dots (a plus); ACTION5 switches the active shape | T1 match (shape onto dots) | select by key 5, move_key (3), shapes deform on a ring | none in notes | select-by-key not built; T1 needs "cover targets" variant |
| s5i5 | "+" buttons rotate segments (children rotate with them); assemble | not classified (assembly by rotation) | click rotates a segment (dial) | 143 | no template |
| sb26 | fill slots so the flattened nested-box sequence equals the legend; ACTION5 submits | T1 match sequence | click-select piece, place on slot, commit key 5 | none in notes | select/place/commit not built; T1 sequence variant not built |
| sc25 | enter the blue C bracket sized like the player; the player can change size | T2 reach + size dial | move_key, size dial | 10 | T2 not built |
| sk48 | chain-arm collector; the legend shows the required arm contents in order | T1 match sequence (collect in order) | move_key, collect | 16 | no template |
| sp80 | every stream must end in a castle notch, nothing may reach the grey wall | routing (no template) | move_key (4), commit key 5 | 8 | no template (we win L1 by exploration) |
| su15 | deliver the HUD-listed objects to the blue delivery slots | T5 fill all slots | click-select, place, undo | 5 | not built (we win L1 by exploration) |
| tn36 | get the mover onto the frame's interior cell in exactly the budgeted moves | T2 reach with exact step budget | click moves | 5 | T2 not built; exact-count constraint not modelled |
| tr87 | cycle glyphs at the cursor until the target word matches the key mapping | T1 match (symbolic mapping) | cursor keys, cycle keys (dial) | none in notes | no template (mapping inference) |
| tu93 | reach the green node, avoid guards (static and hunters) | T2 reach + lethal movers | move_key (6), budget bar | 1 | T2 partly (we reach by exploration), pursuers not modelled |
| vc33 | buttons move material between chambers; bring the player marker to the matching marker | T2 reach through T6 (levels as terrain) | click buttons (transfer N units) | 9 | no template (we win L1-L2 by exploration) |
| wa30 | deposit every blue box inside the lock | T5 count (boxes outside lock) to zero | move_key, carry/deposit | 40 | T5 not built; carry not modelled |

Counts: T1 match in some variant 9 games, T2 reach 9, T5 count/fill 5, T6 as a sub-mechanic
3, no template 6 (ar25, lp85, s5i5, sp80, tr87, and re86's cover-the-dots which is T1 only
with a "cover" variant). Built today: T1 for framed displays (1 game as stated, ls20), T2 by
exploration only. The two templates that cover the most games with the least mechanism are
T2 reach (a rare static object or a marked cell) and T5 count-to-target, which is what the
win probe said from our own traces. Tools absent from our store that recur: click-select of
an active object (cn04, ka59, m0r0, sb26, su15, re86 by key), place-on-slot (sb26, su15),
push/carry (ka59, m0r0, wa30), commit key (sb26, sp80), autonomous movers (bp35, tu93).

How VISTA found the goal in the first ten actions (from the replay reasoning):
- m0r0: action 1, one key press: "Both cyan blocks moved up one cell together, they're two
  co-controlled agents in a maze"; by action 2 the note reads "Hypothesis: goal = make the
  two agents occupy the same cell"; action 3 discovers the mirrored horizontal control from a
  blocked move. Goal from co-movement of two identical rare objects plus the "same cell"
  prior, before any win.
- re86: three actions (a move, ACTION5, a move): "ACTION5 toggles which cross is selected
  (white center pixel = selected)"; "Hypothesis: place each cross so all 4 same-color dots lie
  on its arms", with the four dots' coordinates and the target cross positions computed and
  a full plan written at action 2. Goal from colour correspondence between the movable
  crosses and static dot groups.
- cn04: four actions (a move, three ACTION5 presses, a click) before a plan; the goal
  ("every prong paired in a joint") came after seeing prongs meet and render grey.
  Goal from an observed effect (joint colour) plus counting what remains unpaired.
In all three the goal is stated after 1 to 4 actions and before any level is won; the
evidence is object correspondence (same colour, same count, same shape) between what moves
and what stays. That is resemblance in our terms, applied to positions and counts, not only
to framed displays.
