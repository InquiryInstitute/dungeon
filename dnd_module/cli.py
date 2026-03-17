#!/usr/bin/env python3
"""
CLI for the D&D Tomb of Horrors-style module generator.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .framework import FrameworkConfig
from .generator import generate_module
from .export import write_json, write_ascii_map, write_markdown_key


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Tomb of Horrors-style D&D module (map, traps, clues, keyed areas)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible generation",
    )
    parser.add_argument(
        "--title",
        type=str,
        default="Generated Tomb of Horrors",
        help="Module title",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=32,
        help="Map width (default 32)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=24,
        help="Map height (default 24)",
    )
    parser.add_argument(
        "--min-rooms",
        type=int,
        default=8,
        help="Minimum number of rooms (default 8)",
    )
    parser.add_argument(
        "--max-rooms",
        type=int,
        default=20,
        help="Maximum number of rooms (default 20)",
    )
    parser.add_argument(
        "--trap-density",
        type=float,
        default=0.35,
        help="Fraction of non-entrance/goal areas that have traps (default 0.35)",
    )
    parser.add_argument(
        "--clue-density",
        type=float,
        default=0.25,
        help="Fraction of areas that contain clues (default 0.25)",
    )
    parser.add_argument(
        "--no-switches",
        action="store_true",
        help="Disable switches that disarm distant traps",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="generated_module",
        help="Output base path (default: generated_module)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=True,
        help="Write JSON module (default on)",
    )
    parser.add_argument(
        "--no-json",
        action="store_false",
        dest="json",
        help="Do not write JSON",
    )
    parser.add_argument(
        "--map",
        action="store_true",
        help="Write ASCII map file",
    )
    parser.add_argument(
        "--key",
        action="store_true",
        help="Write Markdown DM key",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Write JSON, ASCII map, and Markdown key",
    )
    args = parser.parse_args()

    config = FrameworkConfig(
        title=args.title,
        grid_height=args.height,
        grid_width=args.width,
        min_rooms=args.min_rooms,
        max_rooms=args.max_rooms,
        trap_density=args.trap_density,
        clue_density=args.clue_density,
        use_switches=not args.no_switches,
        seed=args.seed,
    )
    module = generate_module(config)

    base = Path(args.output)
    write_json_flag = args.json or args.all
    write_map_flag = args.map or args.all
    write_key_flag = args.key or args.all

    if write_json_flag:
        write_json(module, base.with_suffix(".json"))
        print(f"Wrote {base.with_suffix('.json')}")
    if write_map_flag:
        map_path = base.parent / f"{base.name}_map.txt"
        write_ascii_map(module, map_path)
        print(f"Wrote {map_path}")
    if write_key_flag:
        key_path = base.parent / f"{base.name}_key.md"
        write_markdown_key(module, key_path)
        print(f"Wrote {key_path}")

    if not (write_json_flag or write_map_flag or write_key_flag):
        print("No output format selected. Use --json, --map, --key, or --all.")
        return 1
    print(f"Generated: {len(module.areas)} areas, {len(module.traps)} traps, {len(module.clues)} clues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
