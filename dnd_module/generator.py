"""
Main module generator: builds map, places traps and clues, outputs full D&D module.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .content_generator import (
    generate_inscription_clue,
    generate_riddle_clue,
    populate_area_descriptions,
)
from .framework import (
    FrameworkConfig,
    make_clue,
    make_door,
    make_trap,
    TRAP_TEMPLATES,
)
from .map_builder import build_dungeon_map
from .schema import (
    Clue,
    DoorType,
    GeneratedModule,
    KeyedArea,
    Legend,
    Position,
    Switch,
    Trap,
    TrapKind,
)

if TYPE_CHECKING:
    pass


def place_traps_in_areas(
    areas: list[KeyedArea],
    trap_density: float = 0.35,
    use_switches: bool = True,
    seed: int | None = None,
) -> tuple[list[Trap], list[Switch]]:
    """
    Place traps in some areas; optionally add switches that disarm distant traps.
    Returns (all_traps, all_switches). Traps are also appended to the relevant KeyedAreas.
    """
    if seed is not None:
        random.seed(seed)
    all_traps: list[Trap] = []
    all_switches: list[Switch] = []
    switch_id = 0

    # Decide which areas get traps (avoid entrance and goal for fairness)
    entrance_goal = {a.id for a in areas if a.room_type.value in ("entrance", "crypt")}
    candidate_areas = [a for a in areas if a.id not in entrance_goal and a.room_type.value != "entrance"]
    n_traps = max(1, int(len(candidate_areas) * trap_density))
    trap_areas = random.sample(candidate_areas, min(n_traps, len(candidate_areas)))

    for area in trap_areas:
        # One trap per trap area, placed at center of room
        pos = Position(row=area.position.row + 1, col=area.position.col + 1)
        kind = random.choice(list(TrapKind))
        template = TRAP_TEMPLATES.get(kind, {})
        disarm_id = None
        if use_switches and random.random() < 0.4:
            switch_id += 1
            disarm_id = f"s{switch_id}"
        trap = Trap(
            position=pos,
            kind=kind,
            armed=True,
            disarm_switch_id=disarm_id,
            damage=template.get("damage"),
            save=template.get("save"),
            description=template.get("description", ""),
        )
        area.traps.append(trap)
        all_traps.append(trap)

        if disarm_id:
            # Place switch in a different area
            other_areas = [a for a in areas if a.id != area.id]
            if other_areas:
                switch_area = random.choice(other_areas)
                switch_pos = Position(
                    row=switch_area.position.row + 1,
                    col=switch_area.position.col + 1,
                )
                sw = Switch(
                    id=disarm_id,
                    position=switch_pos,
                    effects=[{"trap_id": area.id, "armed": False}],
                    description="Lever or stud; toggling disarms a distant trap.",
                )
                all_switches.append(sw)
                switch_area.switches.append(sw)

    return all_traps, all_switches


def add_doors_between_areas(areas: list[KeyedArea], seed: int | None = None) -> None:
    """Add door objects at boundaries between connected areas (simplified: one door per connection)."""
    if seed is not None:
        random.seed(seed)
    area_by_id = {a.id: a for a in areas}
    for area in areas:
        for conn_id in area.connections:
            if conn_id not in area_by_id:
                continue
            other = area_by_id[conn_id]
            # Add door on this side (at edge of room)
            door_type = DoorType.CLOSED
            if random.random() < 0.2:
                door_type = DoorType.SECRET
            elif random.random() < 0.15:
                door_type = DoorType.FALSE
            d = make_door(
                area.position.row,
                area.position.col + area.connections.index(conn_id),
                door_type=door_type,
                leads_to=conn_id,
            )
            if d not in area.doors:
                area.doors.append(d)


def place_clues(
    areas: list[KeyedArea],
    clues: list[Clue],
    clue_density: float = 0.25,
    seed: int | None = None,
) -> None:
    """Add clues to some areas and to the global clues list."""
    if seed is not None:
        random.seed(seed)
    n_clues = max(1, int(len(areas) * clue_density))
    clue_areas = random.sample(areas, min(n_clues, len(areas)))
    for i, area in enumerate(clue_areas):
        text = generate_riddle_clue(hints_at_areas=[], seed_hint=(seed or 0) + i)
        hint_areas = random.sample([a.id for a in areas if a.id != area.id], min(2, len(areas) - 1))
        clue = make_clue(text, area_id=area.id, hints_at=hint_areas)
        area.clues.append(clue)
        clues.append(clue)
    # One inscription-style clue
    if areas:
        ins_area = random.choice(areas)
        ins = make_clue(
            generate_inscription_clue(ins_area.id, seed_hint=(seed or 0) + 999),
            area_id=ins_area.id,
            hints_at=[],
        )
        ins_area.clues.append(ins)
        clues.append(ins)


def build_legend(title: str, seed: int | None = None) -> Legend:
    if seed is not None:
        random.seed(seed)
    return Legend(
        title=title,
        backstory="Somewhere under a lost and lonely hill lies a labyrinthine crypt. It is filled with terrible traps, "
        "strange guardians, and rich treasures—but the true nature of the place is known only to the one who built it.",
        locale_options=[
            "The highest hill on the plains",
            "An unmapped island in the great lake",
            "In the wastes of the desert",
            "At the border of the northern duchy",
            "Somewhere in the vast swamp",
            "On an island beyond the realm of the sea barons",
        ],
        dm_notes="This is a thinking person's module. Negotiation requires caution and observation. "
        "Read keyed areas as players arrive; never give information characters would have no way of knowing.",
    )


def generate_module(config: FrameworkConfig | None = None) -> GeneratedModule:
    """
    Generate a full Tomb-of-Horrors-style D&D module.
    """
    config = config or FrameworkConfig()
    config.ensure_seed()

    # Build map and keyed areas
    dungeon_map, rooms, keyed_areas = build_dungeon_map(
        height=config.grid_height,
        width=config.grid_width,
        min_rooms=config.min_rooms,
        max_rooms=config.max_rooms,
        seed=config.seed,
    )

    if not keyed_areas:
        return GeneratedModule(
            title=config.title if getattr(config, "title", None) else "Generated Tomb",
            legend=build_legend("Generated Tomb", config.seed),
            map=dungeon_map,
            areas=[],
            traps=[],
            switches=[],
            clues=[],
        )

    # Populate room descriptions and names
    populate_area_descriptions(keyed_areas, seed=config.seed)

    # Place traps and switches
    all_traps, all_switches = place_traps_in_areas(
        keyed_areas,
        trap_density=config.trap_density,
        use_switches=config.use_switches,
        seed=config.seed,
    )

    # Doors between areas (optional; can be minimal for first version)
    add_doors_between_areas(keyed_areas, seed=config.seed)

    # Clues
    global_clues: list[Clue] = []
    place_clues(keyed_areas, global_clues, clue_density=config.clue_density, seed=config.seed)

    # Eval hazards (positions of traps for optional DWMB alignment)
    eval_hazards = [ (t.position.row, t.position.col) for t in all_traps ]

    title = config.title
    return GeneratedModule(
        version="tomb-module-1.0",
        title=title,
        legend=build_legend(title, config.seed),
        map=dungeon_map,
        areas=keyed_areas,
        traps=all_traps,
        switches=all_switches,
        clues=global_clues,
        eval_hazards=eval_hazards,
    )
