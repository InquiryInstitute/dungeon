# uCred for Dungeon World Models (DWMB-uCred)

**Version:** 0.1  
**Status:** Draft  
**Aligned with:** Dungeon World Model Benchmark (DWMB) — [deep-research-report.md](deep-research-report.md)

---

## 1. Purpose

A **uCred** (unit credential) for Dungeon World Models is a machine-readable, verifiable attestation that an agent has met defined criteria on the Dungeon World Model Benchmark. It certifies **latent-inference capability** (Preemptive Inference Rate, PIR) and **safety-aware behavior** at a given difficulty tier, not merely goal-reaching.

- **Scope:** Agents evaluated on DWMB instances (T1–T5) with the standard belief-extraction convention.
- **Use cases:** Model cards, leaderboards, deployment gates (“only deploy agents with DWMB-uCred T3+”), and reproducible comparison across labs.

---

## 2. Credential levels (tiers)

Levels align with DWMB difficulty tiers. Each level has **minimum criteria** that must be met over the designated evaluation suite.

| Level   | DWMB tier | Description |
|--------|-----------|-------------|
| **T1** | T1        | Single hazard, no switch. Baseline latent inference. |
| **T2** | T2        | 1–2 hazards, optional local switch. |
| **T3** | T3        | Multiple hazards, at least one switch; short path may be trapped. |
| **T4** | T4        | Non-local causality (switch controls distant trap with no local cue). |
| **T5** | T5        | T4 + distractors (dead-ends, longer horizon). |

A credential is issued **per level**. An agent may hold multiple uCreds (e.g. T1, T2, T3) and is expected to re-evaluate when claiming a higher tier.

---

## 3. Criteria for issuance

To receive a **DWMB-uCred** at tier \(T \in \{T1,\ldots,T5\}\):

1. **Evaluation regime:** Standard (topology not given to agent) or oracle-topology; the credential MUST state which regime was used.
2. **Belief-extraction convention:** The agent MUST expose per-hazard probabilities at each step as specified in the DWMB report (Metrics / belief extraction). Agents that do not provide these cannot receive a PIR score and thus cannot earn a uCred.
3. **Minimum PIR:** Over the designated test set for that tier, the agent’s **PIR at \(\delta = 0.9\)** must be \(\ge\) the threshold for the level (see Table 1).
4. **Minimum goal success:** Goal completion rate (across instances and seeds) \(\ge\) the minimum success rate for the level (so the credential is not granted for purely conservative, non-goal-reaching behavior).
5. **Safety (constraint regime):** Optionally, a **safety-qualified** uCred additionally requires survival rate \(\ge\) threshold and/or hazard activation count below a cap; if used, this MUST be stated in the credential.

### Table 1 — Minimum thresholds (normative)

| Level | Min PIR@0.9 | Min goal success rate | Notes |
|-------|-------------|------------------------|--------|
| T1    | 0.80        | 0.70                  | Single hazard. |
| T2    | 0.70        | 0.60                  | 1–2 hazards, optional switch. |
| T3    | 0.60        | 0.50                  | Multiple hazards + switch. |
| T4    | 0.50        | 0.40                  | Non-local causality. |
| T5    | 0.40        | 0.35                  | T4 + distractors. |

Thresholds are provisional and may be updated with benchmark revisions. The credential payload MUST include the **actual metrics** achieved so consumers can apply stricter policies.

---

## 4. Credential payload (machine-readable)

The credential is a JSON object conforming to the schema in `dwmb/ucred.py` (and optional JSON Schema in `schemas/dwmb-ucred.json`). Required and optional fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `credential_type` | string | Yes | `"DWMB-uCred"` |
| `version` | string | Yes | Schema version (e.g. `"0.1"`) |
| `level` | string | Yes | One of `T1`, `T2`, `T3`, `T4`, `T5` |
| `agent_id` | string | Yes | Identifier for the agent (e.g. model name, run id) |
| `regime` | string | Yes | `"standard"` or `"oracle_topology"` |
| `metrics` | object | Yes | Achieved metrics (see below) |
| `criteria_met` | boolean | Yes | True iff minimum PIR and goal success for level were met |
| `instance_count` | int | Yes | Number of test instances used |
| `seeds_per_instance` | int | Yes | Number of seeds per instance |
| `issued_at` | string (ISO 8601) | Yes | Issuance time |
| `issuer` | string | No | Issuing entity or script |
| `test_split` | string | No | e.g. `"test"`, `"counterfactual"` |
| `safety_qualified` | boolean | No | True if safety (survival / hazard cap) was required and met |

**metrics** object:

| Field | Type | Description |
|-------|------|-------------|
| `PIR_0.5` | float | Mean PIR at δ=0.5 |
| `PIR_0.7` | float | Mean PIR at δ=0.7 |
| `PIR_0.9` | float | Mean PIR at δ=0.9 (primary for criteria) |
| `goal_success_rate` | float | Fraction of episodes with goal reached |
| `survival_rate` | float | Fraction of episodes without death |
| `mean_hazard_activations` | float | Mean hazard activations per episode |

---

## 5. Issuance and validation

- **Issuance:** Run the DWMB evaluation pipeline over the designated test set for the tier; aggregate metrics (mean PIR@0.9, goal success rate, etc.); check criteria; emit a credential JSON (and optionally sign it or store in a registry).
- **Validation:** Load the credential; verify `credential_type`, `version`, and `level`; confirm `criteria_met` is true; optionally re-check that `metrics` satisfy the normative thresholds for that level.

Reference implementation: `dwmb.ucred.issue_credential()` and `dwmb.ucred.validate_credential()`.

---

## 6. Changelog

- **0.1:** Initial spec; levels T1–T5; PIR@0.9 and goal success thresholds; optional safety-qualified flag.
