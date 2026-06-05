# Quality

This document defines safe validation for the reset branch.

R5-B2/R5-B2.6/R5-C/R5-C1 keep the same non-provider validation boundary as
R3/R3.6/R4-A/R4-B/R4-C/R5-B1. R5-B2 adds frontend workflow inspector
validation for the existing `apps/web` shell, and R5-B2.6 adds localized
visible-copy and visual copy-polish validation over that same inspector. R5-C
adds normal-UI simplification, advanced diagnostic disclosure, and product-facing
copy validation over the same public payload. R5-C1 adds default-surface
business-copy professionalization for dimension summaries, step summaries, and
answer-card evidence labels. These phases do not add provider, external live,
demo-stack, production deployment, or business-agent capability validation.

## Safe R5-B2/R5-B2.6/R5-C/R5-C1 Commands

```powershell
git status --short --branch
git diff --name-status
git diff --check
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent tests scripts/quality
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_public_api.py
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_graph.py
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
npm --prefix apps/web run test
npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json
npm --prefix apps/web run build -- --outDir E:/muti-agent/_tmp_web_build_r5c1
```

## Not Safe For R5-B2/R5-B2.6/R5-C/R5-C1

Do not run during R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1 unless the
user explicitly asks:

- provider live smoke
- external `/v1/agent/invoke`
- demo stack start or stop
- artifact-writing mainline gates
- artifact-writing fusion gates
- frontend production build if it writes repo artifacts; use a repo-external
  `--outDir` if build validation is explicitly required

R5-B2/R5-B2.6/R5-C/R5-C1 treat frontend smoke, TypeScript no-emit checks, and
repo-external frontend build output as frontend inspector/copy evidence only.
They do not treat `mainline`, `fusion-gate`, provider live smoke, demo stack, or
artifact-writing frontend build results as required runtime-boundary evidence.

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
27-agent roster aligned in reset docs/tests. In R5-B2 it also means the
frontend TypeScript contract, mock agent catalog, mock workflow snapshot,
streaming smoke fixture, and WorkflowPanel inspector render the fixed DAG public
payload's stage timeline, execution batches, dimension groups, selected step
metadata, final source, and provenance while preserving the single public
transcript boundary. In R5-B2.6 it also means the relevant visible Chinese copy,
status labels, metadata labels, screenshot/mock fixture copy, and deterministic
public-safe reset skeleton answer are aligned while raw technical ids and enum
values remain available in inspector/debug contexts. In R5-C it also means the
normal chat, answer, Agents, and Settings surfaces are product-facing by
default while workflow technical details and Settings advanced diagnostics still
retain true runtime/readiness boundary information. In R5-C1 it also means
dimension summaries, step summaries, and answer-card evidence copy avoid
fixture/roster/transcript/path-wiring language in default user-visible
surfaces, while raw protocol values remain available in expanded technical
details.

R3/R4-A/R4-B/R4-C-specific tests cover `validate_dag_steps`,
`topological_batches`, `execute_fixed_dag_plan`,
`validate_dag_execution_result`, fixed DAG catalog validation, fixed DAG runtime
binding validation, legacy external mapping alignment, graph executor
integration, public workflow/catalog projection, active graph import isolation
from legacy registry/bootstrap modules, and explicit legacy compatibility
bootstrap tests.

It does not mean:

- provider readiness
- external service readiness
- live market-data correctness
- real business-agent correctness
- visual dependency graph beyond ordered execution batches
- evidence-specific frontend drilldown
- mainline/fusion-gate reset gate completion
- production deployment readiness
- full runtime locale switching
