# langgraph-my-agent

This branch is the Fixed DAG reset branch. It replaces the old route-mode,
Router-SFT, route-prior, A01 contract dispatch, and Fair Fusion mainline with a
smaller deterministic fixed-DAG runtime skeleton.

Phase R2 has hardened the active reset skeleton with explicit contracts,
validators, normalizers, and deterministic function seams. It is not a
completed business analysis engine.

## Current Branch Scope

- Branch: `reset/fixed-dag-v1`.
- Reset base: `pre-fixed-dag-reset-20260604-1457`.
- Current phase: R2 contract and function seam hardening.
- Runtime entry: `langgraph.json -> src/react_agent/graph.py:graph`.
- Public Python workflow contract: `workflow_snapshot_v2`.
- Public web shell: retained for later in-place frontend v2 migration.
- Production status: not a production deployment claim.

Historical material removed on this branch remains recoverable from the
pre-reset tag. Do not use old Agent Catalog v2 docs, route mode docs,
route-prior/RARP material, Router-SFT material, A01 SFT material, or Fair Fusion
docs as current reset authority.

## Active Runtime Skeleton

The active graph is now deterministic and provider-free:

```text
user input
  -> route_planner
  -> prepare_l1_context
  -> run_l2_conclusions
  -> run_dimension_composites
  -> decision_synthesizer
  -> report_generator
  -> final_emit
  -> memory_update
```

The reset target has 27 formal agent ids:

- L1 planning/evidence seams: 3 target ids.
- L2 conclusion placeholders: 18 target ids.
- L3 dimension composites: 4 target ids.
- L4 decision/report: 2 target ids.

The v4 feedback-aligned roster removes the enterprise financial analysis target.
`sentiment_company_radar` belongs to the market dimension and routes only to
`market_composite`; it is not a direct risk-composite input in this reset
runtime.

See `docs/ARCHITECTURE_FIXED_DAG.md` for the current skeleton map.

## Current Runtime Boundary

R1-B changes the active graph and Python public workflow adapter:
R2 keeps that graph deterministic and routes graph/public fallback construction
through `src/react_agent/fixed_dag_contracts.py` contract/function seams:

- `src/react_agent/fixed_dag_contracts.py`
- `src/react_agent/graph.py`
- `src/react_agent/prompts.py`
- `src/react_agent/router_parse.py`
- `src/react_agent/state.py`
- `src/react_agent/public_contracts.py`
- `src/react_agent/public_mapping.py`
- `src/react_agent/public_runtime.py`
- `src/react_agent/public_api.py`

The external HTTP wrapper infrastructure and baseline sidecar module remain in
the repository, but they are not connected to the active reset graph. Existing
`config/agents/*.json` remains until the R4 catalog/runtime registry phase.

## Public Transcript Boundary

The product keeps a single assistant transcript. Internal graph steps, raw graph
messages, manager assignments, agent JSON, and provider raw responses must not
be treated as public transcript content.

The workflow inspector is a diagnostic panel. The Python public adapter projects
DAG stages, steps, dimensions, provenance, and final source as
`workflow_snapshot_v2` through reset contract seams. The current web UI still
needs its R5 workflow rewrite.

## Documentation Index

- `docs/INDEX.md` - reset documentation map.
- `docs/SYSTEM_MAP.md` - active runtime topology and phase map.
- `docs/ARCHITECTURE_FIXED_DAG.md` - fixed DAG skeleton and target ids.
- `docs/CONTRACTS.md` - runtime/public contract payload boundaries.
- `docs/FRONTEND_V2.md` - frontend/public transcript boundary.
- `docs/QUALITY.md` - safe quality commands for the reset branch.
- `docs/DECISIONS.md` - reset architecture decisions.
- `docs/CHANGELOG.md` - reset branch changelog.

## Safe Local Validation

Use the project conda environment when available:

```powershell
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent tests scripts/quality
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_public_api.py
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_graph.py
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
```

Do not use successful tests as production readiness evidence.

## Explicit Non-Claims

- No provider or live external service was verified by R2.
- No `external /v1/agent/invoke` call is part of R2 validation.
- No demo stack startup is part of R2 validation.
- No real business algorithms for individual agents are implemented in R2.
- No frontend v2 rewrite is complete in R2.
- No mainline or fusion-gate reset quality gate is rebuilt in R2.
- No production auth, rate limit, HTTPS, deployment, or observability claim is made here.
