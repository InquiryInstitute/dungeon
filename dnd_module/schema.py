"""
Schema for a Tomb-of-Horrors-style D&D module.
Output is a keyed module with map, areas, traps, and clues for tabletop play.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DoorType(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"
    SECRET = "secret"
    FALSE = "false"
    ONE_WAY = "one_way"
    MAGICAL = "magical"


class TrapKind(str, Enum):
    PIT = "pit"
    SLIDING_BLOCK = "sliding_block"
    CEILING_COLLAPSE = "ceiling_collapse"
    SPEAR = "spear"
    POISON_NEEDLE = "poison_needle"
    GAS = "gas"
    CRUSHING = "crushing"
    TELEPORT = "teleport"
    CURSE = "curse"
    SPHERE_ANNIHILATION = "sphere_annihilation"
    SPIKE_VOLLEY = "spike_volley"
    TILTING_FLOOR = "tilting_floor"
    MAGIC_MOUTH = "magic_mouth"


class RoomType(str, Enum):
    ENTRANCE = "entrance"
    CORRIDOR = "corridor"
    HALL = "hall"
    CHAMBER = "chamber"
    PRISON = "prison"
    CHAPEL = "chapel"
    THRONE_ROOM = "throne_room"
    CRYPT = "crypt"
    TREASURE_ROOM = "treasure_room"
    TRAP_ROOM = "trap_room"
    PUZZLE_ROOM = "puzzle_room"
    DEAD_END = "dead_end"


class Position(BaseModel):
    row: int = Field(..., ge=0)
    col: int = Field(..., ge=0)


class Door(BaseModel):
    position: Position
    door_type: DoorType = DoorType.CLOSED
    key_id: str | None = None
    open_method: str | None = None  # e.g. "pull down", "press studs 1 and 7"
    leads_to_area: str | None = None  # area id


class Trap(BaseModel):
    position: Position
    kind: TrapKind = TrapKind.PIT
    armed: bool = True
    disarm_switch_id: str | None = None
    damage: str | None = None  # e.g. "2-16 (2d8)"
    save: str | None = None   # e.g. "vs magic"
    description: str = ""


class Switch(BaseModel):
    id: str
    position: Position
    effects: list[dict[str, Any]] = Field(default_factory=list)  # e.g. [{"trap_id": "t1", "armed": False}]
    description: str = ""


class Clue(BaseModel):
    area_id: str | None = None  # where clue is found
    format: str = "riddle"  # riddle, inscription, runes, map_fragment
    text: str = ""
    hints_at: list[str] = Field(default_factory=list)  # area ids or trap/secret this helps with


class KeyedArea(BaseModel):
    id: str
    position: Position
    room_type: RoomType = RoomType.CHAMBER
    name: str = ""
    description: str = ""
    doors: list[Door] = Field(default_factory=list)
    traps: list[Trap] = Field(default_factory=list)
    switches: list[Switch] = Field(default_factory=list)
    clues: list[Clue] = Field(default_factory=list)
    connections: list[str] = Field(default_factory=list)  # adjacent area ids
    illustration_ref: str | None = None


class MapCell(BaseModel):
    row: int = Field(..., ge=0)
    col: int = Field(..., ge=0)
    cell_type: str = "."  # . = floor, # = wall, D = door, S = secret, E = entrance, G = goal
    area_id: str | None = None


class DungeonMap(BaseModel):
    height: int = Field(..., ge=1, le=128)
    width: int = Field(..., ge=1, le=128)
    cells: list[MapCell] = Field(default_factory=list)
    entrance_area_id: str = ""
    goal_area_id: str = ""


class Legend(BaseModel):
    title: str = ""
    backstory: str = ""
    locale_options: list[str] = Field(default_factory=list)
    dm_notes: str = ""


class GeneratedModule(BaseModel):
    """Full Tomb-of-Horrors-style D&D module."""
    version: str = "tomb-module-1.0"
    title: str = "Generated Tomb"
    legend: Legend = Field(default_factory=Legend)
    map: DungeonMap = Field(..., alias="map")
    areas: list[KeyedArea] = Field(default_factory=list)
    traps: list[Trap] = Field(default_factory=list)  # global list for reference
    switches: list[Switch] = Field(default_factory=list)
    clues: list[Clue] = Field(default_factory=list)
    eval_hazards: list[tuple[int, int]] = Field(default_factory=list)  # optional: for DWMB alignment

    class Config:
        populate_by_name = True
