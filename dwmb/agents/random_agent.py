from __future__ import annotations

import random
from typing import Any

from dwmb.env import ACTIONS, MOVES


class RandomAgent:
    """Picks random move; reports uniform 0.5 per hazard (no inference)."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    def act(self, obs: dict[str, Any], hazards: list[tuple[int, int]]) -> tuple[str, list[float]]:
        move_actions = [a for a in ACTIONS if a in MOVES]
        action = self._rng.choice(move_actions)
        probs = [0.5] * len(hazards)
        return action, probs

    def update_belief(self, action: str, obs_new: dict[str, Any]) -> None:
        pass
