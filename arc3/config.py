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
    # Action-selection policy: "graph" (Baseline 1 explorer) or "random" (legal uniform).
    policy: str = "graph"
    # Graph explorer: node cap per level (memory) and click candidates per state (branching).
    max_nodes_per_level: int = 5000
    max_click_candidates: int = 64
    # Optional local LLM layer. Off by default; must degrade to rules-only when missing.
    reasoner_enabled: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
