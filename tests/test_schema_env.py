"""Tests for DWMB schema and env."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dwmb.env import DWMBEnv, MOVES
from dwmb.schema import DWMBInstance
from dwmb.validate import infer_tier, validate_instance


FIXTURE_DIR = Path(__file__).resolve().parent.parent / "instances" / "unit_test"


def test_parse_worked_example() -> None:
    path = FIXTURE_DIR / "worked_example_16x16.json"
    if not path.exists():
        pytest.skip("fixture not found")
    with open(path) as f:
        data = json.load(f)
    inst = DWMBInstance.parse_json_compat(data)
    assert inst.grid.height == 16 and inst.grid.width == 16
    assert inst.entities.agent_start == (2, 2)
    assert inst.entities.goal == (13, 12)
    assert len(inst.hidden_state.traps) == 1
    assert inst.hidden_state.traps[0].pos == (2, 6)
    assert inst.eval.hazards_for_PIR == [(2, 6)]


def test_validate_worked_example() -> None:
    path = FIXTURE_DIR / "worked_example_16x16.json"
    if not path.exists():
        pytest.skip("fixture not found")
    with open(path) as f:
        data = json.load(f)
    inst = DWMBInstance.parse_json_compat(data)
    errs = validate_instance(inst)
    assert errs == [], errs


def test_infer_tier() -> None:
    path = FIXTURE_DIR / "worked_example_16x16.json"
    if not path.exists():
        pytest.skip("fixture not found")
    with open(path) as f:
        data = json.load(f)
    inst = DWMBInstance.parse_json_compat(data)
    t = infer_tier(inst)
    assert t >= 1 and t <= 5


def test_env_reset_step() -> None:
    path = FIXTURE_DIR / "worked_example_16x16.json"
    if not path.exists():
        pytest.skip("fixture not found")
    with open(path) as f:
        data = json.load(f)
    inst = DWMBInstance.parse_json_compat(data)
    env = DWMBEnv(seed=42)
    obs, info = env.reset(inst, seed=42)
    assert "view" in obs and "event" in obs
    assert env.agent == (2, 2)
    # Move east
    obs, r, term, trunc, info = env.step("Move_E")
    assert env.agent == (2, 3)
    assert not term
    # Move until we hit wall or goal or trap
    for _ in range(20):
        obs, r, term, trunc, info = env.step("Move_E")
        if term:
            break
    assert env.step_count >= 1


def test_agents_run_and_pir() -> None:
    """Sanity: random and heuristic agents run on T1 and return PIR."""
    path = FIXTURE_DIR / "worked_example_16x16.json"
    if not path.exists():
        pytest.skip("fixture not found")
    with open(path) as f:
        data = json.load(f)
    inst = DWMBInstance.parse_json_compat(data)
    from dwmb.agents.base import make_agent
    from dwmb.runner import run_episode
    for name in ("random", "heuristic"):
        agent = make_agent(name, seed=0)
        metrics, _, _, _ = run_episode(inst, agent, seed=0, max_steps=100)
        assert "PIR_0.5" in metrics and "PIR_0.9" in metrics
        assert 0 <= metrics["PIR_0.5"] <= 1 and 0 <= metrics["PIR_0.9"] <= 1
        assert "goal_reached" in metrics and "hazard_activations" in metrics
