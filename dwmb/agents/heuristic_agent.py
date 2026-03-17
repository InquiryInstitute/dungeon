"""
Cautious heuristic: higher belief for hazard tiles we haven't visited; random move.
No goal in observation (per report); belief only drives PIR logging.
"""
from __future__ import annotations

import random
from typing import Any

from dwmb.env import ACTIONS, MOVES


class HeuristicAgent:
    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)
        self._visited: set[tuple[int, int]] = set()

    def act(self, obs: dict[str, Any], hazards: list[tuple[int, int]]) -> tuple[str, list[float]]:
        pos = tuple(obs.get("position", [0, 0]))
        self._visited.add(pos)
        probs = [0.15 if h in self._visited else 0.55 for h in hazards]
        move_actions = [a for a in ACTIONS if a in MOVES]
        action = self._rng.choice(move_actions)
        return action, probs

    def update_belief(self, action: str, obs_new: dict[str, Any]) -> None:
        pos = obs_new.get("position")
        if pos is not None:
            self._visited.add(tuple(pos))
