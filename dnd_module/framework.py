"""
Tomb of Horrors framework: trap templates, room themes, and clue patterns.
Inspired by the classic module's traps, puzzles, and deceptive design.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .schema import (
    Clue,
    Door,
    DoorType,
    Position,
    RoomType,
    Trap,
    TrapKind,
)

if TYPE_CHECKING:
    pass


# --- Trap templates (damage, save, short description) ---
TRAP_TEMPLATES: dict[TrapKind, dict[str, str]] = {
    TrapKind.PIT: {
        "damage": "10' pit, 1-6 per spike, 5 spikes (poison save)",
        "save": "vs poison per spike",
        "description": "Counter-weighted trap door; thrusting with pole reveals 4-in-6.",
    },
    TrapKind.SLIDING_BLOCK: {
        "damage": "crushed (no save)",
        "save": "none",
        "description": "Stone block slides shut; 10 counts to escape. Iron bar on floor can wedge it.",
    },
    TrapKind.CEILING_COLLAPSE: {
        "damage": "5-50 (5d10) hit points, no save",
        "save": "none",
        "description": "Roof collapses when doors opened or ceiling prodded.",
    },
    TrapKind.SPEAR: {
        "damage": "2-16 (2d8)",
        "save": "vs magic",
        "description": "Spear shoots from door when opened; refires when door closed and re-opened.",
    },
    TrapKind.POISON_NEEDLE: {
        "damage": "poison (save or die)",
        "save": "vs poison",
        "description": "Easily detectable needle on catch; avoid by pressing with dagger pommel.",
    },
    TrapKind.GAS: {
        "damage": "e.g. strength 2-8 for 48 hours, or sleep 2-8 turns",
        "save": "vs poison",
        "description": "Cloud fills area; hold breath or save.",
    },
    TrapKind.CRUSHING: {
        "damage": "10-100 (10d10) or squashed to jelly",
        "save": "none (avoid by leaving south 15' before count ends)",
        "description": "Floor rises; 5 count to escape zone.",
    },
    TrapKind.TELEPORT: {
        "damage": "none (teleport to another area)",
        "save": "none",
        "description": "Living matter teleported to area X; non-living to area Y (e.g. nude).",
    },
    TrapKind.CURSE: {
        "damage": "alignment/sex reversed, or similar",
        "save": "none",
        "description": "Passing through portal applies curse; re-entry may reverse.",
    },
    TrapKind.SPHERE_ANNIHILATION: {
        "damage": "permanent destruction",
        "save": "none",
        "description": "Gaping mouth; anything entering is utterly destroyed.",
    },
    TrapKind.SPIKE_VOLLEY: {
        "damage": "2-5 spikes, 1-6 each, no save",
        "save": "none",
        "description": "Stepping on last 3' of pit triggers upward spike volley.",
    },
    TrapKind.TILTING_FLOOR: {
        "damage": "slide into lava/abyss; 1-6 then 2-12 heat",
        "save": "none",
        "description": "Floor tilts; 5 count to retreat at 1' per 1\" movement.",
    },
    TrapKind.MAGIC_MOUTH: {
        "damage": "none (riddle or taunt)",
        "save": "none",
        "description": "Spell speaks when condition met; may give clue or misdirection.",
    },
}

# --- Door open methods (ToH-style variety) ---
DOOR_OPEN_METHODS: list[str] = [
    "pull down",
    "pivots centrally",
    "pull inward and up at bottom",
    "slides up",
    "double panels pull inward",
    "slide left",
    "7 studs — press all to open; 1 & 7 bring door falling inwards for 3-18 h.p. damage",
    "ring pull",
    "key (specific key id)",
    "dispel magic / remove curse (magical secret door)",
    "knock, disintegrate, rock to mud, or stone to flesh",
]

# --- Room type display names ---
ROOM_NAMES: dict[RoomType, list[str]] = {
    RoomType.ENTRANCE: ["False Entrance Tunnel", "Entrance to the Tomb", "Crawl Space"],
    RoomType.CORRIDOR: ["Corridor", "Passage", "Winding Passage"],
    RoomType.HALL: ["Great Hall", "Hall of Spheres", "Columned Hall"],
    RoomType.CHAMBER: ["Chamber", "Room", "Cubicle"],
    RoomType.PRISON: ["Forsaken Prison", "Guard Room", "Holding Cell"],
    RoomType.CHAPEL: ["Chapel of Evil", "Shrine", "Temple Area"],
    RoomType.THRONE_ROOM: ["Pillared Throne Room", "Throne Room", "Dais Chamber"],
    RoomType.CRYPT: ["Crypt", "Burial Vault", "False Crypt"],
    RoomType.TREASURE_ROOM: ["Treasure Room", "Hoard", "False Treasure Room"],
    RoomType.TRAP_ROOM: ["Trapped Corridor", "Deadly Gallery", "Trap Room"],
    RoomType.PUZZLE_ROOM: ["Arch of Mist", "Portal Chamber", "Puzzle Room"],
    RoomType.DEAD_END: ["Dead End", "Blind Corridor", "False Passage"],
}

# --- Clue format snippets (for generator) ---
CLUE_PHRASES: list[str] = [
    "Go back to the tormentor or through the arch.",
    "Shun green if you can; night's good color is for those of great valor.",
    "If shades of red stand for blood, the wise will not need sacrifice aught but a loop of magical metal.",
    "Two pits along the way will be found to lead to a fortuitous fall; check the wall.",
    "Beware of trembling hands and what will maul.",
    "If you find the false you find the true.",
    "The iron men of visage grim do more than meets the viewer's eye.",
    "Look low and high for gold, to hear a tale untold.",
]


@dataclass
class FrameworkConfig:
    """Configuration for generation (can be overridden)."""
    title: str = "Generated Tomb of Horrors"
    grid_height: int = 24
    grid_width: int = 32
    min_rooms: int = 8
    max_rooms: int = 20
    trap_density: float = 0.35
    clue_density: float = 0.25
    secret_door_chance: float = 0.3
    false_door_chance: float = 0.2
    use_switches: bool = True
    seed: int | None = None

    def ensure_seed(self) -> None:
        if self.seed is not None:
            random.seed(self.seed)


def make_trap(
    row: int,
    col: int,
    kind: TrapKind | None = None,
    armed: bool = True,
    disarm_switch_id: str | None = None,
) -> Trap:
    kind = kind or random.choice(list(TrapKind))
    template = TRAP_TEMPLATES.get(kind, {})
    return Trap(
        position=Position(row=row, col=col),
        kind=kind,
        armed=armed,
        disarm_switch_id=disarm_switch_id,
        damage=template.get("damage"),
        save=template.get("save"),
        description=template.get("description", ""),
    )


def make_door(
    row: int,
    col: int,
    door_type: DoorType = DoorType.CLOSED,
    leads_to: str | None = None,
    open_method: str | None = None,
) -> Door:
    if open_method is None and door_type == DoorType.SECRET:
        open_method = random.choice(DOOR_OPEN_METHODS[:7])
    return Door(
        position=Position(row=row, col=col),
        door_type=door_type,
        leads_to_area=leads_to,
        open_method=open_method,
    )


def make_clue(text: str, area_id: str | None = None, hints_at: list[str] | None = None) -> Clue:
    return Clue(
        area_id=area_id or "",
        format="riddle",
        text=text,
        hints_at=hints_at or [],
    )


def random_room_name(room_type: RoomType) -> str:
    names = ROOM_NAMES.get(room_type, ["Chamber"])
    return random.choice(names)
