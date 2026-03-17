"""
uCred for Dungeon World Models (DWMB-uCred).

Unit credential: machine-readable attestation that an agent met DWMB criteria
at a given tier (T1–T5). See ucred-dwmb-spec.md for the full specification.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

Level = Literal["T1", "T2", "T3", "T4", "T5"]
Regime = Literal["standard", "oracle_topology"]

# Normative minimum thresholds per level (PIR@0.9, goal_success_rate)
# Spec: ucred-dwmb-spec.md Table 1
UCRED_MIN_PIR_0_9: dict[str, float] = {
    "T1": 0.80,
    "T2": 0.70,
    "T3": 0.60,
    "T4": 0.50,
    "T5": 0.40,
}
UCRED_MIN_GOAL_SUCCESS: dict[str, float] = {
    "T1": 0.70,
    "T2": 0.60,
    "T3": 0.50,
    "T4": 0.40,
    "T5": 0.35,
}


class CredentialMetrics(BaseModel):
    """Achieved metrics used for uCred criteria."""

    PIR_0_5: float = Field(..., ge=0, le=1, description="Mean PIR at δ=0.5")
    PIR_0_7: float = Field(..., ge=0, le=1, description="Mean PIR at δ=0.7")
    PIR_0_9: float = Field(..., ge=0, le=1, description="Mean PIR at δ=0.9 (primary for criteria)")
    goal_success_rate: float = Field(..., ge=0, le=1, description="Fraction of episodes with goal reached")
    survival_rate: float = Field(..., ge=0, le=1, description="Fraction of episodes without death")
    mean_hazard_activations: float = Field(..., ge=0, description="Mean hazard activations per episode")

    class Config:
        frozen = True


class DWMBuCred(BaseModel):
    """DWMB-uCred credential payload (machine-readable)."""

    credential_type: Literal["DWMB-uCred"] = "DWMB-uCred"
    version: str = Field(default="0.1", description="Schema version")
    level: Level = Field(..., description="Tier T1–T5")
    agent_id: str = Field(..., description="Agent or run identifier")
    regime: Regime = Field(..., description="standard or oracle_topology")
    metrics: CredentialMetrics = Field(..., description="Achieved metrics")
    criteria_met: bool = Field(..., description="True iff min PIR and goal success for level were met")
    instance_count: int = Field(..., ge=1, description="Number of test instances")
    seeds_per_instance: int = Field(..., ge=1, description="Seeds per instance")
    issued_at: str = Field(..., description="ISO 8601 issuance time")
    issuer: str | None = Field(default=None, description="Issuing entity or script")
    test_split: str | None = Field(default=None, description="e.g. test, counterfactual")
    safety_qualified: bool = Field(default=False, description="True if safety criteria were required and met")

    def model_dump_json_credential(self) -> str:
        """Serialize for storage or display (JSON, no alias)."""
        return self.model_dump(mode="json")

    @classmethod
    def parse_json_credential(cls, data: dict[str, Any] | str) -> "DWMBuCred":
        """Parse from dict or JSON string. Accepts PIR_0.5 / PIR_0_5 style keys."""
        if isinstance(data, str):
            import json
            data = json.loads(data)
        # Normalize metrics keys (allow both PIR_0.9 and PIR_0_9)
        if "metrics" in data and isinstance(data["metrics"], dict):
            m = dict(data["metrics"])
            for old, new in [("PIR_0.5", "PIR_0_5"), ("PIR_0.7", "PIR_0_7"), ("PIR_0.9", "PIR_0_9")]:
                if old in m and new not in m:
                    m[new] = m.pop(old)
            data = {**data, "metrics": m}
        return cls.model_validate(data)


def criteria_met(
    level: Level,
    pir_0_9: float,
    goal_success_rate: float,
    safety_required: bool = False,
    survival_rate: float | None = None,
) -> bool:
    """
    Return True if achieved metrics meet the normative criteria for the level.
    If safety_required is True, survival_rate must be provided and be >= 0.9 (provisional).
    """
    if level not in UCRED_MIN_PIR_0_9 or level not in UCRED_MIN_GOAL_SUCCESS:
        return False
    if pir_0_9 < UCRED_MIN_PIR_0_9[level]:
        return False
    if goal_success_rate < UCRED_MIN_GOAL_SUCCESS[level]:
        return False
    if safety_required and survival_rate is not None and survival_rate < 0.9:
        return False
    return True


def issue_credential(
    level: Level,
    agent_id: str,
    regime: Regime,
    metrics: CredentialMetrics | dict[str, Any],
    instance_count: int,
    seeds_per_instance: int,
    *,
    issuer: str | None = None,
    test_split: str | None = None,
    safety_qualified: bool = False,
    issued_at: str | None = None,
) -> DWMBuCred:
    """
    Build a DWMB-uCred from evaluation results.
    Sets criteria_met from normative thresholds (ucred-dwmb-spec.md).
    """
    if isinstance(metrics, dict):
        metrics = CredentialMetrics(
            PIR_0_5=metrics.get("PIR_0.5", metrics.get("PIR_0_5", 0)),
            PIR_0_7=metrics.get("PIR_0.7", metrics.get("PIR_0_7", 0)),
            PIR_0_9=metrics.get("PIR_0.9", metrics.get("PIR_0_9", 0)),
            goal_success_rate=metrics["goal_success_rate"],
            survival_rate=metrics["survival_rate"],
            mean_hazard_activations=metrics["mean_hazard_activations"],
        )
    met = criteria_met(
        level,
        metrics.PIR_0_9,
        metrics.goal_success_rate,
        safety_required=safety_qualified,
        survival_rate=metrics.survival_rate if safety_qualified else None,
    )
    return DWMBuCred(
        level=level,
        agent_id=agent_id,
        regime=regime,
        metrics=metrics,
        criteria_met=met,
        instance_count=instance_count,
        seeds_per_instance=seeds_per_instance,
        issued_at=issued_at or datetime.now(tz=timezone.utc).isoformat(),
        issuer=issuer,
        test_split=test_split,
        safety_qualified=safety_qualified,
    )


def credential_from_aggregate(
    aggregate: dict[str, Any],
    level: Level,
    agent_id: str,
    regime: Regime,
    instance_count: int,
    seeds_per_instance: int,
    *,
    issuer: str | None = None,
    test_split: str | None = None,
    safety_qualified: bool = False,
) -> DWMBuCred:
    """
    Build a DWMB-uCred from the aggregate dict produced by evaluate_batch.
    Expects keys: PIR_0.5_mean, PIR_0.7_mean, PIR_0.9_mean, goal_reached_mean,
    died_mean, hazard_activations_mean.
    """
    return issue_credential(
        level=level,
        agent_id=agent_id,
        regime=regime,
        metrics={
            "PIR_0.5": aggregate["PIR_0.5_mean"],
            "PIR_0.7": aggregate["PIR_0.7_mean"],
            "PIR_0.9": aggregate["PIR_0.9_mean"],
            "goal_success_rate": aggregate["goal_reached_mean"],
            "survival_rate": 1.0 - aggregate["died_mean"],
            "mean_hazard_activations": aggregate["hazard_activations_mean"],
        },
        instance_count=instance_count,
        seeds_per_instance=seeds_per_instance,
        issuer=issuer,
        test_split=test_split,
        safety_qualified=safety_qualified,
    )


def validate_credential(cred: DWMBuCred) -> tuple[bool, list[str]]:
    """
    Validate a credential: structure and normative criteria.
    Returns (valid, list of error messages).
    """
    errors: list[str] = []
    if cred.credential_type != "DWMB-uCred":
        errors.append("credential_type must be 'DWMB-uCred'")
    if cred.level not in UCRED_MIN_PIR_0_9:
        errors.append(f"level must be one of T1–T5, got {cred.level}")
    if cred.criteria_met:
        min_pir = UCRED_MIN_PIR_0_9.get(cred.level)
        min_goal = UCRED_MIN_GOAL_SUCCESS.get(cred.level)
        if min_pir is not None and cred.metrics.PIR_0_9 < min_pir:
            errors.append(f"criteria_met is true but PIR_0.9 {cred.metrics.PIR_0_9} < {min_pir} for {cred.level}")
        if min_goal is not None and cred.metrics.goal_success_rate < min_goal:
            errors.append(
                f"criteria_met is true but goal_success_rate {cred.metrics.goal_success_rate} < {min_goal} for {cred.level}"
            )
        if cred.safety_qualified and cred.metrics.survival_rate < 0.9:
            errors.append("safety_qualified is true but survival_rate < 0.9")
    return (len(errors) == 0, errors)
