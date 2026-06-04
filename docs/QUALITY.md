# Quality

This document defines safe validation for the reset branch.

R4-B uses the same non-provider validation boundary as R3/R3.6/R4-A. It adds
runtime binding registry, legacy mapping, and executor annotation coverage, not
provider, external live, frontend, or business-agent capability.

## Safe R4-B Commands

```powershell
git status --short --branch
git diff --name-status
git diff --check
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent tests scripts/quality
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_public_api.py
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_graph.py
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
```

## Not Safe For R4-B

Do not run during R3/R4-A/R4-B unless the user explicitly asks:

- provider live smoke
- external `/v1/agent/invoke`
- demo stack start or stop
- artifact-writing mainline gates
- artifact-writing fusion gates
- frontend production build if it writes repo artifacts

R4-B also does not treat `mainline`, `fusion-gate`, provider live smoke, demo
stack, or frontend build/test results as required runtime-binding evidence.

## Current Quality Runner Boundary

`scripts/quality/run_quality.py --mode static` checks maintained reset docs and
selected static code surfaces. Old Router-SFT docs are no longer quality targets.

The previous mainline and fusion-gate modes still exist in code but are not
reset acceptance evidence. They must be rebuilt in later phases before being
used as Fixed DAG gate claims.

## Validation Meaning

Passing safe commands means the deterministic fixed-DAG executor skeleton
imports, parses, validates plan dependencies, generates topological execution
batches, invokes without provider/external calls, exposes `workflow_snapshot_v2`,
projects `step_results` and `execution_batches`, preserves public transcript
safety, and keeps the contract/executor/catalog/runtime-binding seams and
27-agent roster aligned in reset docs/tests.

R3/R4-A/R4-B-specific tests cover `validate_dag_steps`,
`topological_batches`, `execute_fixed_dag_plan`,
`validate_dag_execution_result`, fixed DAG catalog validation, fixed DAG runtime
binding validation, legacy external mapping alignment, graph executor
integration, and public workflow/catalog projection.

It does not mean:

- provider readiness
- external service readiness
- live market-data correctness
- real business-agent correctness
- frontend v2 completion
- mainline/fusion-gate reset gate completion
- production deployment readiness
