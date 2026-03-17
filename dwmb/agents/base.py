"""
Agent interface and belief-extraction convention for PIR.

Every agent used in evaluation must return (action, per_hazard_probs) from act():
- action: one of Move_N/S/E/W, Inspect, Interact, UseItem
- per_hazard_probs: list of float, length = len(hazards_for_PIR); probs[h] = p(hazard h is dangerous)

Belief-extraction convention (per report Metrics):
1. Belief-native agents: report marginal P(hazard) from internal belief or decoder.
2. Model-free / MuZero-like: add an auxiliary belief head (BCE/log loss) on hazard presence; head output = p_t(h).
3. Dreamer/RSSM: decoder or auxiliary head from z_t to per-tile hazard probability.
4. LLM agents: extract or prompt for numerical probability per eval hazard each step; log it.

Evaluation uses only these logged values; agents that do not provide them get no PIR score.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DWMBAgent(Protocol):
    """Agent that acts in DWMB and reports per-hazard beliefs for PIR."""

    def act(self, obs: dict[str, Any], hazards: list[tuple[int, int]]) -> tuple[str, list[float]]:
        """
        Return (action, probs).
        - action: string action name.
        - probs: list of length len(hazards); probs[i] = P(hazard at hazards[i] is dangerous).
        """
        ...

    def update_belief(self, action: str, obs_new: dict[str, Any]) -> None:
        """Optional: update internal state after step (for stateful agents). Default no-op."""
        ...


def make_agent(name: str, **kwargs: Any) -> DWMBAgent:
    """Factory: random, heuristic, ppo_lstm, jepa (optional checkpoint; jepa supports ablation flags)."""
    if name == "random":
        from dwmb.agents.random_agent import RandomAgent
        return RandomAgent(seed=kwargs.get("seed", 0))
    if name == "heuristic":
        from dwmb.agents.heuristic_agent import HeuristicAgent
        return HeuristicAgent(seed=kwargs.get("seed", 0))
    if name == "ppo_lstm":
        from dwmb.agents.ppo_lstm import PPOLSTMAgent
        return PPOLSTMAgent(checkpoint_path=kwargs.get("checkpoint_path"), seed=kwargs.get("seed", 0))
    if name == "jepa":
        from dwmb.agents.jepa_agent import JEPAAgent
        return JEPAAgent(
            checkpoint_path=kwargs.get("checkpoint_path"),
            seed=kwargs.get("seed", 0),
            use_predictor=kwargs.get("use_predictor", True),
            use_belief_loss=kwargs.get("use_belief_loss", True),
        )
    raise ValueError(f"Unknown agent: {name}")
