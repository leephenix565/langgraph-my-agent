# langgraph-my-agent

This branch is a Fixed DAG reset branch. It is a reset baseline for replacing the old agent-catalog, route mode, Router-SFT, route-prior, and Fair Fusion lineage with a smaller fixed-DAG architecture.

Phase R1-A is a hard slimming phase only. It deletes archived/offline lineage and rebuilds the reset documentation set. It does not mean the Fixed DAG runtime has been implemented.

## Current Branch Scope

- Branch: `reset/fixed-dag-v1`.
- Reset base: `pre-fixed-dag-reset-20260604-1457`.
- Target architecture: 28 formal agents plus a fixed topological DAG executor.
- Runtime status: current `langgraph.json` still points at `src/react_agent/graph.py:graph`.
- Public surface status: the existing public adapter and web shell remain in place.
- Production status: not a production deployment claim.

Historical material removed on this branch remains recoverable from the pre-reset tag. Do not use old Agent Catalog v2 docs, old `aNN` ids, route mode docs, Fair Fusion docs, route-prior/RARP material, or Router-SFT material as current reset facts.

## Target Architecture

The reset target is:

```text
user input
  -> fixed_dag_plan_v1
  -> L1 parse and data preparation
  -> L2 dimension analysis
  -> L3 dimension composites
  -> L4 decision synthesis and report generation
  -> public single-assistant transcript
```

The target formal agent set has 28 ids:

- L1 parse layer: 3 agents.
- L2 analysis layer: 19 agents.
- L3 application layer: 4 agents.
- L4 report layer: 2 agents.

See `docs/ARCHITECTURE_FIXED_DAG.md` for the target agent table and high-level DAG.

## Current Runtime Boundary

R1-A keeps the current runtime files intact:

- `src/react_agent/graph.py`
- `src/react_agent/prompts.py`
- `src/react_agent/router_parse.py`
- `src/react_agent/state.py`
- `src/react_agent/public_contracts.py`
- `src/react_agent/public_mapping.py`
- `src/react_agent/public_api.py`
- `src/react_agent/public_runtime.py`
- `src/react_agent/public_store.py`
- `src/react_agent/public_guardrails.py`
- `src/react_agent/baseline_sidecar.py`
- `apps/web`

Those files still describe the old running graph and public workflow until later phases replace them. Do not read the reset docs as evidence that the code already executes the new DAG.

## Public Transcript Boundary

The target product keeps a single assistant transcript. Internal graph steps, raw graph messages, manager assignments, agent JSON, and provider raw responses must not be treated as public transcript content.

The workflow inspector is a diagnostic panel. In the target frontend it should describe DAG stages, dimensions, and steps. It must not create a multi-agent public chat transcript.

## Documentation Index

- `docs/INDEX.md` - reset documentation map.
- `docs/SYSTEM_MAP.md` - current operational boundary and phase map.
- `docs/ARCHITECTURE_FIXED_DAG.md` - target 28-agent fixed DAG.
- `docs/CONTRACTS.md` - target contract names and payload boundaries.
- `docs/FRONTEND_V2.md` - target frontend/public transcript boundary.
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

- No provider or live external service was verified by R1-A docs.
- No `external /v1/agent/invoke` call is part of R1-A validation.
- No demo stack startup is part of R1-A validation.
- No Fixed DAG runtime execution is complete in R1-A.
- No frontend v2 rewrite is complete in R1-A.
- No production auth, rate limit, HTTPS, deployment, or observability claim is made here.
