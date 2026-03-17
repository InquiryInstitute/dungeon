"""
Procedural dungeon map builder in the Tomb of Horrors style.
Generates a grid of rooms and corridors with optional dead-ends and branches.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .schema import (
    Door,
    DoorType,
    DungeonMap,
    KeyedArea,
    MapCell,
    Position,
    RoomType,
)

if TYPE_CHECKING:
    from .framework import FrameworkConfig

# Cell type constants
WALL = "#"
FLOOR = "."
DOOR = "D"
SECRET = "S"
ENTRANCE = "E"
GOAL = "G"


@dataclass
class Room:
    id: str
    row: int
    col: int
    height: int
    width: int
    room_type: RoomType = RoomType.CHAMBER
    connections: list[str] = field(default_factory=list)


def _grid_empty(grid: list[list[str]], r: int, c: int, h: int, w: int, margin: int) -> bool:
    """Check if rectangle (r,c) to (r+h, c+w) is empty with margin."""
    rows, cols = len(grid), len(grid[0])
    for rr in range(max(0, r - margin), min(rows, r + h + margin)):
        for cc in range(max(0, c - margin), min(cols, c + w + margin)):
            if grid[rr][cc] != WALL:
                return False
    return True


def _carve_room(grid: list[list[str]], room: Room, cell_type: str = FLOOR) -> None:
    for rr in range(room.row, room.row + room.height):
        for cc in range(room.col, room.col + room.width):
            if 0 <= rr < len(grid) and 0 <= cc < len(grid[0]):
                grid[rr][cc] = cell_type


def _carve_corridor(grid: list[list[str]], r1: int, c1: int, r2: int, c2: int) -> None:
    """L-shaped corridor between (r1,c1) and (r2,c2)."""
    rows, cols = len(grid), len(grid[0])
    r, c = r1, c1
    while r != r2:
        if 0 <= r < rows and 0 <= c < cols:
            grid[r][c] = FLOOR
        r += 1 if r2 > r else -1
    while c != c2:
        if 0 <= r < rows and 0 <= c < cols:
            grid[r][c] = FLOOR
        c += 1 if c2 > c else -1
    if 0 <= r < rows and 0 <= c < cols:
        grid[r][c] = FLOOR


def _room_center(room: Room) -> tuple[int, int]:
    return room.row + room.height // 2, room.col + room.width // 2


def _adjacent_cells(r: int, c: int, rows: int, cols: int) -> list[tuple[int, int]]:
    out = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            out.append((nr, nc))
    return out


def build_dungeon(
    height: int = 24,
    width: int = 32,
    min_rooms: int = 8,
    max_rooms: int = 20,
    seed: int | None = None,
) -> tuple[list[list[str]], list[Room]]:
    """
    Build a dungeon grid and list of rooms.
    Returns (grid, rooms). Grid uses WALL, FLOOR, etc.; rooms have ids and connections.
    """
    if seed is not None:
        random.seed(seed)

    grid = [[WALL for _ in range(width)] for _ in range(height)]
    rooms: list[Room] = []
    room_count = random.randint(min_rooms, max_rooms)
    margin = 1
    min_room_h, min_room_w = 3, 3
    max_room_h, max_room_w = 6, 8

    for i in range(room_count * 3):  # try more than needed
        if len(rooms) >= room_count:
            break
        h = random.randint(min_room_h, max_room_h)
        w = random.randint(min_room_w, max_room_w)
        r = random.randint(1, height - h - 2)
        c = random.randint(1, width - w - 2)
        if _grid_empty(grid, r, c, h, w, margin):
            room_id = f"area_{len(rooms) + 1}"
            room = Room(id=room_id, row=r, col=c, height=h, width=w)
            _carve_room(grid, room)
            rooms.append(room)

    # Connect rooms with corridors (simple spanning tree + a few extra)
    if len(rooms) < 2:
        return grid, rooms

    # Build connections: each room (after first) connects to a random previous room
    for i in range(1, len(rooms)):
        other = random.randint(0, i - 1)
        r1, c1 = _room_center(rooms[i])
        r2, c2 = _room_center(rooms[other])
        _carve_corridor(grid, r1, c1, r2, c2)
        rooms[i].connections.append(rooms[other].id)
        rooms[other].connections.append(rooms[i].id)

    # Add a few extra corridors for branches/dead-ends (ToH style)
    extra = min(3, len(rooms) - 1)
    for _ in range(extra):
        a, b = random.sample(range(len(rooms)), 2)
        if rooms[b].id not in rooms[a].connections:
            r1, c1 = _room_center(rooms[a])
            r2, c2 = _room_center(rooms[b])
            _carve_corridor(grid, r1, c1, r2, c2)
            rooms[a].connections.append(rooms[b].id)
            rooms[b].connections.append(rooms[a].id)

    return grid, rooms


def assign_room_types(rooms: list[Room], entrance_id: str, goal_id: str) -> None:
    """Assign RoomType to each room (entrance, goal, dead-end, hall, chamber, etc.)."""
    for room in rooms:
        if room.id == entrance_id:
            room.room_type = RoomType.ENTRANCE
        elif room.id == goal_id:
            room.room_type = RoomType.CRYPT
        elif len(room.connections) == 1:
            room.room_type = random.choice([
                RoomType.DEAD_END,
                RoomType.TRAP_ROOM,
                RoomType.CHAMBER,
            ])
        elif len(room.connections) >= 3:
            room.room_type = random.choice([
                RoomType.HALL,
                RoomType.THRONE_ROOM,
                RoomType.CHAPEL,
            ])
        else:
            room.room_type = random.choice([
                RoomType.CORRIDOR,
                RoomType.CHAMBER,
                RoomType.PUZZLE_ROOM,
                RoomType.PRISON,
            ])


def grid_to_cells(grid: list[list[str]]) -> list[MapCell]:
    """Convert 2D grid to list of MapCell for schema."""
    cells = []
    for r, row in enumerate(grid):
        for c, cell_type in enumerate(row):
            cells.append(MapCell(row=r, col=c, cell_type=cell_type))
    return cells


def build_dungeon_map(
    height: int = 24,
    width: int = 32,
    min_rooms: int = 8,
    max_rooms: int = 20,
    seed: int | None = None,
) -> tuple[DungeonMap, list[Room], list[KeyedArea]]:
    """
    Full build: DungeonMap, Room list, and KeyedArea list.
    Entrance is first room, goal is last room (or farthest).
    """
    grid, rooms = build_dungeon(height, width, min_rooms, max_rooms, seed)
    if not rooms:
        cells = grid_to_cells(grid)
        return (
            DungeonMap(height=height, width=width, cells=cells, entrance_area_id="", goal_area_id=""),
            [],
            [],
        )

    entrance_id = rooms[0].id
    goal_id = rooms[-1].id
    assign_room_types(rooms, entrance_id, goal_id)

    # Mark entrance and goal on grid
    er, ec = _room_center(rooms[0])
    gr, gc = _room_center(rooms[-1])
    grid[er][ec] = ENTRANCE
    grid[gr][gc] = GOAL

    cells = grid_to_cells(grid)
    dungeon_map = DungeonMap(
        height=height,
        width=width,
        cells=cells,
        entrance_area_id=entrance_id,
        goal_area_id=goal_id,
    )

    keyed_areas: list[KeyedArea] = []
    for room in rooms:
        from .framework import random_room_name
        name = random_room_name(room.room_type)
        area = KeyedArea(
            id=room.id,
            position=Position(row=room.row, col=room.col),
            room_type=room.room_type,
            name=name,
            description="",
            connections=room.connections,
        )
        keyed_areas.append(area)

    return dungeon_map, rooms, keyed_areas
