"""
Procedural DWMB instance generator. Tier parameters and adversarial constraints per report.
"""
from __future__ import annotations

import random
from collections import deque
from typing import Any

from dwmb.schema import (
    DWMBInstance,
    Eval,
    Entities,
    Grid,
    HiddenState,
    Reward,
    Switch,
    SwitchEffect,
    Terminal,
    Topology,
    Trap,
    Visibility,
)

# Tier parameters (report: T1–T2 up to 12×12, T4–T5 up to 20×20, r=2)
TIER_PARAMS = {
    1: {"min_size": 8, "max_size": 12, "max_traps": 1, "max_switches": 0, "min_switch_trap_dist": 0},
    2: {"min_size": 8, "max_size": 12, "max_traps": 2, "max_switches": 1, "min_switch_trap_dist": 0},
    3: {"min_size": 12, "max_size": 16, "max_traps": 3, "max_switches": 2, "min_switch_trap_dist": 2},
    4: {"min_size": 16, "max_size": 20, "max_traps": 4, "max_switches": 3, "min_switch_trap_dist": 4},
    5: {"min_size": 18, "max_size": 22, "max_traps": 5, "max_switches": 4, "min_switch_trap_dist": 4},
}


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _bfs_reachable(grid: list[list[str]], start: tuple[int, int], goals: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """All floor cells reachable from start (without stepping on goals if they block)."""
    h, w = len(grid), len(grid[0])
    reachable = set()
    q: deque[tuple[int, int]] = deque([start])
    reachable.add(start)
    while q:
        r, c = q.popleft()
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in reachable:
                ch = grid[nr][nc]
                if ch == "." or ch == "G":
                    reachable.add((nr, nc))
                    q.append((nr, nc))
    return reachable


def _has_path_avoiding(grid: list[list[str]], start: tuple[int, int], goal: tuple[int, int], avoid: set[tuple[int, int]]) -> bool:
    """BFS from start to goal without stepping on any cell in avoid."""
    h, w = len(grid), len(grid[0])
    q: deque[tuple[int, int]] = deque([start])
    seen = {start}
    while q:
        r, c = q.popleft()
        if (r, c) == goal:
            return True
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in seen and (nr, nc) not in avoid:
                ch = grid[nr][nc]
                if ch == "." or ch == "G":
                    seen.add((nr, nc))
                    q.append((nr, nc))
    return False


def _build_empty_grid(height: int, width: int, add_walls: bool = True) -> list[list[str]]:
    """Border walls, floor inside. Optionally add a few internal walls for T5."""
    grid = [["." for _ in range(width)] for _ in range(height)]
    for c in range(width):
        grid[0][c] = "W"
        grid[height - 1][c] = "W"
    for r in range(height):
        grid[r][0] = "W"
        grid[r][width - 1] = "W"
    if add_walls and height >= 10 and width >= 10:
        # One vertical bar to create two corridors (alternate paths / distractors)
        mid_c = width // 2
        for r in range(2, height - 2):
            if r != height // 2:
                grid[r][mid_c] = "W"
    return grid


def generate(seed: int, tier: int) -> DWMBInstance:
    """
    Generate a DWMB instance for the given tier and seed.
    Enforces: indistinguishability (traps = floor in obs), alternate safe path,
    non-local causality for T4+, distractors for T5.
    """
    rng = random.Random(seed)
    params = TIER_PARAMS.get(tier, TIER_PARAMS[1])
    min_sz = params["min_size"]
    max_sz = params["max_size"]
    max_traps = params["max_traps"]
    max_switches = params["max_switches"]
    min_switch_trap_dist = params["min_switch_trap_dist"]

    height = rng.randint(min_sz, max_sz)
    width = rng.randint(min_sz, max_sz)
    add_internal_walls = tier >= 3
    grid = _build_empty_grid(height, width, add_walls=add_internal_walls)

    floor_cells = [
        (r, c) for r in range(1, height - 1) for c in range(1, width - 1)
        if grid[r][c] == "."
    ]
    if len(floor_cells) < 4:
        grid = _build_empty_grid(height, width, add_walls=False)
        floor_cells = [(r, c) for r in range(1, height - 1) for c in range(1, width - 1)]

    # Ensure agent and goal are in same connected component (path exists)
    reachable = _bfs_reachable(grid, floor_cells[0], set())
    floor_cells = [p for p in floor_cells if p in reachable]
    if len(floor_cells) < 4:
        grid = _build_empty_grid(height, width, add_walls=False)
        floor_cells = [(r, c) for r in range(1, height - 1) for c in range(1, width - 1)]

    rng.shuffle(floor_cells)
    agent_start = floor_cells[0]
    goal = floor_cells[1]
    candidates = [p for p in floor_cells[2:] if p != agent_start and p != goal]

    n_traps = min(rng.randint(1, max_traps), len(candidates))
    trap_positions: list[tuple[int, int]] = []
    for i in range(n_traps):
        if not candidates:
            break
        idx = rng.randint(0, len(candidates) - 1)
        trap_positions.append(candidates.pop(idx))

    # Alternate safe path: at least one path from start to goal avoiding all traps
    if trap_positions and not _has_path_avoiding(grid, agent_start, goal, set(trap_positions)):
        # Remove one trap from the only path so there is a detour
        for j in range(len(trap_positions)):
            others = set(trap_positions) - {trap_positions[j]}
            if _has_path_avoiding(grid, agent_start, goal, others):
                trap_positions.pop(j)
                break

    switches: list[Switch] = []
    traps: list[Trap] = []
    switch_by_id: dict[str, Switch] = {}

    if tier >= 2 and max_switches >= 1 and trap_positions and len(candidates) >= 1:
        n_switches = min(rng.randint(1, max_switches), len(candidates), len(trap_positions))
        for i in range(n_switches):
            trap_pos = trap_positions[i % len(trap_positions)]
            # Switch must be min_switch_trap_dist away for T4+
            valid_switch_cells = [
                p for p in candidates
                if _manhattan(p, trap_pos) >= min_switch_trap_dist
            ] if min_switch_trap_dist > 0 else list(candidates)
            if not valid_switch_cells:
                valid_switch_cells = [p for p in floor_cells if p not in trap_positions and p != agent_start and p != goal]
                valid_switch_cells = [p for p in valid_switch_cells if _manhattan(p, trap_pos) >= max(1, min_switch_trap_dist - 1)]
            if valid_switch_cells:
                sw_pos = rng.choice(valid_switch_cells)
                if sw_pos in candidates:
                    candidates.remove(sw_pos)
                sw_id = f"s{i + 1}"
                switch_by_id[sw_id] = Switch(
                    id=sw_id,
                    pos=sw_pos,
                    effects=[SwitchEffect(trap_pos=trap_pos, armed=False)],
                )
                switches.append(switch_by_id[sw_id])

    for i, pos in enumerate(trap_positions):
        disarm_switch = None
        for sw in switches:
            for eff in sw.effects:
                if eff.trap_pos == pos:
                    disarm_switch = sw.id
                    break
        traps.append(Trap(
            pos=pos,
            kind=rng.choice(["pit", "slick"]),
            armed=True,
            disarm_switch=disarm_switch,
        ))

    tiles = "".join("".join(row) for row in grid)
    # Goal cell in grid
    gr, gc = goal
    row = list(grid[gr])
    row[gc] = "G"
    grid[gr] = row
    tiles = "".join("".join(row) for row in grid)

    instance = DWMBInstance(
        version="dwmb-0.1",
        grid=Grid(height=height, width=width, tiles=tiles),
        visibility=Visibility(radius=2, line_of_sight=True),
        entities=Entities(agent_start=agent_start, goal=goal),
        topology=Topology(doors=[], secret_edges=[]),
        hidden_state=HiddenState(traps=traps, switches=switches),
        reward=Reward(goal=1.0, step=-0.001, trap=-0.2),
        terminal=Terminal(goal=True, death_on_trap=False),
        eval=Eval(hazards_for_PIR=[t.pos for t in traps]),
    )
    return instance


def generate_counterfactual(instance: DWMBInstance, seed: int) -> DWMBInstance:
    """
    Counterfactual: permute trap positions (preserve geometry). Same grid and entity counts;
    trap positions are shuffled among themselves so switch–trap assignments follow the permutation.
    """
    rng = random.Random(seed)
    traps = list(instance.hidden_state.traps)
    switches = list(instance.hidden_state.switches)
    if not traps:
        return instance

    positions = [t.pos for t in traps]
    rng.shuffle(positions)
    # Trap j moves from traps[j].pos to positions[j]
    new_traps = [
        Trap(pos=positions[j], kind=traps[j].kind, armed=True, disarm_switch=traps[j].disarm_switch)
        for j in range(len(traps))
    ]
    # Map old pos -> new pos: old traps[j].pos -> positions[j]
    old_to_new = {traps[j].pos: positions[j] for j in range(len(traps))}
    new_switches = []
    for sw in switches:
        new_effects = [
            SwitchEffect(trap_pos=old_to_new[eff.trap_pos], armed=eff.armed)
            for eff in sw.effects if eff.trap_pos in old_to_new
        ]
        new_switches.append(Switch(id=sw.id, pos=sw.pos, effects=new_effects))

    return DWMBInstance(
        version=instance.version,
        grid=instance.grid,
        visibility=instance.visibility,
        entities=instance.entities,
        topology=instance.topology,
        hidden_state=HiddenState(traps=new_traps, switches=new_switches),
        reward=instance.reward,
        terminal=instance.terminal,
        eval=Eval(hazards_for_PIR=[t.pos for t in new_traps]),
    )
