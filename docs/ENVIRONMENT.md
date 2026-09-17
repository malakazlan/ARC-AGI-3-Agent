# ARC-AGI-3 environment facts

Written 2026-09-17 during Phase 0. Every fact carries a source. `[docs:<page>]` means
https://docs.arcprize.org/<page>.md. `[src:<file>]` means code in the installed packages
(`arc-agi 0.9.9`, `arcengine 0.9.3`, framework `ARC-AGI-3-Agents` at commit cloned 2026-09-17).
`[measured]` means observed by running the local engine on public games on 2026-09-17
(scripts were ad hoc; the facts are re-checkable with `scripts/play_local.py` once Phase 1 lands).
Anything not verified is marked **UNKNOWN**.

## 1. Observation (what one response contains)

| Field | Type | Meaning | Source |
|---|---|---|---|
| `frame` | `list[list[list[int]]]` (framework) / `list[np.ndarray]` (raw) | One or more 2D grids. Last element is the current state. | `[src:arcengine ARCBaseGame.perform_action]`, `[src:agents/agent.py _convert_raw_frame_data]` |
| `state` | `GameState` enum | `NOT_PLAYED`, `NOT_FINISHED`, `WIN`, `GAME_OVER` | `[docs:game-schema]` |
| `levels_completed` | int | Number of levels beaten so far (engine field `_score`) | `[src:arcengine perform_action]` |
| `win_levels` | int | Total levels in the game. `WIN` when `levels_completed == win_levels` | `[src:arcengine next_level/win]` |
| `available_actions` | `list[int]` | Action ids (1..7) the game exposes. Raw ints, not enums | `[docs:actions]`, `[measured]` |
| `full_reset` | bool | True when the last RESET restarted the whole game, not just the level | `[src:arcengine full_reset]`, `[measured]` |
| `guid` | str or None | Session id. Locally a UUID generated once per `make()` | `[src:arc_agi local_wrapper]` |
| `action_input` | `ActionInput` | Echo of the action that produced this frame | `[src:arcengine FrameData]` |

Grid facts:

- Shape: every observed frame was `64 x 64`. Docs say **maximum** 64x64, and the engine has
  `camera.resize(level.grid_size)`, so smaller grids are possible. Treat shape as per-frame data,
  never assume 64. `[docs:game-schema]`, `[src:arcengine set_level]`, `[measured: 6 games]`
- Values: integers 0..15 (colors). Raw dtype is `int8`; the framework converts to Python lists.
  `[docs:game-schema]`, `[measured]`
- Coordinates: `(0,0)` top-left, `(x, y)` order for ACTION6; grid arrays index as `frame[y][x]`.
  `[docs:game-schema]`, `[docs:actions]`
- Frames per response: usually 1. Animations and level transitions return a stack, observed
  sizes 5, 13, 20, 22, 26, 27, 28. Engine hard cap is `MAX_FRAME_PER_ACTION = 1000`.
  `[measured: sc25, sp80, su15]`, `[src:arcengine]`
- On a level transition the response stack contains the end of the old level plus the first
  frame of the new level; `frame[-1]` is the new level's start state. `[measured: sp80]`
- An action sent while the game is in `GAME_OVER` or `WIN` returns `frame == []` (empty list),
  same state, and is **not** counted as an action locally. Agent code must tolerate empty
  frame lists. `[src:arcengine perform_action]`, `[measured: vc33]`
- Before the first RESET the framework seeds `frames[0]` with `FrameData(levels_completed=0)`:
  `state=NOT_PLAYED`, `frame=[]`, `available_actions=[]`. `[src:agents/agent.py __init__]`
- Locally, `arc.make()` performs a RESET immediately, so `env.observation_space` is already a
  real `NOT_FINISHED` frame before the agent sends anything. The framework passes that as
  `latest_frame` on the first `choose_action` call. That implicit reset is not counted as an
  action. `[src:arc_agi local_wrapper.__init__]`, `[measured]`
  **UNKNOWN** whether the Kaggle gateway (remote wrapper) does the same; remote `step()` refuses
  to run until a `reset()` has produced a guid, and the framework's `Swarm` calls `make()` only.
  Safe rule: if `state is NOT_PLAYED`, send RESET.

## 2. Action interface

| Action | id | Semantics | Source |
|---|---|---|---|
| `RESET` | 0 | Start or restart (see section 4) | `[docs:actions]` |
| `ACTION1..4` | 1..4 | Simple. Semantically mapped to up/down/left/right but game-defined | `[docs:actions]` |
| `ACTION5` | 5 | Simple. Interact/select/rotate etc., game-defined | `[docs:actions]` |
| `ACTION6` | 6 | Complex. Needs `x, y` in 0..63 | `[docs:actions]` |
| `ACTION7` | 7 | Simple. Always undo, for games that support it | `[docs:llms.txt entry for action 7]` |

- Framework usage: `action.set_data({"x": int, "y": int})` for ACTION6; `action.reasoning` may be a
  str or dict and is forwarded to the recording. `[src:agents/agent.py do_action_request]`
- `available_actions` is the per-game allowed subset. Observed sets on public games include
  `[6]`, `[6, 7]`, `[1,2,3,4,5]`, `[1,2,3,4,6]`, `[1,2,3,4,5,6]`. `[measured]`
- ACTION6 availability does **not** tell you which cells are active. `[docs:actions]`
- Sending an action that is not in `available_actions` locally: accepted, returns one frame,
  no change, state unchanged. **UNKNOWN** online (docs only specify a 400 for game-over).
  `[measured: su15]`, `[docs:actions]`
- ACTION6 with out-of-range coordinates (x=64, y=70) locally: accepted, no error.
  **UNKNOWN** whether it is counted and what the gateway does. `[measured: su15]`
- Online, any non-RESET action while `GAME_OVER` returns HTTP 400. `[docs:actions]`

## 3. Level completion, WIN, GAME_OVER

- Games call `next_level()` internally: `levels_completed += 1`; if it was the last level the
  state becomes `WIN`, otherwise the engine switches to the next level within the same response
  and the state stays `NOT_FINISHED`. `[src:arcengine next_level]`, `[measured: sp80]`
- So a level win is signaled only by `levels_completed` increasing, not by `state`.
- `GAME_OVER` is set by the game via `lose()`. The only useful action afterwards is RESET.
  `[src:arcengine lose]`, `[docs:actions]`
- Per-game level counts on the public set range 6..10 (`win_levels`). `[measured: 25 games]`

## 4. RESET semantics (the dangerous part)

Engine rule (`handle_reset`): `[src:arcengine handle_reset]`

- If no non-RESET action has been taken since the level started (`_action_count == 0`), or the
  state is `WIN`: **full reset** (all levels restored, `levels_completed = 0`, `full_reset=True`).
- Otherwise: **level reset** (current level restored, progress kept, `full_reset=False`).
- `_action_count` is zeroed by `set_level`, which runs on every level change.

Consequences, all measured locally:

- RESET after GAME_OVER mid-level keeps `levels_completed` and restarts that level. `[measured]`
- RESET immediately after a level-up (before any action on the new level) is a **full reset**
  and drops `levels_completed` to 0. `[measured: sp80]`
- Two consecutive RESETs are always a full game reset. `[docs:start-or-reset]`, `[measured]`
- `guid` stays the same across resets locally. `[measured]`
- Competition mode: "Only Level Resets are permitted, Game Resets are not allowed and become
  Level Resets" (engine env var `ONLY_RESET_LEVELS=true`). The Kaggle competition is forced
  into this mode. `[docs:toolkit/competition_mode]`, `[src:arcengine handle_reset]`
  **UNKNOWN** whether the Kaggle gateway sets `ONLY_RESET_LEVELS`; the agent must not rely on it.
  Rule for our agent: never send RESET unless `state in {NOT_PLAYED, GAME_OVER}`.

## 5. Action counting and scoring

- Score per level: `(human_baseline_actions / agent_actions)^2 * 100`, capped at 115.
  Human baseline is the upper-median human by fewest actions. `[docs:methodology]`,
  `[src:arc_agi scorecard.add_level]`
- Per game: weighted mean of level scores with weight = 1-indexed level number; capped so an
  incomplete game cannot exceed the share of weight from completed levels. Total = mean over
  games. `[docs:methodology]`, `[src:arc_agi scorecard.to_score]`
- The public games expose `baseline_actions` per level in `EnvironmentInfo`, so a local RHAE
  estimate is possible on public games. `[measured: get_environments()]`
- What counts as an action locally: every non-RESET action sent while `NOT_FINISHED`.
  RESET is **not** counted (`_set_action` skips the increment; scorecard showed 2 actions after
  3 RESETs + 2 ACTION1). `[src:arcengine _set_action]`, `[measured: sp80]`
- Actions sent during `GAME_OVER` are not counted locally. `[measured: vc33]`
- Level actions accumulate per level index across resets of that level (`level_actions[0]` kept
  growing through repeated GAME_OVER + RESET). `[measured: scorecard output]`
- **UNKNOWN**: whether the online gateway counts RESET, invalid, or game-over actions the same
  way. Docs say "internal operations ... are not counted"; they do not mention RESET.
  Decision: keep the strict assumption (every RESET and every sent action may count).
  `[owner, 2026-09-17]`
- In competition mode "scoring is against all available environments, even if you choose not
  to interact with them", `make()` may be called once per environment, and only one scorecard.
  `[docs:toolkit/competition_mode]`

## 6. Runtime and orchestration on Kaggle

- Kaggle runs the framework `main.py --agent myagent`; it lists games from the gateway
  (`http://gateway:8001/api/games`) and starts one agent **thread per game concurrently**
  (`Swarm.main`). All games run in parallel in one process, so per-game wall time budgets
  must be set against the total, and CPU is shared. `[src:reference/stochastic-goose notebook]`,
  `[src:vendor/ARC-AGI-3-Agents/agents/swarm.py]`
- The agent loop stops when `is_done()` is True or `action_counter > MAX_ACTIONS`
  (`while not is_done and action_counter <= MAX_ACTIONS`, so `MAX_ACTIONS=80` yields 81 calls).
  `[src:agents/agent.py main]`
- The official sample (`Stochastic Goose`) stops itself at `8 h - 5 min` wall time and sets
  `MAX_ACTIONS = inf`. That implies an 8 h notebook limit but is not an official statement.
  `[src:reference/stochastic-goose]`
- Runtime limit is not in public docs; community reports kills around 6 to 9 h. **Working
  assumption: 6 h global budget with margin** until confirmed on the Kaggle page (log in, Overview,
  Code Requirements). `[owner, 2026-09-17]`
- Hidden game count unknown; one team measured about 110. **Design for 100+ games.**
  `[owner, 2026-09-17]`
- The technical report lists 25 public, 55 semi-private (API-tested) and 55 fully private
  (competition) environments; the public set is "intentionally easier" and the private set is
  "intentionally out-of-distribution relative to the public set". `[ARC_AGI_3_Technical_Report
  Table 1, section 3.6]`
- Official leaderboard runs terminate a level after 5x the human-median actions for that level.
  **UNKNOWN** whether the Kaggle gateway applies the same cap; assume it might, so a level that
  needs more than 5x human actions may never count. `[Technical Report section 4.3]`
- "The environment's state does not change asynchronously from the agent's actions"; frame
  sequences are transition animations only. `[Technical Report section 2.3]`
- Environments are validated so that "a random policy should not successfully solve a level
  more often than 1 in 10,000 times" (non-tutorial levels); the first level is a tutorial that
  random agents can occasionally clear. `[Technical Report sections 3.4, 3.5]`
- Kaggle limits: 1 submission per day, 2 final submissions selectable, team max 8, entry and
  merger deadline 2026-10-26. `[owner, 2026-09-17]`
- Wheels are installed offline from
  `/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels` (`arc-agi`,
  `python-dotenv`). Any extra dependency must be in that wheel dir or attached as a dataset.
  `[src:scripts/build_notebook.py]`, `[src:reference/stochastic-goose cell 0]`
- Kaggle accelerator default in the starter is T4 x2; `enable_internet=false`.
  `[src:notebooks/kernel-metadata.json]`, `[docs:arc-prize-2026]`
- The sample notebook writes the agent to `agents/templates/my_agent.py` inside the copied
  framework, so imports must resolve from there. Our `arc3/` package must be shipped into the
  notebook explicitly (Phase 1/2 task). `[src:scripts/build_notebook.py]`

## 7. Determinism and local speed

- Local engine: same `make(game, seed)` and same action sequence gave identical frame
  sequences. Seeds 0 and 1 also gave identical sequences on `sp80`, so game seeds may be
  unused by many games. `[measured]`
- Speed: 20 random actions in 0.08 s in-process; docs quote about 2000 FPS. `[measured]`,
  `[docs:local-vs-online]`
- `OperationMode.OFFLINE` lists only games already cached in `environment_files/`; `NORMAL`
  fetches the list from the API and downloads sources on first use. Online rate limit is
  600 requests/min; local has none. `[src:arc_agi base]`, `[docs:rate_limits]`, `[measured]`
- Public roster on 2026-09-17: 25 games (anonymous key). Registered keys may see more.
  `[measured]`, `[docs:local-vs-online]`

## 8. Surprises worth remembering

1. RESET right after a level-up wipes all progress locally. Guard it.
2. Level wins do not change `state`; watch `levels_completed`.
3. Responses can carry up to 28 frames; use `frame[-1]` for state, the stack for animation cues.
4. Game-over responses to non-RESET actions have an empty `frame` list.
5. The framework runs all games in parallel threads; a global deadline must be shared.
6. Unavailable actions are silent no-ops locally, so they waste nothing locally but may be
   400s online. Always filter by `available_actions`.
