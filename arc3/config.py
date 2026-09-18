"""Single configuration dataclass. Every knob lives here and every knob has a default."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Arc3Config:
    seed: int = 0
    # Wall-clock budget shared by every game in the process. 6 h assumed limit minus margin.
    global_budget_s: float = 5.5 * 3600
    # Hard cap on choices (actions + resets) per game so one game cannot eat the budget.
    max_actions_per_game: int = 2000
    # Action-selection policy: "graph" (explorer, control), "rules" (v2: discovery + rule store
    # on top of the explorer) or "random" (legal uniform).
    policy: str = "rules"
    # Graph explorer: node cap per level (memory) and click candidates per state (branching).
    max_nodes_per_level: int = 5000
    max_click_candidates: int = 64
    # Learn energy/countdown bars across attempts and drop them from the state key.
    countdown_mask: bool = True
    # Deaths at a fixed per-attempt step count are budget expiries, not lethal actions.
    budget_aware: bool = True
    # Learn per action class (key id, or click target colour+size) what does nothing or kills;
    # explore those classes last.
    action_prior: bool = True
    # Learn the avatar, key vectors and per-colour passability; predict moves instead of
    # re-testing them and plan paths to unknown terrain. Disabled per level after 3 mispredictions.
    planner: bool = True
    planner_max_mismatches: int = 3
    # Learn click effects by object signature and non-move key effects by avatar appearance;
    # skip actions whose effect is a known no-op or leads to a state already explored.
    effects: bool = True
    # Ablation switches for the two discovery changes of 2026-09-18.
    dial_cap: bool = False       # skip confirmed key dials on avatar games (costs su15/tu93 with breadth-first)
    breadth_first: bool = True   # try every move key once before repeating any (elects the avatar, shows the bar)
    # Click model switches (2026-09-18 click autopsies, ft09 and lp85).
    click_mask: bool = True          # the step bar is not part of what a click did
    click_split: bool = True         # a contradicted signature predicts per instance only
    verify_first: bool = True        # a signature's rule is trusted only after one confirmed prediction
    verify_predictions: bool = True  # exhausted frontier: execute a predicted edge before any random click
    diverse_clicks: bool = True      # the click cap keeps one instance of every signature first
    # Optional local LLM layer. Off by default; must degrade to rules-only when missing.
    reasoner_enabled: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
