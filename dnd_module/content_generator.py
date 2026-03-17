"""
Generates descriptive text for rooms, traps, and clues in Tomb of Horrors style.
Uses templates and procedural variation to create DM-ready copy.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .schema import Clue, KeyedArea, RoomType, Trap, TrapKind

if TYPE_CHECKING:
    from .framework import FrameworkConfig


# --- Room description templates by type ---
ROOM_DESCRIPTIONS: dict[RoomType, list[str]] = {
    RoomType.ENTRANCE: [
        "The corridor is of plain stone, roughly worked, dark and full of cobwebs. Daylight reveals a pair of doors at the end.",
        "A low tunnel leads in. The ceiling is obscured; casual observation will not reveal its construction.",
        "Bright colors are visible even by torchlight—stones and pigments undimmed by time. A distinct path winds ahead.",
    ],
    RoomType.CORRIDOR: [
        "A plain stone passageway; the walls are smooth and the floor is paved.",
        "The corridor narrows here. Something about the masonry suggests great age.",
        "Dust hangs in the air. Faint scratches mark the floor where others have passed.",
    ],
    RoomType.HALL: [
        "A great hall with inlaid tiles underfoot and painted figures on the walls—animals, glyphs, and humanoid shapes.",
        "Massive columns support the ceiling. The floor is mosaic; the walls show scenes of strange significance.",
        "Spheres of different colors appear in the murals—gold, silver, green, and others—each held by a figure.",
    ],
    RoomType.CHAMBER: [
        "A smallish chamber with bare stone. No obvious exit save the way you came.",
        "The room is cluttered with the remnants of furniture and old containers.",
        "Plain walls and a high ceiling. Something here feels watched.",
    ],
    RoomType.PRISON: [
        "This miserable cubicle appears to have no means of egress. Levers protrude from one wall.",
        "Iron bars and stone. The air is still. Three levers are set in the south wall.",
        "A cell with no visible door. Detection magic reveals nothing—yet there are levers.",
    ],
    RoomType.CHAPEL: [
        "Scenes of life are painted on the walls, but the figures show rotting flesh and skeletal hands.",
        "A temple area with pews and an altar. A faint aura of good can be detected—or is it illusion?",
        "Religious symbols of good alignment mix with depictions of decay. A mosaic path leads to the altar.",
    ],
    RoomType.THRONE_ROOM: [
        "Scores of massive columns fill the chamber. Each pillar radiates magic when detected.",
        "A huge dais supports an obsidian throne inlaid with silver and ivory. Pastel colors cover the floor.",
        "Columns stretch to the ceiling. Touching a pillar causes uncontrollable levitation.",
    ],
    RoomType.CRYPT: [
        "A small burial vault with an arched ceiling. The center of the floor has a shallow depression.",
        "Nothing obvious is here—but a careful search reveals a keyhole in the floor.",
        "The end of the adventure—one way or another—is near. A crypt with a single notable feature.",
    ],
    RoomType.TREASURE_ROOM: [
        "An imposing chamber with a silvered ceiling. Statues of black iron stand in the corners.",
        "The walls are ivory with gold inlay. Iron chests are set into the stone.",
        "Treasure seems to await—but the room radiates anti-magic. Proceed with caution.",
    ],
    RoomType.TRAP_ROOM: [
        "The passage here is narrow. The floor shows slight irregularities.",
        "A gallery with no side passages. The walls are smooth and unbroken.",
        "Something about this place sets the nerves on edge. Test each step.",
    ],
    RoomType.PUZZLE_ROOM: [
        "An archway blocks the path. Stones set into the frame glow when approached—yellow, blue, orange.",
        "A portal filled with mist. No magic allows sight through the vapors.",
        "The correct sequence of pressed stones will clear the way. Wrong choices lead elsewhere.",
    ],
    RoomType.DEAD_END: [
        "The passage ends in solid stone. Or does it? Detection may reveal more.",
        "A blind corridor. Perhaps something was meant to be here.",
        "Dead end. The walls are featureless—or so they appear.",
    ],
}


def room_description(room_type: RoomType, seed_hint: int | None = None) -> str:
    if seed_hint is not None:
        random.seed(seed_hint)
    options = ROOM_DESCRIPTIONS.get(room_type, ["A chamber."])
    return random.choice(options)


def trap_short_description(trap: Trap) -> str:
    k = trap.kind
    if trap.description:
        return trap.description
    one_liners = {
        TrapKind.PIT: "A pit lies concealed beneath the floor.",
        TrapKind.SLIDING_BLOCK: "A massive block can seal the passage.",
        TrapKind.CEILING_COLLAPSE: "The ceiling is unstable.",
        TrapKind.SPEAR: "Opening the door triggers a spear.",
        TrapKind.POISON_NEEDLE: "A needle trap guards the mechanism.",
        TrapKind.GAS: "Gas will fill the area when triggered.",
        TrapKind.TELEPORT: "The portal teleports the unwary.",
        TrapKind.CURSE: "A curse awaits those who pass through.",
        TrapKind.SPHERE_ANNIHILATION: "The mouth destroys all that enter.",
        TrapKind.SPIKE_VOLLEY: "Spikes shoot up from the pit.",
        TrapKind.TILTING_FLOOR: "The floor tilts toward doom.",
        TrapKind.MAGIC_MOUTH: "A magic mouth speaks when triggered.",
    }
    return one_liners.get(k, "A trap is present.")


def generate_riddle_clue(hints_at_areas: list[str] | None = None, seed_hint: int | None = None) -> str:
    """Generate a short riddle-style clue that hints at areas or actions."""
    if seed_hint is not None:
        random.seed(seed_hint)
    hints_at_areas = hints_at_areas or []
    lines = [
        "Go back to the tormentor or through the arch.",
        "Shun green if you can; night's good color is for those of great valor.",
        "If you find the false you find the true.",
        "The iron men of visage grim do more than meets the viewer's eye.",
        "Look low and high for gold, to hear a tale untold.",
        "Two pits along the way will be found to lead to a fortuitous fall; check the wall.",
        "Beware of trembling hands and what will maul.",
    ]
    return random.choice(lines)


def generate_inscription_clue(area_id: str, seed_hint: int | None = None) -> str:
    """Short inscription that might reference a location or object."""
    if seed_hint is not None:
        random.seed(seed_hint)
    templates = [
        f"The one who built this place mocks: \"You will be mine in the end—no matter what.\"",
        "Runes in the floor read: ACERERAK CONGRATULATES YOU ON YOUR POWERS OF OBSERVATION.",
        "A faint message: \"So make of this whatever you wish.\"",
        "The script warns: \"Into the columned hall you'll come, and there the throne that's key and keyed.\"",
    ]
    return random.choice(templates)


def populate_area_descriptions(areas: list[KeyedArea], seed: int | None = None) -> None:
    """Fill in description and name for each KeyedArea."""
    if seed is not None:
        random.seed(seed)
    for i, area in enumerate(areas):
        if not area.description:
            area.description = room_description(area.room_type, seed_hint=(seed or 0) + i)
        if not area.name:
            from .framework import random_room_name
            area.name = random_room_name(area.room_type)
