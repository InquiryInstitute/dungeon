"""
DWMB instance schema (POMDP specification).
Per deep-research-report Appendix A (dwmb-0.1).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Grid(BaseModel):
    height: int = Field(..., ge=1, le=64)
    width: int = Field(..., ge=1, le=64)
    tiles: str  # Grid representation; format: row-major, one char per cell (e.g. W=wall, .=floor)


class Visibility(BaseModel):
    radius: int = Field(default=2, ge=1, le=10)
    line_of_sight: bool = True


class Entities(BaseModel):
    agent_start: tuple[int, int]  # (row, col)
    goal: tuple[int, int]


class Door(BaseModel):
    pos: tuple[int, int]
    type: Literal["open", "closed", "locked"] = "closed"
    key_id: str | None = None


class SecretEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_pos: tuple[int, int] = Field(..., alias="from")
    to: tuple[int, int]
    discover: Literal["inspect"] = "inspect"


class Topology(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    doors: list[Door] = Field(default_factory=list)
    secret_edges: list[SecretEdge] = Field(default_factory=list, alias="secret_edges")


class Trap(BaseModel):
    pos: tuple[int, int]
    kind: str = "pit"  # pit, slick, etc.
    armed: bool = True
    disarm_switch: str | None = None


class SwitchEffect(BaseModel):
    trap_pos: tuple[int, int]
    armed: bool  # state after toggle (e.g. False = disarmed)


class Switch(BaseModel):
    id: str
    pos: tuple[int, int]
    effects: list[SwitchEffect]


class HiddenState(BaseModel):
    traps: list[Trap] = Field(default_factory=list)
    switches: list[Switch] = Field(default_factory=list)


class Reward(BaseModel):
    goal: float = 1.0
    step: float = -0.001
    trap: float = -0.2


class Terminal(BaseModel):
    goal: bool = True
    death_on_trap: bool = False


class Eval(BaseModel):
    hazards_for_PIR: list[tuple[int, int]] = Field(default_factory=list)


class DWMBInstance(BaseModel):
    """Full DWMB instance (POMDP)."""
    version: str = "dwmb-0.1"
    grid: Grid
    visibility: Visibility = Field(default_factory=Visibility)
    entities: Entities
    topology: Topology = Field(default_factory=Topology)
    hidden_state: HiddenState = Field(default_factory=HiddenState)
    reward: Reward = Field(default_factory=Reward)
    terminal: Terminal = Field(default_factory=Terminal)
    eval: Eval = Field(default_factory=Eval)

    def model_dump_json_tuples(self) -> dict[str, Any]:
        """Export for JSON: tuples as [r, c] lists, use aliases (e.g. 'from')."""
        d = self.model_dump(mode="json", by_alias=True)
        return self._tuples_to_lists(d)  # type: ignore[return-value]

    @staticmethod
    def _tuples_to_lists(obj: Any) -> Any:
        if isinstance(obj, tuple):
            return list(obj)
        if isinstance(obj, dict):
            return {k: DWMBInstance._tuples_to_lists(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [DWMBInstance._tuples_to_lists(x) for x in obj]
        return obj

    @classmethod
    def parse_json_compat(cls, data: dict[str, Any]) -> "DWMBInstance":
        """Parse from JSON where tuples may be lists."""
        def lists_to_tuples(obj: Any) -> Any:
            if isinstance(obj, list) and len(obj) == 2 and all(isinstance(x, int) for x in obj):
                return (obj[0], obj[1])
            if isinstance(obj, dict):
                return {k: lists_to_tuples(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [lists_to_tuples(x) for x in obj]
            return obj
        return cls.model_validate(lists_to_tuples(data))
