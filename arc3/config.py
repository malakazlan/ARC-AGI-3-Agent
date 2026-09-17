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
    # Which action-selection policy the orchestrator uses. "random" = legal uniform random.
    policy: str = "random"
    # Optional local LLM layer. Off by default; must degrade to rules-only when missing.
    reasoner_enabled: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
