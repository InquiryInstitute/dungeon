# DWMB Agents & Belief-Extraction Convention

## Interface

Every agent must implement:

- **`act(obs, hazards) -> (action, probs)`**  
  - `action`: one of `Move_N`, `Move_S`, `Move_E`, `Move_W`, `Inspect`, `Interact`, `UseItem`.  
  - `probs`: list of length `len(hazards)`; `probs[i]` = P(hazard at `hazards[i]` is dangerous).

- **`update_belief(action, obs_new)`** (optional)  
  Update internal state after env step (e.g. visited set, LSTM state).

Evaluation uses only these logged per-hazard probabilities to compute PIR. Agents that do not provide them receive no PIR score.

## Belief-extraction convention (per report)

1. **Belief-native**  
   Report marginal P(hazard) from the agent’s internal belief or decoder.

2. **Model-free / MuZero-like**  
   Add an auxiliary **belief head** trained with BCE or log loss to predict hazard presence from the same features as the policy; that head’s output is used as `probs`.

3. **Dreamer/RSSM**  
   Use a decoder or auxiliary head from latent state `z_t` to per-tile hazard probability; do not use value at the tile as a proxy for belief.

4. **LLM agents**  
   Extract or prompt for a numerical probability per eval hazard at each step and log it.

## Built-in agents

- **random** – Random move; uniform 0.5 per hazard.
- **heuristic** – Higher belief for unvisited hazard tiles; random move.
- **ppo_lstm** – Small CNN+LSTM+policy/value/belief head; optional checkpoint. Requires `torch`.
- **jepa** – Encoder → context RNN → predictor + belief head + policy; optional checkpoint. Requires `torch`. Ablation: `use_predictor=False` or `use_belief_loss=False` (via factory kwargs).

## Factory

```python
from dwmb.agents.base import make_agent

agent = make_agent("heuristic", seed=42)
action, probs = agent.act(obs, hazards)
```
