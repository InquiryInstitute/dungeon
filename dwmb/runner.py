"""Run episodes and compute PIR/metrics; used by evaluate.py and evaluate_batch.py."""
from __future__ import annotations

from dwmb.env import DWMBEnv
from dwmb.schema import DWMBInstance


def run_episode(
    instance: DWMBInstance,
    agent,
    seed: int = 0,
    max_steps: int = 500,
) -> tuple[dict, list[dict], list[list[float]], list]:
    """
    Run one episode. Returns (metrics_dict, trajectory, belief_log, hazard_activations).
    belief_log[t][h] = agent's p(hazard h dangerous) at step t before acting.
    """
    env = DWMBEnv(seed=seed)
    obs, info = env.reset(instance, seed=seed)
    hazards = list(instance.eval.hazards_for_PIR)
    trajectory = []
    belief_log = []

    for _ in range(max_steps):
        action, probs = agent.act(obs, hazards)
        belief_log.append(probs)
        obs_new, reward, term, trunc, info = env.step(action)
        if hasattr(agent, "update_belief"):
            agent.update_belief(action, obs_new)
        trajectory.append({
            "action": action,
            "reward": reward,
            "position": info["position"],
            "event": info["event"],
            "hazard_activated": info.get("hazard_activated"),
            "goal_reached": info.get("goal_reached", False),
            "died": info.get("died", False),
        })
        obs = obs_new
        if term or trunc:
            break

    first_visit: dict[tuple[int, int], int] = {}
    for i, tr in enumerate(trajectory):
        pos = tuple(tr["position"])
        for h in hazards:
            if h not in first_visit and pos == h:
                first_visit[h] = i
    deltas = [0.5, 0.7, 0.9]
    pir = {}
    for delta in deltas:
        count = 0
        for h in hazards:
            tau = first_visit.get(h)
            if tau is None:
                count += 1
                continue
            if tau == 0:
                continue
            idx = hazards.index(h)
            if idx < len(belief_log[tau - 1]) and belief_log[tau - 1][idx] >= delta:
                count += 1
        pir[f"PIR_{delta}"] = count / len(hazards) if hazards else 0.0

    metrics = {
        "goal_reached": trajectory[-1].get("goal_reached", False) if trajectory else False,
        "died": any(tr.get("died") for tr in trajectory),
        "steps": len(trajectory),
        "hazard_activations": len(env.hazard_activations),
        **pir,
    }
    return metrics, trajectory, belief_log, env.hazard_activations
