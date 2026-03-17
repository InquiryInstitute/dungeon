"""
Supabase storage for DWMB instances, runs, and metrics.
Uses keys from config (project .env or ../Inquiry.Institute).
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from dwmb.config import get_supabase_key, get_supabase_url, load_dotenv_paths


def get_client() -> Any:
    """Return Supabase client or None if not configured."""
    load_dotenv_paths()
    url = get_supabase_url()
    key = get_supabase_key()
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except ImportError:
        return None


def upsert_instance(
    instance_id: str,
    tier: int,
    split: str,
    payload: dict[str, Any],
) -> UUID | None:
    """Insert or update a DWMB instance. Returns row id or None."""
    client = get_client()
    if not client:
        return None
    row = {
        "instance_id": instance_id,
        "tier": tier,
        "split": split,
        "payload": payload,
    }
    r = client.table("dwmb_instances").upsert(row, on_conflict="instance_id").execute()
    if r.data and len(r.data) > 0:
        return UUID(r.data[0]["id"])
    return None


def insert_run(
    instance_uuid: UUID,
    agent_type: str,
    seed: int,
    trajectory: list[Any] | None = None,
    belief_log: list[Any] | None = None,
    goal_reached: bool | None = None,
    died: bool | None = None,
    hazard_activations: list[tuple[int, int]] | None = None,
    steps: int | None = None,
) -> UUID | None:
    """Insert a run record. Returns run id or None."""
    client = get_client()
    if not client:
        return None
    row = {
        "instance_id": str(instance_uuid),
        "agent_type": agent_type,
        "seed": seed,
        "trajectory": trajectory,
        "belief_log": belief_log,
        "goal_reached": goal_reached,
        "died": died,
        "hazard_activations": [list(p) for p in (hazard_activations or [])],
        "steps": steps,
    }
    r = client.table("dwmb_runs").insert(row).execute()
    if r.data and len(r.data) > 0:
        return UUID(r.data[0]["id"])
    return None


def insert_metrics(
    run_uuid: UUID,
    pir_delta: float | None = None,
    aupr: float | None = None,
    goal_success: bool | None = None,
    survival: bool | None = None,
    hazard_count: int | None = None,
) -> UUID | None:
    """Insert metrics for a run."""
    client = get_client()
    if not client:
        return None
    row = {
        "run_id": str(run_uuid),
        "pir_delta": pir_delta,
        "aupr": aupr,
        "goal_success": goal_success,
        "survival": survival,
        "hazard_count": hazard_count,
    }
    r = client.table("dwmb_metrics").insert(row).execute()
    if r.data and len(r.data) > 0:
        return UUID(r.data[0]["id"])
    return None


def fetch_instances(split: str | None = None, tier: int | None = None) -> list[dict[str, Any]]:
    """Fetch instances, optionally filtered by split and tier."""
    client = get_client()
    if not client:
        return []
    q = client.table("dwmb_instances").select("*")
    if split:
        q = q.eq("split", split)
    if tier is not None:
        q = q.eq("tier", tier)
    r = q.execute()
    return list(r.data or [])
