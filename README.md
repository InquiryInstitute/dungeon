# Dungeon World Model Benchmark (DWMB)

Implementation of the **Dungeon World Model Benchmark** from the [deep-research-report](deep-research-report.md): POMDP grid-worlds with hidden hazards and non-local causality, and the **Preemptive Inference Rate (PIR)** metric.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python scripts/evaluate.py instances/unit_test/worked_example_16x16.json
```

## Keys (Google & Supabase)

- **Supabase** (optional): store instances, runs, and metrics. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`, or use the same vars as [Inquiry.Institute](../Inquiry.Institute) (e.g. copy `../Inquiry.Institute/.env.local` or symlink).
- **Google / Vertex AI** (optional): for the LLM baseline agent; use `VERTEX_PROJECT_ID`, `VERTEX_LOCATION`, `VERTEX_SERVICE_ACCOUNT_JSON` (or load from Inquiry.Institute).

See [.env.example](.env.example). Config is loaded from the project `.env` first, then `../Inquiry.Institute/.env.local` or `../Inquiry.Institute/.env`.

## Project layout

| Path | Description |
|------|-------------|
| `dwmb/` | Core: schema, env, validation, config, generator, Supabase storage |
| `instances/unit_test/` | Canonical unit-test dungeons (e.g. worked 16×16) |
| `instances/train`, `test`, `counterfactual/` | Generated splits (see below) |
| `scripts/evaluate.py` | Run agent on instance, compute PIR, optional Supabase sync |
| `scripts/generate_splits.py` | Generate train/test/counterfactual instance JSONs per tier |
| `supabase/migrations/` | DB tables for `dwmb_instances`, `dwmb_runs`, `dwmb_metrics` |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Full 6-phase implementation plan |

## Generate instance splits (Phase 2)

```bash
# Small: 3 train + 2 test per tier for tiers 1–2
python scripts/generate_splits.py --out instances --train-per-tier 3 --test-per-tier 2 --tiers 1 2

# Full: 50 train + 20 test per tier (T1–T5), 2 counterfactuals per test
python scripts/generate_splits.py --out instances --train-per-tier 50 --test-per-tier 20
```

Output: `instances/train/*.json`, `instances/test/*.json`, `instances/counterfactual/*.json`, `instances/seeds_manifest.json`.

## Agents and training (Phase 3)

**Agents:** `random`, `heuristic`, `ppo_lstm` (optional PyTorch). Each exposes `act(obs, hazards)` → `(action, per_hazard_probs)` for PIR.

```bash
# Single instance
python scripts/evaluate.py instances/unit_test/worked_example_16x16.json --agent heuristic

# Batch: aggregate over instances and seeds
python scripts/evaluate_batch.py instances/test --agent random --seeds 3 --out results.json
python scripts/evaluate_batch.py instances/seeds_manifest.json --manifest test --agent heuristic
```

**Train PPO+LSTM** (optional, requires `torch`):

```bash
pip install torch
python scripts/train.py --instances instances/train --steps 5000 --out runs/ppo --save-every 1000
python scripts/evaluate.py instances/unit_test/worked_example_16x16.json --agent ppo_lstm --checkpoint runs/ppo/ckpt_final.pt
```

**JEPA-style agent** (Phase 4):

```bash
python scripts/train_jepa.py --instances instances/train --steps 3000 --out runs/jepa
python scripts/evaluate.py instances/unit_test/worked_example_16x16.json --agent jepa --checkpoint runs/jepa/ckpt_final.pt
# Ablations: --no-predictor or --no-belief-loss in train_jepa
```

## Apply Supabase migrations

If using Supabase, create the tables:

```bash
# If using Supabase CLI (from project root)
supabase db push

# Or run the SQL in supabase/migrations/20250317000000_dwmb_tables.sql
# in the Supabase SQL editor.
```

## Evaluate and sync to Supabase

```bash
python scripts/evaluate.py instances/unit_test/worked_example_16x16.json --agent random --seed 42 --sync --out results.json
```

## License

See repository license.
