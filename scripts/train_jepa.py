#!/usr/bin/env python3
"""
Train JEPA-style agent: latent prediction loss (mask-and-predict) + belief consistency (prior vs inference).
Usage:
  python scripts/train_jepa.py --instances instances/train --steps 3000 --out runs/jepa
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
from dwmb.agents.jepa_agent import JEPAModule, ACTION_IDS
from dwmb.agents.ppo_lstm import _view_to_tensor

import torch
import torch.nn.functional as F


def load_instance(path: Path) -> DWMBInstance:
    with open(path) as f:
        data = json.load(f)
    return DWMBInstance.parse_json_compat(data)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--instances", type=Path, default=Path("instances/train"))
    p.add_argument("--steps", type=int, default=3000)
    p.add_argument("--out", type=Path, default=Path("runs/jepa"))
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--save-every", type=int, default=1000)
    p.add_argument("--no-predictor", action="store_true", help="Ablation: disable predictor loss")
    p.add_argument("--no-belief-loss", action="store_true", help="Ablation: disable belief consistency loss")
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    paths = sorted(args.instances.glob("*.json"))
    if not paths:
        paths = sorted(args.instances.glob("*.json"))
    paths = paths[:40]
    if not paths:
        print("No instances", file=sys.stderr)
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = JEPAModule(
        use_predictor=not args.no_predictor,
        use_belief_loss=not args.no_belief_loss,
    ).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    env = DWMBEnv(seed=args.seed)
    rng = __import__("random").Random(args.seed)
    log_metrics = []

    for step in range(args.steps):
        path = rng.choice(paths)
        instance = load_instance(path)
        if validate_instance(instance):
            continue
        hazards = list(instance.eval.hazards_for_PIR)
        obs, _ = env.reset(instance, seed=args.seed + step)
        prev_action = len(ACTION_IDS)
        h_prev = None
        z_prior_prev = None
        ep_loss = 0.0
        n_steps = 0
        for t in range(150):
            view = obs.get("view", [])
            if not view:
                break
            view_t = _view_to_tensor(view).to(device)
            pos = tuple(obs.get("position", [0, 0]))
            out = model(view_t, prev_action, h_prev=h_prev)
            y = out["y"]
            z = out["z"]
            h_prev = out["h"]
            loss = torch.tensor(0.0, device=device)

            if model.predictor is not None and out.get("y_pred") is not None:
                y_pred = out["y_pred"]
                mask_size = max(1, y.shape[1] // 4)
                mask_idx = torch.randperm(y.shape[1], device=device)[:mask_size]
                y_masked = y[:, mask_idx]
                pred_masked = y_pred[:, mask_idx]
                loss_pred = F.mse_loss(pred_masked, y_masked.detach())
                loss = loss + loss_pred

            if model.use_belief_loss and z_prior_prev is not None:
                loss_consist = F.mse_loss(z, z_prior_prev)
                loss = loss + 0.1 * loss_consist
            z_prior_prev = out["z_prior_next"]

            if hazards:
                belief_probs = model.belief_for_hazards(z, hazards, pos)
                labels = torch.tensor(
                    [1.0 if pos == h else 0.0 for h in hazards],
                    device=device, dtype=torch.float32,
                ).unsqueeze(0)
                loss_belief = F.binary_cross_entropy(belief_probs, labels.expand_as(belief_probs))
                loss = loss + 0.2 * loss_belief

            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            ep_loss += loss.item()
            n_steps += 1

            action_logits = out["action_logits"]
            action_idx = torch.argmax(action_logits[0]).item()
            from dwmb.agents.ppo_lstm import ID_ACTION
            action = ID_ACTION.get(action_idx, "Move_N")
            obs, reward, term, trunc, info = env.step(action)
            prev_action = ACTION_IDS.get(action, 0)
            if term or trunc:
                break

        log_metrics.append({"step": step, "ep_steps": n_steps, "loss": ep_loss / max(n_steps, 1)})
        if (step + 1) % args.save_every == 0:
            torch.save({"model": model.state_dict(), "step": step}, args.out / f"ckpt_{step+1}.pt")
            (args.out / "metrics.json").write_text(json.dumps(log_metrics, indent=2))
            print("Saved", step + 1)

    torch.save({"model": model.state_dict(), "step": args.steps}, args.out / "ckpt_final.pt")
    (args.out / "metrics.json").write_text(json.dumps(log_metrics, indent=2))
    print("Done.", args.out)


if __name__ == "__main__":
    main()
