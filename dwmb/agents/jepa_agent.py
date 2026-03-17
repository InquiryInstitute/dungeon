"""
JEPA-style agent: encoder → context RNN → predictor + belief head + planner.
Per report: E_φ(o) → y_t (token embeddings), C_ψ aggregates → z_t, P_ω predicts masked embeddings,
D(z_t, pos) → p(hazard), planner uses predictor for action selection.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from dwmb.env import ACTIONS
from dwmb.agents.ppo_lstm import VIEW_SIZE, ID_ACTION, ACTION_IDS, _view_to_tensor

NUM_TILES = 5
NUM_POSITIONS = VIEW_SIZE * VIEW_SIZE  # 25
EMBED_DIM = 16
Z_DIM = 64
ACTION_DIM = 8
MAX_HAZARDS = 8


class JEPAModule(nn.Module):
    """Encoder → Context RNN → Predictor, Prior, Belief head, Policy head."""

    def __init__(
        self,
        z_dim: int = Z_DIM,
        embed_dim: int = EMBED_DIM,
        use_predictor: bool = True,
        use_belief_loss: bool = True,
    ) -> None:
        super().__init__()
        self.z_dim = z_dim
        self.embed_dim = embed_dim
        self.use_predictor = use_predictor
        self.use_belief_loss = use_belief_loss

        self.encoder = nn.Embedding(NUM_TILES, embed_dim)
        self.action_embed = nn.Embedding(len(ACTIONS) + 1, ACTION_DIM)
        rnn_input = NUM_POSITIONS * embed_dim + ACTION_DIM
        self.context_rnn = nn.GRU(rnn_input, z_dim, batch_first=True)
        self.predictor = nn.Sequential(
            nn.Linear(z_dim, z_dim),
            nn.ReLU(),
            nn.Linear(z_dim, NUM_POSITIONS * embed_dim),
        ) if use_predictor else None
        self.prior_net = nn.Sequential(
            nn.Linear(z_dim + ACTION_DIM, z_dim),
            nn.ReLU(),
            nn.Linear(z_dim, z_dim),
        )
        self.belief_head = nn.Sequential(
            nn.Linear(z_dim + 2, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )
        self.policy_head = nn.Linear(z_dim, len(ACTIONS))

    def encode_view(self, view_tensor: "torch.Tensor") -> "torch.Tensor":
        B = view_tensor.shape[0]
        x = self.encoder(view_tensor.clamp(0, NUM_TILES - 1))
        return x.view(B, NUM_POSITIONS, -1)

    def forward(
        self,
        view_tensor: "torch.Tensor",
        prev_action: int,
        z_prev: "torch.Tensor | None" = None,
        h_prev: "torch.Tensor | None" = None,
    ) -> dict[str, "torch.Tensor"]:
        B = view_tensor.shape[0]
        y = self.encode_view(view_tensor)
        y_flat = y.view(B, -1)
        a_emb = self.action_embed(torch.tensor([prev_action], device=view_tensor.device)).expand(B, -1)
        rnn_in = torch.cat([y_flat, a_emb], dim=1).unsqueeze(1)
        if h_prev is None:
            z, h = self.context_rnn(rnn_in)
        else:
            z, h = self.context_rnn(rnn_in, h_prev)
        z_t = z.squeeze(1)

        out = {"z": z_t, "h": h, "y": y}
        if self.predictor is not None:
            pred_flat = self.predictor(z_t)
            out["y_pred"] = pred_flat.view(B, NUM_POSITIONS, self.embed_dim)
        z_a = torch.cat([z_t, a_emb], dim=1)
        out["z_prior_next"] = self.prior_net(z_a)
        out["action_logits"] = self.policy_head(z_t)
        return out

    def belief_for_hazards(self, z: "torch.Tensor", hazards: list[tuple[int, int]], agent_pos: tuple[int, int]) -> "torch.Tensor":
        """D(z, pos) → p(hazard dangerous). pos in world coords; normalize relative to agent."""
        B = z.shape[0]
        probs = []
        for (r, c) in hazards:
            dr = (r - agent_pos[0]) / 20.0
            dc = (c - agent_pos[1]) / 20.0
            pos_feat = torch.tensor([[dr, dc]], device=z.device, dtype=z.dtype).expand(B, 2)
            inp = torch.cat([z, pos_feat], dim=1)
            logit = self.belief_head(inp).squeeze(-1)
            probs.append(logit.sigmoid())
        return torch.stack(probs, dim=1) if probs else z.new_zeros(B, 0)


class JEPAAgent:
    """JEPA-style agent; same act(obs, hazards) interface; optional checkpoint and ablation flags."""

    def __init__(
        self,
        checkpoint_path: str | Path | None = None,
        seed: int = 0,
        use_predictor: bool = True,
        use_belief_loss: bool = True,
    ) -> None:
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch required for JEPAAgent")
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model = JEPAModule(use_predictor=use_predictor, use_belief_loss=use_belief_loss).to(self._device)
        if checkpoint_path:
            path = Path(checkpoint_path)
            if path.exists():
                ckpt = torch.load(path, map_location=self._device, weights_only=True)
                if "model" in ckpt:
                    self._model.load_state_dict(ckpt["model"])
                else:
                    self._model.load_state_dict(ckpt)
        self._model.eval()
        self._prev_action = len(ACTIONS)
        self._h_prev: Any = None
        self._rng = __import__("random").Random(seed)

    def _reset(self) -> None:
        self._prev_action = len(ACTIONS)
        self._h_prev = None

    def act(self, obs: dict[str, Any], hazards: list[tuple[int, int]]) -> tuple[str, list[float]]:
        view = obs.get("view", [])
        pos = tuple(obs.get("position", [0, 0]))
        if not view:
            from dwmb.env import MOVES
            move_actions = [a for a in ACTIONS if a in MOVES]
            return self._rng.choice(move_actions), [0.5] * len(hazards)
        view_t = _view_to_tensor(view).to(self._device)
        with torch.no_grad():
            out = self._model(view_t, self._prev_action, h_prev=self._h_prev)
            self._h_prev = out["h"]
            belief_probs = self._model.belief_for_hazards(out["z"], hazards, pos)
            probs = belief_probs[0].cpu().tolist() if belief_probs.shape[1] else [0.5] * len(hazards)
            logits = out["action_logits"][0]
            action_idx = torch.argmax(logits).item()
            action = ID_ACTION.get(action_idx, "Move_N")
        self._prev_action = ACTION_IDS.get(action, 0)
        return action, probs

    def update_belief(self, action: str, obs_new: dict[str, Any]) -> None:
        self._prev_action = ACTION_IDS.get(action, 0)
