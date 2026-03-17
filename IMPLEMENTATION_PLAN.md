# DWMB Implementation Plan

This plan translates the **Dungeon World Model Benchmark (DWMB)** research report into concrete implementation steps. It follows the report’s 12-week outline (Appendix E) and adds dependencies, deliverables, and checkpoints.

---

## Phase 1: Core Engine & Schema (Weeks 1–2)

**Goal:** Implement the DWMB simulation engine, JSON schema, and a minimal runnable environment.

### 1.1 JSON Schema & Validation
- [ ] **Define formal JSON schema** (e.g. JSON Schema or Pydantic) for DWMB instances per Appendix A:
  - `version`, `grid` (height, width, tiles), `visibility` (radius, line_of_sight)
  - `entities` (agent_start, goal)
  - `topology`: doors, secret_edges
  - `hidden_state`: traps (pos, kind, armed, disarm_switch), switches (id, pos, effects)
  - `reward`, `terminal`, `eval.hazards_for_PIR`
- [ ] **Validator** that rejects invalid instances and checks tier constraints (e.g. T3+ has switch–trap links).
- [ ] **Deliverable:** `schema/dwmb_schema.json` (or equivalent) and validation tests.

### 1.2 Simulation Engine
- [ ] **State representation:** `s = (x, θ, h)` — agent position, static topology, dynamic hidden state (trap armed flags, switch states).
- [ ] **Actions:** `Move(N,S,E,W)`, `Inspect`, `Interact`, `UseItem`; collision/wall handling; door and key logic.
- [ ] **Observation function:** Egocentric `View_r` (radius r, default 2); hidden traps rendered as floor; `Event_t` (damage, “click”, pickup, etc.).
- [ ] **Dynamics:** Deterministic transitions given `h`; trap damage and death rules; switch effects on distant traps.
- [ ] **Inspect:** Low success probability (e.g. `p_reveal = 0.15`, tier-dependent) for revealing secret/trap; no info on failure.
- [ ] **Reward:** Sparse goal (+1), step cost (-0.001), trap penalty; support both sparse-goal and constraint (goal + safety) regimes.
- [ ] **Deliverable:** Fast simulator (Python or C extension) with `step(a)`, `observe()`, `reset(instance)`; unit tests for transitions and PIR-relevant events.

### 1.3 Canonical Unit-Test Dungeons
- [ ] **Hand-authored instances** matching report examples (e.g. 16×16 worked example with trap at [2,6], switch s1 at [3,13]).
- [ ] **Regression tests:** Known trajectories, first-visit times for hazards, correct PIR ground truth for a fixed policy.
- [ ] **Deliverable:** `instances/unit_test/*.json` and tests in CI.

---

## Phase 2: Tiered Generators (Weeks 3–4)

**Goal:** Procedural generators that sample POMDPs from distribution 𝒟 with tier constraints.

### 2.1 Tier Definitions (Code)
- [ ] **T1:** Single hazard, no switch; small grid (e.g. up to 12×12).
- [ ] **T2:** 1–2 hazards, optional local switch; same size.
- [ ] **T3:** Multiple hazards, ≥1 switch; short path may be trapped; enforce “alternate safe path” and “indistinguishability” where applicable.
- [ ] **T4:** Non-local causality — ≥1 switch controls a distant trap with no local cue; grid up to 20×20.
- [ ] **T5:** T4 + distractors (dead-ends, longer horizon); same or larger.
- [ ] **Parameters:** Max traps, min switch–trap distance, visibility radius per tier; document in code and README.

### 2.2 Adversarial Constraints (Generator)
- [ ] **Indistinguishability:** At least one trap has no unique visual hint (same tile as safe floor).
- [ ] **Alternate safe path:** At least one trap avoidable via detour.
- [ ] **Non-local causality (T4+):** Switch–trap pairs with sufficient distance and no local cue at trap.
- [ ] **Distractors (T5):** Plausible dead-end corridors/rooms.
- [ ] **Output:** Valid JSON instances with `eval.hazards_for_PIR` populated.

### 2.3 Dataset Splits
- [ ] **Train seeds:** e.g. 200 instances per tier (T2–T5); fixed seeds for reproducibility.
- [ ] **Test seeds:** Held-out seeds, same generator.
- [ ] **Counterfactual:** For each test dungeon, permute trap tile or switch–trap assignment (preserve geometry); generate and save.
- [ ] **Deliverable:** Scripts to generate splits; published seed lists and/or pre-generated `instances/train`, `instances/test`, `instances/counterfactual`.

---

## Phase 3: Baselines & Training/Eval Pipeline (Weeks 5–7)

**Goal:** Implement baseline agents and a unified training/evaluation pipeline with belief logging for PIR.

### 3.1 Belief-Extraction Convention (Interface)
- [ ] **Agent interface:** Each agent must expose:
  - `act(o, b)` (or equivalent with internal state)
  - `update_belief(a, o_new)` → updated belief
  - **Per-hazard probabilities:** For each coordinate in `eval.hazards_for_PIR`, output `p_t(hazard dangerous)` at each step; logged before `step(a)` for PIR.
- [ ] **Convention document:** Short spec for “belief-native” vs “auxiliary head” vs “LLM prompt” extraction (per report Metrics section) so third-party agents can comply.

### 3.2 Baseline Agents
- [ ] **Model-free RL (PPO + LSTM):** Policy over egocentric view + recurrence; optional auxiliary **belief head** (BCE/log loss on hazard presence) for PIR; train on DWMB reward.
- [ ] **MuZero-like:** Learned model of reward, value, policy in latent space; MCTS or similar planning; add belief head for PIR logging.
- [ ] **RSSM/Dreamer-style:** Recurrent latent state, imagined rollouts, policy from latent; decoder or auxiliary head from latent to per-tile hazard probability for PIR.
- [ ] **LLM + memory (optional):** Text description of view + event; LLM with memory to maintain beliefs; extract or prompt for numerical P(hazard) per eval tile at each step; log for PIR.
- [ ] **Sanity checks:** Each baseline runs on trivial (e.g. T1) instances; goal success and basic PIR computation without errors.

### 3.3 Training Pipeline
- [ ] **Config-driven runs:** Instance list, tier, seed, agent type, hyperparameters.
- [ ] **Checkpointing and logging:** Trajectories, beliefs (per-hazard probs), rewards, terminations; format suitable for offline PIR computation.
- [ ] **Reproducibility:** Fixed env seeds, agent seeds; document versions.

### 3.4 Evaluation Scripts
- [ ] **PIR:** For each hazard in `eval.hazards_for_PIR`, compute first-visit time τ(h); check if agent’s logged `p_{τ(h)-1}(h) ≥ δ`; aggregate PIR_δ.
- [ ] **AUPIR:** Area under PIR vs δ curve.
- [ ] **Secondary:** Goal completion rate, survival rate, hazard activation count, damage; calibration (optional); map reconstruction F1 and causal discovery F1 if agent outputs available.
- [ ] **Deliverable:** Single entry point (e.g. `evaluate.py`) that loads run logs + instance, computes all metrics, writes summary (per instance and aggregate).

---

## Phase 4: JEPA-Style Agent Prototype (Weeks 8–9)

**Goal:** Prototype the proposed architecture (encoder → context RNN → predictor → planner) with a belief head for PIR.

### 4.1 Architecture
- [ ] **Encoder E_φ(o_t):** Map observation to token embeddings (e.g. one vector per visible tile).
- [ ] **Context RNN C_ψ:** Aggregate {y_{1:t}} and actions → latent state z_t.
- [ ] **Predictor P_ω:** From z_t predict future embeddings for masked/unseen regions or time steps (mask-and-predict in latent space).
- [ ] **Belief head:** D(z_t, pos) → p_t(hazard at pos); trained with same losses so PIR is comparable.
- [ ] **Planner:** Use predictor as dynamics model (e.g. latent MPC or tree search) to choose actions.

### 4.2 Losses
- [ ] **Latent prediction loss:** L2 or contrastive over masked positions; stop-gradient on targets (e.g. V-JEPA-style).
- [ ] **Belief consistency (KL):** If using inference network q(z_{t+1}|o_{1:t+1},a_{1:t}) and prior p(z_{t+1}|z_t,a_t), add KL term to avoid collapse.
- [ ] **Regularization:** Document choices (e.g. masking scheme, weight for KL) to avoid representation collapse.

### 4.3 Integration
- [ ] **Same env and belief interface** as baselines; log per-hazard probabilities at each step.
- [ ] **Ablation:** Option to disable belief loss or predictor to test contribution.

---

## Phase 5: Experiments & Analysis (Weeks 10–11)

**Goal:** Run preregistered evaluation and produce statistical results.

### 5.1 Experimental Protocol
- [ ] **Runs:** Each method × tier (e.g. T2–T5) on train and test splits; K ≥ 10 random seeds per instance.
- [ ] **Counterfactual:** Same agents on counterfactual instances; record PIR and success.
- [ ] **Compute metrics:** PIR (multiple δ), AUPIR, goal success, survival, hazard activations; optional calibration and F1 metrics.

### 5.2 Statistical Analysis
- [ ] **Paired Wilcoxon** on PIR across instances (method A vs B).
- [ ] **Mixed-effects model:** PIR (or success) ~ Method + (1|dungeon); report fixed effects and variance.
- [ ] **Multiple comparisons:** Benjamini–Hochberg FDR correction.
- [ ] **Effect sizes:** Cliff’s delta for PIR; odds ratio for goal success.
- [ ] **Hypotheses (from report):** (H1) Belief/planning agents higher PIR than model-free at similar success; (H2) Planners better causal-discovery F1 on T4–T5; (H3) Counterfactual PIR drop for shortcut-reliant agents.

### 5.3 Ablations & Robustness
- [ ] Ablate JEPA-style agent: with/without belief loss, with/without latent prediction.
- [ ] Sensitivity to PIR threshold δ and to tier.

---

## Phase 6: Artifacts & Dissemination (Week 12)

**Goal:** Release-ready code, data, and documentation.

### 6.1 Code Release
- [ ] **Repository structure:** e.g. `env/`, `agents/`, `eval/`, `generators/`, `schema/`, `instances/`, `scripts/`.
- [ ] **README:** Install, quick start (run one dungeon, run one baseline, run evaluation).
- [ ] **Open license** (e.g. MIT/Apache); document in LICENSE and paper.

### 6.2 Data & Splits
- [ ] **Published splits:** Train/test/counterfactual seed lists or pre-generated instance IDs.
- [ ] **Canonical instances:** Unit-test and worked-example JSONs included; optional larger instance archive (e.g. Zenodo) if needed.

### 6.3 Documentation
- [ ] **Schema and tier spec** (link to schema, tier table, adversarial constraints).
- [ ] **Belief-extraction convention** for PIR (how each agent type should report p_t(h)).
- [ ] **Reproducibility:** Environment (e.g. conda/venv), versions, and run commands for main tables/figures.

### 6.4 Manuscript
- [ ] **Fill in results** (tables, figures) from Phase 5; update “pending validation” and “no empirical results” language.
- [ ] **Camera-ready** revisions and supplementary (e.g. hyperparameters, extra ablations).

---

## Dependency Overview

```
Phase 1 (engine, schema) ──► Phase 2 (generators) ──► Phase 3 (baselines, pipeline)
         │                              │                        │
         └──────────────────────────────┴────────────────────────┴──► Phase 5 (experiments)
                                                                  │
Phase 4 (JEPA prototype) ────────────────────────────────────────┘
                                                                  │
                                                                  ▼
                                                            Phase 6 (release)
```

- **Phase 1** is blocking for all other phases.
- **Phase 2** is needed for large-scale training and evaluation (Phase 3, 5).
- **Phase 3** and **Phase 4** can overlap after Phase 1–2; Phase 4 depends on the same env and belief interface from Phase 3.
- **Phase 5** depends on Phase 3 and 4; **Phase 6** depends on Phase 5.

---

## Success Criteria (from Report)

- **Benchmark:** DWMB generator and schema released; tier constraints and adversarial properties enforced.
- **Metrics:** PIR (and AUPIR) computed via uniform belief-extraction convention; success, safety, and optional F1/calibration reported.
- **Hypotheses:** (H1)–(H3) tested with preregistered statistics; falsifiable claim about belief-based agents vs reactive agents clearly stated and either supported or refuted by data.
- **Reproducibility:** Others can regenerate instances, run baselines, and reproduce main results with provided code and splits.

---

## Optional Extensions (Post–12 Weeks)

- **Oracle-topology regime:** Option to provide θ to the agent to isolate belief over h only; compare PIR in full vs oracle-topology.
- **Additional baselines:** Other world models (e.g. different RSSM variants) or planning methods.
- **Larger tiers:** More tiers or larger grids if compute allows.
- **Visualization:** Belief heatmaps over the grid (as in report Fig. 1(c)) for selected runs to support interpretation.
