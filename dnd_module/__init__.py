"""
D&D Module Generator — Tomb of Horrors framework.
Generates procedural dungeons with maps, traps, clues, and keyed areas.
"""
from .framework import FrameworkConfig
from .generator import generate_module
from .schema import (
    GeneratedModule,
    KeyedArea,
    DungeonMap,
    Trap,
    TrapKind,
    Clue,
    Legend,
)

__all__ = [
    "FrameworkConfig",
    "generate_module",
    "GeneratedModule",
    "KeyedArea",
    "DungeonMap",
    "Trap",
    "TrapKind",
    "Clue",
    "Legend",
]
