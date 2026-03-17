#!/usr/bin/env python3
"""
Evaluate an agent on a DWMB instance: run episode, log beliefs, compute PIR and other metrics.
Usage:
  python scripts/evaluate.py instances/unit_test/worked_example_16x16.json
  python scripts/evaluate.py instances/unit_test/worked_example_16x16.json --agent random --seed 42
  python scripts/evaluate.py instances/unit_test/worked_example_16x16.json --sync  # store run in Supabase
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dwmb.runner import run_episode
from dwmb.schema import DWMBInstance
from dwmb.validate import validate_instance


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluate agent on DWMB instance")
    p.add_argument("instance_path", type=Path, help="Path to instance JSON")
    p.add_argument("--agent", default="random", choices=["random", "heuristic", "ppo_lstm", "jepa"], help="Agent type")
    p.add_argument("--checkpoint", type=Path, help="Checkpoint for ppo_lstm agent")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-steps", type=int, default=500)
    p.add_argument("--sync", action="store_true", help="Store run and metrics in Supabase")
    p.add_argument("--out", type=Path, help="Write metrics JSON here")
    args = p.parse_args()

    with open(args.instance_path) as f:
        data = json.load(f)
    instance = DWMBInstance.parse_json_compat(data)

    errs = validate_instance(instance)
    if errs:
        print("Validation errors:", errs, file=sys.stderr)
        sys.exit(1)

    from dwmb.agents.base import make_agent
    agent = make_agent(
        args.agent,
        seed=args.seed,
        checkpoint_path=args.checkpoint,
    )
    metrics, trajectory, belief_log, hazard_activations = run_episode(
        instance, agent, seed=args.seed, max_steps=args.max_steps
    )

    print("Metrics:", json.dumps(metrics, indent=2))
    if args.out:
        args.out.write_text(json.dumps({"metrics": metrics, "steps": len(trajectory)}, indent=2))

    if args.sync:
        from dwmb.storage import get_client, insert_metrics, insert_run, upsert_instance
        from dwmb.validate import infer_tier

        client = get_client()
        if not client:
            print("Supabase not configured; skip sync.", file=sys.stderr)
        else:
            instance_id = args.instance_path.stem
            tier = infer_tier(instance)
            row_id = upsert_instance(instance_id, tier, "unit_test", instance.model_dump_json_tuples())
            if row_id:
                run_id = insert_run(
                    row_id,
                    args.agent,
                    args.seed,
                    trajectory=trajectory,
                    belief_log=belief_log,
                    goal_reached=metrics["goal_reached"],
                    died=metrics["died"],
                    hazard_activations=[list(p) for p in hazard_activations],
                    steps=metrics["steps"],
                )
                if run_id:
                    insert_metrics(
                        run_id,
                        pir_delta=metrics.get("PIR_0.9"),
                        goal_success=metrics["goal_reached"],
                        survival=not metrics["died"],
                        hazard_count=metrics["hazard_activations"],
                    )
                    print("Synced run to Supabase.")
            else:
                print("Failed to upsert instance.", file=sys.stderr)


if __name__ == "__main__":
    main()
