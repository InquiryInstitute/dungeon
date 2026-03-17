#!/usr/bin/env python3
"""
Run evaluation on a set of instances (manifest or directory) and aggregate metrics.
Usage:
  python scripts/evaluate_batch.py instances/test --agent random --seeds 5 --out results.json
  python scripts/evaluate_batch.py instances/seeds_manifest.json --manifest test --agent heuristic
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dwmb.schema import DWMBInstance
from dwmb.validate import validate_instance
from dwmb.runner import run_episode


def load_instance(path: Path) -> DWMBInstance:
    with open(path) as f:
        data = json.load(f)
    return DWMBInstance.parse_json_compat(data)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path, help="Directory of instance JSONs or seeds_manifest.json")
    p.add_argument("--manifest", choices=["train", "test"], help="If source is manifest, which split to run")
    p.add_argument("--agent", default="random", choices=["random", "heuristic", "ppo_lstm", "jepa"])
    p.add_argument("--seeds", type=int, default=3, help="Seeds per instance")
    p.add_argument("--max-steps", type=int, default=500)
    p.add_argument("--checkpoint", type=Path, help="For ppo_lstm")
    p.add_argument("--out", type=Path, help="Write aggregated metrics JSON here")
    args = p.parse_args()

    if args.source.is_file() and args.source.name == "seeds_manifest.json":
        manifest = json.loads(args.source.read_text())
        key = args.manifest or "test"
        entries = manifest.get(key, [])
        instance_dir = args.source.parent / key
        paths = [instance_dir / f"t{e['tier']}_{key}_{e['seed']}.json" for e in entries]
        paths = [p for p in paths if p.exists()]
    else:
        paths = sorted(args.source.glob("*.json"))
    if not paths:
        print("No instances found", file=sys.stderr)
        sys.exit(1)

    from dwmb.agents.base import make_agent

    all_metrics = []
    for path in paths:
        try:
            instance = load_instance(path)
        except Exception as e:
            print(path, e, file=sys.stderr)
            continue
        if validate_instance(instance):
            continue
        for seed in range(args.seeds):
            agent = make_agent(args.agent, seed=seed, checkpoint_path=args.checkpoint)
            metrics, _, _, _ = run_episode(instance, agent, seed=seed, max_steps=args.max_steps)
            metrics["instance"] = path.stem
            metrics["seed"] = seed
            all_metrics.append(metrics)

    if not all_metrics:
        print("No runs", file=sys.stderr)
        sys.exit(1)

    agg = {
        "n_runs": len(all_metrics),
        "goal_reached_mean": sum(m["goal_reached"] for m in all_metrics) / len(all_metrics),
        "died_mean": sum(m["died"] for m in all_metrics) / len(all_metrics),
        "hazard_activations_mean": sum(m["hazard_activations"] for m in all_metrics) / len(all_metrics),
        "steps_mean": sum(m["steps"] for m in all_metrics) / len(all_metrics),
        "PIR_0.5_mean": sum(m["PIR_0.5"] for m in all_metrics) / len(all_metrics),
        "PIR_0.7_mean": sum(m["PIR_0.7"] for m in all_metrics) / len(all_metrics),
        "PIR_0.9_mean": sum(m["PIR_0.9"] for m in all_metrics) / len(all_metrics),
    }
    out = {"aggregate": agg, "runs": all_metrics}
    print(json.dumps(agg, indent=2))
    if args.out:
        args.out.write_text(json.dumps(out, indent=2))
        print("Wrote", args.out)


if __name__ == "__main__":
    main()
