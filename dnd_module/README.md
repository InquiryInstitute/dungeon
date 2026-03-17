# D&D Module Generator — Tomb of Horrors Framework

Procedural generator for **Tomb of Horrors–style** D&D modules: maps, keyed areas, traps, clues, and switches.

## Features

- **Map**: Procedural dungeon layout (rooms + corridors) with entrance and goal.
- **Traps**: Pit, sliding block, spear, gas, crushing, teleport, curse, sphere-of-annihilation style, spike volley, tilting floor, magic mouth, etc.
- **Clues**: Riddle- and inscription-style clues that hint at areas or actions.
- **Switches**: Optional levers/studs that disarm distant traps (non-local causality).
- **Doors**: Closed, secret, and false doors between areas.
- **Room types**: Entrance, corridor, hall, chamber, prison, chapel, throne room, crypt, treasure room, trap room, puzzle room, dead end.

## Quick start

```bash
# From repo root with venv activated
python -m dnd_module.cli --seed 42 --all -o my_tomb
```

Produces:

- `my_tomb.json` — full module (map, areas, traps, switches, clues).
- `my_tomb_map.txt` — ASCII map (`#` wall, `.` floor, `E` entrance, `G` goal).
- `my_tomb_key.md` — DM key in Markdown (legend, keyed areas, trap/clue summaries).

## Options

- `--seed N` — reproducible generation.
- `--title "My Dungeon"` — module title.
- `--width / --height` — map size (default 32×24).
- `--min-rooms / --max-rooms` — room count range (default 8–20).
- `--trap-density` — fraction of areas with traps (default 0.35).
- `--clue-density` — fraction of areas with clues (default 0.25).
- `--no-switches` — disable disarm switches.
- `--json`, `--map`, `--key` — output only selected formats; `--all` enables all.

## Programmatic use

```python
from dnd_module import generate_module
from dnd_module.framework import FrameworkConfig
from dnd_module.export import write_json, write_ascii_map, write_markdown_key

config = FrameworkConfig(
    title="My Tomb",
    seed=42,
    grid_height=20,
    grid_width=30,
    min_rooms=10,
    max_rooms=18,
    trap_density=0.4,
    clue_density=0.3,
    use_switches=True,
)
module = generate_module(config)

write_json(module, "my_tomb.json")
write_ascii_map(module, "my_tomb_map.txt")
write_markdown_key(module, "my_tomb_key.md")
```

## Schema (high level)

- **GeneratedModule**: `version`, `title`, `legend`, `map`, `areas`, `traps`, `switches`, `clues`, `eval_hazards`.
- **DungeonMap**: `height`, `width`, `cells` (row, col, cell_type, optional area_id).
- **KeyedArea**: `id`, `position`, `room_type`, `name`, `description`, `doors`, `traps`, `switches`, `clues`, `connections`.
- **Trap**: `position`, `kind`, `armed`, `disarm_switch_id`, `damage`, `save`, `description`.
- **Clue**: `area_id`, `format`, `text`, `hints_at`.

Design is inspired by the classic *Tomb of Horrors* module: deadly traps, false and secret doors, cryptic clues, and non-local switch–trap links.
