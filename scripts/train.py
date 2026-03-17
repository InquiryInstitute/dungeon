#!/usr/bin/env python3
"""
Train PPO+LSTM agent on DWMB instances. Config-driven; saves checkpoints and logs.
Usage:
  python scripts/train.py --instances instances/train --steps 5000 --out runs/ppo
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dwmb.env import DWMBEnv
from dwmb.schema import DWMBInstance
from dwmb.validate import validate_instance


def load_instance(path: Path) -> DWMBInstance:
    with open(path) as f:
        data = json.load(f)
    return DWMBInstance.parse_json_compat(data)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, help="JSON config (optional)")
    p.add_argument("--instances", type=Path, default=Path("instances/train"), help="Dir of instance JSONs")
    p.add_argument("--steps", type=int, default=5000)
    p.add_argument("--out", type=Path, default=Path("runs/ppo"))
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--save-every", type=int, default=1000)
    args = p.parse_args()

    config = {}
    if args.config and args.config.exists():
        config = json.loads(args.config.read_text())
    instances_dir = Path(config.get("instances_dir", str(args.instances)))
    steps = config.get("steps", args.steps)
    out_dir = Path(config.get("out_dir", str(args.out)))
    out_dir.mkdir(parents=True, exist_ok=True)

    instance_paths = sorted(instances_dir.glob("*.json"))[:50]
    if not instance_paths:
        print("No instances in", instances_dir, file=sys.stderr)
        sys.exit(1)

    try:
        from dwmb.agents.ppo_lstm import (
            PPOLSTMModule,
            PPOLSTMAgent,
            _view_to_tensor,
            ID_ACTION,
        )
        import torch
        import torch.nn.functional as F
    except ImportError as e:
        print("PyTorch required:", e, file=sys.stderr)
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = PPOLSTMModule().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=config.get("lr", 3e-4))
    env = DWMBEnv(seed=args.seed)
    rng = __import__("random").Random(args.seed)
    log_metrics = []

    for step in range(steps):
        path = rng.choice(instance_paths)
        instance = load_instance(path)
        if validate_instance(instance):
            continue
        hazards = list(instance.eval.hazards_for_PIR)
        obs, _ = env.reset(instance, seed=args.seed + step)
        agent = PPOLSTMAgent(seed=args.seed + step)
        agent._model = model
        agent._model.train()
        agent._device = device
        agent._lstm_h = None

        views, actions, old_logprobs, rewards, vals, belief_labels = [], [], [], [], [], []
        for t in range(250):
            view = obs.get("view", [])
            if not view:
                break
            view_t = _view_to_tensor(view).to(device)
            with torch.no_grad():
                logits, value, belief_logits, agent._lstm_h = model(view_t, agent._lstm_h)
            probs = F.softmax(logits[0], dim=0)
            action_idx = torch.multinomial(probs, 1).item()
            old_lp = F.log_softmax(logits[0], dim=0)[action_idx].item()
            action = ID_ACTION.get(action_idx, "Move_N")

            views.append(view_t)
            actions.append(action_idx)
            old_logprobs.append(old_lp)
            vals.append(value[0].item())
            rewards.append(0.0)

            obs, reward, term, trunc, info = env.step(action)
            rewards[-1] = reward
            pos = tuple(info["position"])
            belief_labels.append([1.0 if pos == h and info.get("hazard_activated") else 0.0 for h in hazards])
            if term or trunc:
                break

        if len(rewards) < 2:
            continue

        returns = []
        R = 0
        for r in reversed(rewards):
            R = r + 0.99 * R
            returns.insert(0, R)
        returns_t = torch.tensor(returns, device=device, dtype=torch.float32)
        vals_t = torch.tensor(vals, device=device)
        adv = returns_t - vals_t
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)

        agent._lstm_h = None
        policy_loss_sum = 0.0
        value_loss_sum = 0.0
        belief_loss_sum = 0.0
        n = len(views)
        for i in range(n):
            logits, value, belief_logits, agent._lstm_h = model(views[i], agent._lstm_h)
            new_logprob = F.log_softmax(logits[0], dim=0)[actions[i]]
            ratio = (new_logprob - old_logprobs[i]).exp()
            surr1 = ratio * adv[i]
            surr2 = ratio.clamp(0.8, 1.2) * adv[i]
            policy_loss_sum = policy_loss_sum - torch.min(surr1, surr2)
            value_loss_sum = value_loss_sum + (value[0] - returns_t[i]).pow(2)
            if hazards:
                lb = torch.tensor(belief_labels[i], device=device, dtype=torch.float32)
                b = torch.sigmoid(belief_logits[0, : len(hazards)])
                belief_loss_sum = belief_loss_sum + F.binary_cross_entropy(b, lb)
        loss = (policy_loss_sum / n) + 0.5 * (value_loss_sum / n) + 0.1 * (belief_loss_sum / max(n, 1))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
        opt.step()

        log_metrics.append({"step": step, "ep_len": len(rewards), "return": sum(rewards)})
        if (step + 1) % args.save_every == 0:
            torch.save({"model": model.state_dict(), "step": step}, out_dir / f"ckpt_{step+1}.pt")
            (out_dir / "metrics.json").write_text(json.dumps(log_metrics, indent=2))
            print("Saved", step + 1)

    torch.save({"model": model.state_dict(), "step": steps}, out_dir / "ckpt_final.pt")
    (out_dir / "metrics.json").write_text(json.dumps(log_metrics, indent=2))
    print("Done.", out_dir)


if __name__ == "__main__":
    main()
