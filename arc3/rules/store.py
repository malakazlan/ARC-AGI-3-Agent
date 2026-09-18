"""Per-game rule store (design v2, section 2). Persists across levels within a game."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

GOAL_FLOOR = 0.35


@dataclass
class Tool:
    kind: str  # move_key | dial | rotator | transporter | refill | lethal | no_op | unknown
    params: dict = field(default_factory=dict)


@dataclass
class Goal:
    template: str  # match_display | reach | collect_then_reach | ...
    params: dict
    confidence: float


@dataclass
class RuleStore:
    tools: dict[tuple, Tool] = field(default_factory=dict)
    displays: list[dict] = field(default_factory=list)
    goal: Goal | None = None
    deaths: list[tuple] = field(default_factory=list)
    level_paths: dict[int, list] = field(default_factory=dict)
    level: int = 0

    # -- tools -------------------------------------------------------------------------------

    def set_tool(self, signature: tuple, kind: str, **params: Any) -> None:
        self.tools[tuple(signature)] = Tool(kind, dict(params))

    def tool(self, signature: tuple) -> Tool | None:
        return self.tools.get(tuple(signature))

    # -- goal --------------------------------------------------------------------------------

    def propose_goal(self, goal: Goal) -> None:
        if self.goal is None or goal.confidence >= self.goal.confidence:
            self.goal = goal

    def demote_goal(self, by: float) -> None:
        if self.goal is None:
            return
        self.goal.confidence = round(self.goal.confidence - by, 6)
        if self.goal.confidence < GOAL_FLOOR:
            self.goal = None

    # -- deaths and paths --------------------------------------------------------------------

    def record_death(self, signature: tuple) -> None:
        self.deaths.append(tuple(signature))
        self.set_tool(signature, "lethal")

    def lethal(self, signature: tuple) -> bool:
        tool = self.tool(signature)
        return tool is not None and tool.kind == "lethal"

    def record_level_path(self, level: int, path: list) -> None:
        self.level_paths[level] = list(path)

    def new_level(self, level: int) -> None:
        """A new level keeps everything learned; only the level index moves."""
        self.level = level

    # -- diagnostics -------------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "tools": {str(k): {"kind": t.kind, "params": {a: str(b) for a, b in t.params.items()}} for k, t in self.tools.items()},
            "displays": [dict(d) for d in self.displays],
            "goal": None if self.goal is None else {"template": self.goal.template,
                                                    "params": {k: str(v) for k, v in self.goal.params.items()},
                                                    "confidence": self.goal.confidence},
            "deaths": [str(d) for d in self.deaths],
            "level_paths": {str(k): len(v) for k, v in self.level_paths.items()},
        }
