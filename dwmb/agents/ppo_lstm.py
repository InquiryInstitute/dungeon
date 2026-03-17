"""
Minimal PPO+LSTM baseline: view encoder, LSTM, policy + value + belief head.
Belief head outputs per-hazard P(dangerous) for PIR; trained with BCE when labels available.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from dwmb.env import ACTIONS, MOVES

# Tile encoding: W=0, .=1, G=2, D=3, S=4
TILE_MAP = {"W": 0, ".": 1, "G": 2, "D": 3, "S": 4}
NUM_TILES = 5
VIEW_SIZE = 5  # 2*2+1
ACTION_IDS = {a: i for i, a in enumerate(ACTIONS)}
ID_ACTION = {i: a for i, a in enumerate(ACTIONS)}
MAX_HAZARDS = 8


def _view_to_tensor(view: list[list[str]]) -> "torch.Tensor":
    if not TORCH_AVAILABLE:
        raise RuntimeError("PyTorch required for PPOLSTMAgent")
    import torch
    rows = []
    for row in view:
        rows.append([TILE_MAP.get(c, 1) for c in row])
    t = torch.tensor(rows, dtype=torch.long)
    return t.unsqueeze(0).unsqueeze(0)


if TORCH_AVAILABLE:
    nn = __import__("torch").nn


if TORCH_AVAILABLE:

    class PPOLSTMModule(nn.Module):
        def __init__(self, lstm_dim: int = 64, max_hazards: int = MAX_HAZARDS) -> None:
            super().__init__()
            self.max_hazards = max_hazards
            self.embed = nn.Embedding(NUM_TILES, 4)
            self.conv = nn.Sequential(
                nn.Conv2d(4, 16, 2),
                nn.ReLU(),
                nn.Flatten(),
            )
            flat = 16 * (VIEW_SIZE - 1) * (VIEW_SIZE - 1)
            self.lstm = nn.LSTM(flat, lstm_dim, batch_first=True)
            self.lstm_dim = lstm_dim
            self.policy = nn.Linear(lstm_dim, len(ACTIONS))
            self.value = nn.Linear(lstm_dim, 1)
            self.belief = nn.Linear(lstm_dim, max_hazards)

        def forward(
            self,
            view_tensor: "torch.Tensor",
            lstm_hidden: tuple["torch.Tensor", "torch.Tensor"] | None = None,
        ) -> tuple["torch.Tensor", "torch.Tensor", "torch.Tensor", tuple]:
            B = view_tensor.shape[0]
            x = self.embed(view_tensor.clamp(0, NUM_TILES - 1).squeeze(1))
            x = x.permute(0, 3, 1, 2)
            feat = self.conv(x)
            feat = feat.unsqueeze(1)
            out, hid = self.lstm(feat, lstm_hidden)
            h = out.squeeze(1)
            logits = self.policy(h)
            value = self.value(h).squeeze(-1)
            belief_logits = self.belief(h)
            return logits, value, belief_logits, hid

    class PPOLSTMAgent:
        def __init__(self, checkpoint_path: str | Path | None = None, seed: int = 0) -> None:
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._model = PPOLSTMModule().to(self._device)
            self._lstm_h: tuple[torch.Tensor, torch.Tensor] | None = None
            if checkpoint_path:
                path = Path(checkpoint_path)
                if path.exists():
                    ckpt = torch.load(path, map_location=self._device, weights_only=True)
                    if "model" in ckpt:
                        self._model.load_state_dict(ckpt["model"])
                    else:
                        self._model.load_state_dict(ckpt)
            self._model.eval()
            self._rng = __import__("random").Random(seed)

        def _reset_lstm(self) -> None:
            self._lstm_h = None

        def act(self, obs: dict[str, Any], hazards: list[tuple[int, int]]) -> tuple[str, list[float]]:
            view = obs.get("view", [])
            if not view:
                move_actions = [a for a in ACTIONS if a in MOVES]
                return self._rng.choice(move_actions), [0.5] * len(hazards)
            view_t = _view_to_tensor(view).to(self._device)
            with torch.no_grad():
                logits, _, belief_logits, self._lstm_h = self._model(view_t, self._lstm_h)
                probs = torch.sigmoid(belief_logits[0, : len(hazards)]).cpu().tolist()
                action_probs = torch.softmax(logits[0], dim=0).cpu()
                action_idx = torch.multinomial(action_probs, 1).item()
            action = ID_ACTION.get(action_idx, "Move_N")
            return action, probs

        def update_belief(self, action: str, obs_new: dict[str, Any]) -> None:
            pass


def create_ppo_lstm_agent(checkpoint_path: str | Path | None = None, seed: int = 0):
    if not TORCH_AVAILABLE:
        raise RuntimeError("Install torch to use PPOLSTMAgent")
    return PPOLSTMAgent(checkpoint_path=checkpoint_path, seed=seed)
