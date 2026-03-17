"""
Validate DWMB instances and tier constraints.
"""
from __future__ import annotations

from dwmb.schema import DWMBInstance, Eval, HiddenState


def validate_instance(inst: DWMBInstance) -> list[str]:
    """Return list of validation errors (empty if valid)."""
    errs: list[str] = []
    g = inst.grid
    h, w = g.height, g.width
    entities = inst.entities
    hidden = inst.hidden_state

    def in_bounds(r: int, c: int) -> bool:
        return 0 <= r < h and 0 <= c < w

    if not in_bounds(*entities.agent_start):
        errs.append("agent_start out of grid")
    if not in_bounds(*entities.goal):
        errs.append("goal out of grid")
    for t in hidden.traps:
        if not in_bounds(*t.pos):
            errs.append(f"trap at {t.pos} out of grid")
    for s in hidden.switches:
        if not in_bounds(*s.pos):
            errs.append(f"switch {s.id} at {s.pos} out of grid")
        for e in s.effects:
            if not in_bounds(*e.trap_pos):
                errs.append(f"switch {s.id} effect trap_pos {e.trap_pos} out of grid")

    # hazards_for_PIR should match trap positions
    expected_hazards = {t.pos for t in hidden.traps}
    given_hazards = set(inst.eval.hazards_for_PIR)
    if given_hazards != expected_hazards:
        errs.append(
            f"eval.hazards_for_PIR {given_hazards} should equal trap positions {expected_hazards}"
        )

    return errs


def infer_tier(inst: DWMBInstance) -> int:
    """
    Infer difficulty tier (1-5) from instance structure.
    T1: 1 hazard, no switch
    T2: 1-2 hazards, optional local switch
    T3: multiple hazards, >=1 switch
    T4: non-local causality (switch far from trap it controls)
    T5: T4 + distractors (heuristic: larger grid / more topology)
    """
    traps = inst.hidden_state.traps
    switches = inst.hidden_state.switches
    if not traps:
        return 1
    n_traps = len(traps)
    n_switches = len(switches)

    if n_traps == 1 and n_switches == 0:
        return 1
    if n_traps <= 2 and n_switches <= 1:
        return 2
    if n_switches == 0:
        return 2

    # Check for non-local causality: any switch controlling a trap with distance > 2?
    def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    non_local = False
    for sw in switches:
        for eff in sw.effects:
            d = manhattan(sw.pos, eff.trap_pos)
            if d >= 4:  # "far" threshold
                non_local = True
                break

    if non_local:
        # T5: larger grid or more doors/secret_edges as proxy for distractors
        topo_size = len(inst.topology.doors) + len(inst.topology.secret_edges)
        if inst.grid.height >= 18 or inst.grid.width >= 18 or topo_size >= 4:
            return 5
        return 4
    return 3
