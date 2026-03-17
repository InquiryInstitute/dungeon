"""
Export generated module to JSON, ASCII map, and Markdown key.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import GeneratedModule, MapCell, KeyedArea, TrapKind

WALL = "#"
FLOOR = "."
DOOR = "D"
SECRET = "S"
ENTRANCE = "E"
GOAL = "G"


def module_to_json(module: GeneratedModule) -> dict[str, Any]:
    """Serialize to JSON-suitable dict (tuples as lists, map by alias)."""
    data = module.model_dump(mode="json", by_alias=True)
    # Convert eval_hazards tuples to lists
    if "eval_hazards" in data and data["eval_hazards"]:
        data["eval_hazards"] = [list(h) for h in data["eval_hazards"]]
    return data


def write_json(module: GeneratedModule, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = module_to_json(module)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def map_to_ascii(module: GeneratedModule) -> str:
    """Render the dungeon map as ASCII (.#DSEG)."""
    m = module.map
    grid = [[None] * m.width for _ in range(m.height)]
    for cell in m.cells:
        if 0 <= cell.row < m.height and 0 <= cell.col < m.width:
            grid[cell.row][cell.col] = cell.cell_type
    lines = []
    for row in grid:
        line = "".join(c or WALL for c in row)
        lines.append(line)
    return "\n".join(lines)


def write_ascii_map(module: GeneratedModule, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ascii_map = map_to_ascii(module)
    legend = "\n# = wall  . = floor  E = entrance  G = goal\n"
    with open(path, "w") as f:
        f.write(module.title + "\n\n")
        f.write(ascii_map)
        f.write(legend)


def key_to_markdown(module: GeneratedModule) -> str:
    """Generate a DM-style key in Markdown."""
    lines = [
        f"# {module.title}",
        "",
        "## Legend",
        "",
        module.legend.backstory,
        "",
        "### Possible locales",
        *[f"- {loc}" for loc in module.legend.locale_options],
        "",
        "### DM notes",
        module.legend.dm_notes,
        "",
        "---",
        "",
        "## Keyed Areas",
        "",
    ]
    for area in module.areas:
        lines.append(f"### {area.id}: {area.name}")
        lines.append("")
        lines.append(f"**Type:** {area.room_type.value}")
        lines.append("")
        lines.append(area.description)
        lines.append("")
        if area.doors:
            lines.append("**Doors:**")
            for d in area.doors:
                lines.append(f"- {d.door_type.value}" + (f" → {d.leads_to_area}" if d.leads_to_area else ""))
            lines.append("")
        if area.traps:
            lines.append("**Traps:**")
            for t in area.traps:
                lines.append(f"- {t.kind.value} at ({t.position.row},{t.position.col}): {t.damage or 'see description'}")
            lines.append("")
        if area.switches:
            lines.append("**Switches:**")
            for s in area.switches:
                lines.append(f"- {s.id}: {s.description}")
            lines.append("")
        if area.clues:
            lines.append("**Clues:**")
            for c in area.clues:
                lines.append(f"- \"{c.text[:80]}...\"" if len(c.text) > 80 else f"- \"{c.text}\"")
            lines.append("")
        lines.append("---")
        lines.append("")
    lines.append("## Traps (summary)")
    for t in module.traps:
        lines.append(f"- **{t.kind.value}** at ({t.position.row},{t.position.col}) — {t.damage or 'various'}")
    lines.append("")
    lines.append("## Clues (summary)")
    for c in module.clues:
        lines.append(f"- {c.text[:100]}...")
    return "\n".join(lines)


def write_markdown_key(module: GeneratedModule, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(key_to_markdown(module))
