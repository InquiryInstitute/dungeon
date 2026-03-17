#!/usr/bin/env python3
"""
Generate DWMB train/test/counterfactual splits and write instance JSONs.
Usage:
  python scripts/generate_splits.py --out instances
  python scripts/generate_splits.py --out instances --train-per-tier 10 --test-per-tier 5
  python scripts/generate_splits.py --out instances --tiers 1 2 3
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dwmb.generator import generate, generate_counterfactual
from dwmb.schema import DWMBInstance
from dwmb.validate import validate_instance


def main() -> None:
    p = argparse.ArgumentParser(description="Generate DWMB instance splits")
    p.add_argument("--out", type=Path, default=Path("instances"), help="Output directory")
    p.add_argument("--tiers", type=int, nargs="+", default=[1, 2, 3, 4, 5], help="Tiers to generate")
    p.add_argument("--train-per-tier", type=int, default=50, help="Train instances per tier")
    p.add_argument("--test-per-tier", type=int, default=20, help="Test instances per tier")
    p.add_argument("--train-seed-start", type=int, default=10000, help="First seed for train")
    p.add_argument("--test-seed-start", type=int, default=20000, help="First seed for test")
    p.add_argument("--counterfactual-per-test", type=int, default=2, help="Counterfactual variants per test instance")
    args = p.parse_args()

    out = args.out
    (out / "train").mkdir(parents=True, exist_ok=True)
    (out / "test").mkdir(parents=True, exist_ok=True)
    (out / "counterfactual").mkdir(parents=True, exist_ok=True)

    train_seeds: list[tuple[int, int]] = []
    test_seeds: list[tuple[int, int]] = []

    for tier in args.tiers:
        for i in range(args.train_per_tier):
            seed = args.train_seed_start + tier * 1000 + i
            inst = generate(seed, tier)
            errs = validate_instance(inst)
            if errs:
                print(f"Warn tier={tier} seed={seed}: {errs}", file=sys.stderr)
            name = f"t{tier}_train_{seed}"
            path = out / "train" / f"{name}.json"
            path.write_text(json.dumps(inst.model_dump_json_tuples(), indent=2))
            train_seeds.append((tier, seed))

        for i in range(args.test_per_tier):
            seed = args.test_seed_start + tier * 1000 + i
            inst = generate(seed, tier)
            errs = validate_instance(inst)
            if errs:
                print(f"Warn tier={tier} seed={seed}: {errs}", file=sys.stderr)
            name = f"t{tier}_test_{seed}"
            path = out / "test" / f"{name}.json"
            path.write_text(json.dumps(inst.model_dump_json_tuples(), indent=2))
            test_seeds.append((tier, seed))

            for cf_idx in range(args.counterfactual_per_test):
                cf_seed = seed * 1000 + cf_idx
                cf_inst = generate_counterfactual(inst, cf_seed)
                cf_name = f"t{tier}_test_{seed}_cf{cf_idx}"
                cf_path = out / "counterfactual" / f"{cf_name}.json"
                cf_path.write_text(json.dumps(cf_inst.model_dump_json_tuples(), indent=2))

    seeds_manifest = {
        "train": [{"tier": t, "seed": s} for t, s in train_seeds],
        "test": [{"tier": t, "seed": s} for t, s in test_seeds],
    }
    (out / "seeds_manifest.json").write_text(json.dumps(seeds_manifest, indent=2))
    print(f"Generated: train {len(train_seeds)}, test {len(test_seeds)}, counterfactual {len(test_seeds) * args.counterfactual_per_test}")
    print(f"Manifest: {out / 'seeds_manifest.json'}")


if __name__ == "__main__":
    main()
