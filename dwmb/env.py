"""
DWMB simulation engine: POMDP step, observe, reset.
State s = (x, θ, h): agent position, static topology, dynamic hidden state (trap armed, switch toggles).
"""
from __future__ import annotations

import random
from typing import Any

from dwmb.schema import DWMBInstance


# Tile symbols for observation (egocentric view). Hidden traps appear as FLOOR.
WALL = "W"
FLOOR = "."
GOAL = "G"
DOOR = "D"
SWITCH = "S"
# In true state we also have trap positions; in observation they render as FLOOR.


ACTIONS = ["Move_N", "Move_S", "Move_E", "Move_W", "Inspect", "Interact", "UseItem"]
MOVES = {"Move_N": (-1, 0), "Move_S": (1, 0), "Move_E": (0, 1), "Move_W": (0, -1)}


class DWMBEnv:
    """
    Single-instance DWMB environment.
    - reset(instance) loads the instance and sets initial state.
    - step(action) returns (obs, reward, terminated, truncated, info).
    - observe() returns current observation (view + event from last step).
    """

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)
        self._instance: DWMBInstance | None = None
        self._height = 0
        self._width = 0
        self._base_grid: list[list[str]] = []  # [r][c] = WALL | FLOOR | GOAL | DOOR | SWITCH
        self._agent: tuple[int, int] = (0, 0)
        self._goal: tuple[int, int] = (0, 0)
        self._trap_positions: set[tuple[int, int]] = set()
        self._trap_armed_initial: dict[tuple[int, int], bool] = {}
        self._trap_disarm_switch: dict[tuple[int, int], str] = {}
        self._switch_positions: dict[str, tuple[int, int]] = {}
        self._switch_effects: dict[str, list[tuple[tuple[int, int], bool]]] = {}
        self._switch_states: dict[str, bool] = {}
        self._radius = 2
        self._p_reveal = 0.15
        self._reward_goal = 1.0
        self._reward_step = -0.001
        self._reward_trap = -0.2
        self._death_on_trap = False
        self._last_event: str = ""
        self._step_count = 0
        self._visited: set[tuple[int, int]] = set()
        self._hazard_activations: list[tuple[int, int]] = []

    def reset(self, instance: DWMBInstance, seed: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        """Load instance and return (obs, info)."""
        if seed is not None:
            self._rng = random.Random(seed)
        self._instance = instance
        g = instance.grid
        self._height = g.height
        self._width = g.width
        # Parse tiles: row-major string into 2D grid
        tiles = g.tiles.strip().replace("\n", "")
        if len(tiles) != self._height * self._width:
            # Extend or truncate to fit
            base = list(FLOOR * (self._height * self._width))
            for i, c in enumerate(tiles[: self._height * self._width]):
                base[i] = c if c in (WALL, FLOOR, GOAL, DOOR) else FLOOR
            tiles = "".join(base)
        self._base_grid = []
        for r in range(self._height):
            row = []
            for c in range(self._width):
                ch = tiles[r * self._width + c]
                row.append(ch if ch in (WALL, FLOOR, GOAL, DOOR) else FLOOR)
            self._base_grid.append(row)

        self._agent = instance.entities.agent_start
        self._goal = instance.entities.goal
        self._base_grid[self._goal[0]][self._goal[1]] = GOAL

        self._trap_positions = set()
        self._trap_armed_initial = {}
        self._trap_disarm_switch = {}
        for t in instance.hidden_state.traps:
            self._trap_positions.add(t.pos)
            self._trap_armed_initial[t.pos] = t.armed
            if t.disarm_switch:
                self._trap_disarm_switch[t.pos] = t.disarm_switch

        self._switch_positions = {}
        self._switch_effects = {}
        self._switch_states = {}
        for s in instance.hidden_state.switches:
            self._switch_positions[s.id] = s.pos
            self._switch_effects[s.id] = [(e.trap_pos, e.armed) for e in s.effects]
            self._switch_states[s.id] = False

        self._radius = instance.visibility.radius
        self._reward_goal = instance.reward.goal
        self._reward_step = instance.reward.step
        self._reward_trap = instance.reward.trap
        self._death_on_trap = instance.terminal.death_on_trap
        self._last_event = ""
        self._step_count = 0
        self._visited = {self._agent}
        self._hazard_activations = []

        obs = self._observe()
        info = {"step": 0, "event": self._last_event}
        return obs, info

    def _trap_armed_now(self, pos: tuple[int, int]) -> bool:
        """Current armed state of trap at pos (depends on switch toggles)."""
        if pos not in self._trap_armed_initial:
            return False
        armed = self._trap_armed_initial[pos]
        sw_id = self._trap_disarm_switch.get(pos)
        if sw_id and self._switch_states.get(sw_id, False):
            for (tpos, effect_armed) in self._switch_effects.get(sw_id, []):
                if tpos == pos:
                    return effect_armed
        return armed

    def _observe(self) -> dict[str, Any]:
        """Egocentric view: grid of size (2*radius+1)^2; traps shown as floor. Event from last step."""
        r, c = self._agent
        rad = self._radius
        view = []
        for dr in range(-rad, rad + 1):
            row = []
            for dc in range(-rad, rad + 1):
                nr, nc = r + dr, c + dc
                if nr < 0 or nr >= self._height or nc < 0 or nc >= self._width:
                    row.append(WALL)
                    continue
                if (nr, nc) in self._switch_positions.values():
                    row.append(SWITCH)
                elif (nr, nc) in self._trap_positions:
                    row.append(FLOOR)  # hidden: trap looks like floor
                else:
                    row.append(self._base_grid[nr][nc])
            view.append(row)
        return {"view": view, "event": self._last_event, "position": [r, c]}

    def observe(self) -> dict[str, Any]:
        """Current observation (view + last event)."""
        return self._observe()

    def step(self, action: str) -> tuple[dict[str, Any], float, bool, bool, dict[str, Any]]:
        """
        Apply action. Returns (obs, reward, terminated, truncated, info).
        info includes "event", "hazard_activated" (pos if stepped on armed trap), "goal_reached", "died".
        """
        self._last_event = ""
        reward = self._reward_step
        terminated = False
        truncated = False
        hazard_activated: tuple[int, int] | None = None
        goal_reached = False
        died = False

        if action in MOVES:
            dr, dc = MOVES[action]
            r, c = self._agent
            nr, nc = r + dr, c + dc
            if 0 <= nr < self._height and 0 <= nc < self._width:
                cell = self._base_grid[nr][nc]
                if (nr, nc) in self._switch_positions.values():
                    cell = SWITCH
                if cell == WALL:
                    self._last_event = "bump"
                else:
                    self._agent = (nr, nc)
                    self._visited.add((nr, nc))
                    if (nr, nc) == self._goal:
                        goal_reached = True
                        terminated = True
                        reward += self._reward_goal
                        self._last_event = "goal"
                    elif (nr, nc) in self._trap_positions and self._trap_armed_now((nr, nc)):
                        hazard_activated = (nr, nc)
                        self._hazard_activations.append((nr, nc))
                        reward += self._reward_trap
                        self._last_event = "trap"
                        if self._death_on_trap:
                            died = True
                            terminated = True
                    else:
                        self._last_event = "moved"
            else:
                self._last_event = "bump"

        elif action == "Inspect":
            # Inspect current or adjacent tile with low success probability
            if self._rng.random() < self._p_reveal:
                self._last_event = "reveal"  # generic; could refine to "trap" or "secret"
            else:
                self._last_event = "nothing"

        elif action == "Interact":
            r, c = self._agent
            for sw_id, pos in self._switch_positions.items():
                if (r, c) == pos:
                    self._switch_states[sw_id] = not self._switch_states[sw_id]
                    self._last_event = "click"
                    break
            else:
                self._last_event = "nothing"

        elif action == "UseItem":
            self._last_event = "no_item"

        self._step_count += 1
        obs = self._observe()
        info = {
            "step": self._step_count,
            "event": self._last_event,
            "hazard_activated": hazard_activated,
            "goal_reached": goal_reached,
            "died": died,
            "position": list(self._agent),
            "hazards_for_PIR": list(self._instance.eval.hazards_for_PIR) if self._instance else [],
        }
        return obs, reward, terminated, truncated, info

    @property
    def agent(self) -> tuple[int, int]:
        return self._agent

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def instance(self) -> DWMBInstance | None:
        return self._instance

    @property
    def hazard_activations(self) -> list[tuple[int, int]]:
        return list(self._hazard_activations)

    @property
    def visited(self) -> set[tuple[int, int]]:
        return set(self._visited)
