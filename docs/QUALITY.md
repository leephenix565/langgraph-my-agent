# Quality

This document defines the safe validation boundary for the fixed-DAG reset
branch after Phase R6-B.

## Default Reset Mainline

R6-B rebuilds `scripts/quality/run_quality.py --mode mainline` as the default
fixed-DAG reset quality gate. The mainline runs:

1. `static`
2. `unit`
3. `public-api`
4. `graph-smoke`
5. `frontend`

It does not run fusion-gate, provider live smoke, external
`/v1/agent/invoke`, demo stack commands, Router-SFT, RARP/route-prior, or
browser screenshot capture.

## Quality Runner Modes

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode unit
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode public-api
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode graph-smoke
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode frontend
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
```

`static` is intentionally scoped to active reset source, reset tests, quality
scripts, and maintained docs. It is not a full-tree legacy/offline lint gate.

`frontend` runs:

```powershell
npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json
npm --prefix apps/web run test
npm --prefix apps/web run build -- --outDir <repo-external-temp-dir>
```

The runner creates a temporary repo-external frontend build directory and
cleans it up after the build. It must not write `apps/web/dist`.

## Manual, Live, And Archived Gates

These checks are not default reset mainline gates:

- `fusion-gate`: archived/manual deterministic regression lineage only.
- provider live smoke: optional live/manual or scheduled workflow only.
- external `/v1/agent/invoke`: manual/live readiness work only.
- demo stack start/stop: manual demo/deployment acceptance only.
- Router-SFT and RARP/route-prior: archived lineage only.
- browser screenshot visual capture: manual frontend visual acceptance only.

## Validation Meaning

Passing the R6-B reset mainline means the maintained static surface passes,
unit tests pass, public adapter integration tests pass, the runtime graph smoke
test passes, and the frontend typecheck/smoke/repo-external build gate passes.

It does not mean:

- provider readiness
- external service readiness
- live market-data correctness
- real business-agent correctness
- fusion acceptance restored
- visual screenshot acceptance
- production deployment readiness
- full-tree lint enforcement

The fixed-DAG runtime remains the deterministic provider-free reset skeleton
until later phases implement and verify real business agents and live external
service readiness.

## R8-1 Selected Contract Gate

R8-1 adds `route_intent_v1` and `selected_fixed_dag_plan_v1` contract validators
without changing active graph behavior. Its narrow validation gate is:

```powershell
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_contracts.py
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py -q
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_executor.py -q
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
git diff --check
```

This gate confirms that the additive selected contract seam and the full default
fixed DAG regression baseline still validate. It does not run selected DAG
execution, provider live smoke, search, external `/v1/agent/invoke`, demo stack,
fusion-gate, Router-SFT, RARP/route-prior, or frontend build.

Passing R8-1 validation does not mean that an LLM planner, deterministic
selected compiler, RouteEval suite, external adapter, or real business-agent
result mapping is implemented.

## R8-2 Selected Compiler Gate

R8-2 adds deterministic selected DAG compilation and selected plan executor
validation helpers without changing active graph behavior. Its narrow
validation gate is:

```powershell
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py src/react_agent/fixed_dag_executor.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py -q
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
git diff --check
```

This gate confirms that `compile_selected_fixed_dag_plan`,
`validate_selected_dag_steps`, and `topological_batches_for_selected_plan`
preserve the full DAG regression baseline while validating selected
dependency-closed plans. It does not run active graph selected execution,
provider live smoke, search, external `/v1/agent/invoke`, demo stack,
fusion-gate, Router-SFT, RARP/route-prior, or frontend build.

Passing R8-2 validation does not mean that an LLM planner, RouteEval suite,
external adapter, runtime binding enablement, public workflow selected-plan
projection, or real business-agent result mapping is implemented.

## R8-3 Planner Seam Gate

R8-3 adds provider-free route-intent planner seam helpers without changing
active graph behavior. Its narrow validation gate is:

```powershell
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py src/react_agent/router_parse.py src/react_agent/prompts.py src/react_agent/context.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_parse_router_layers.py
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_parse_router_layers.py -q
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
git diff --check
```

This gate confirms that deterministic/mock route intent construction, the
route-intent prompt contract, and parser/normalizer fallback behavior preserve
the full DAG regression baseline. It does not run provider live smoke, search,
external `/v1/agent/invoke`, demo stack, fusion-gate, frontend build, active
graph selected execution, or live selected routing.

Passing R8-3 validation does not mean that an active LLM planner, RouteEval
suite, external adapter, runtime binding enablement, public workflow
selected-plan projection, or real business-agent result mapping is implemented.

## R8-4 RouteEval Gate

R8-4 adds provider-free RouteEval helpers and a small local JSONL gold set
without changing active graph behavior. Its narrow validation gate is:

```powershell
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent tests scripts/quality
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_route_eval.py -q
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_parse_router_layers.py -q
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
git diff --check
```

This gate confirms that RouteEval can load the local fixture and evaluate
`route_intent_v1` task type, target, dimension, agent, clarification, and
fallback selections without provider or external calls. R8-4 does not add a
`route-eval` quality runner mode; the explicit unit test is the offline
evaluation baseline for this phase.

Passing R8-4 validation does not mean that selected routing is active in the
graph, that a provider-backed LLM planner is enabled, that the first 12-case
gold set is a formal >=80% Route F1 acceptance suite, or that external adapter,
runtime binding enablement, public workflow selected-plan projection, or real
business-agent result mapping is implemented.

## R8-5 Selected Routing Graph Flag Gate

R8-5 wires selected routing into the graph behind a default-off context/env
flag. Its narrow validation gate is:

```powershell
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/context.py src/react_agent/graph.py src/react_agent/fixed_dag_contracts.py src/react_agent/fixed_dag_executor.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py -q
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
git diff --check
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
```

This gate confirms that default graph behavior remains the full DAG, that
`Context.enable_selected_routing` / `ENABLE_SELECTED_ROUTING=1` can explicitly
enable provider-free selected routing, and that selected compile/validation
failure falls back to the full DAG with safe provenance.

Passing R8-5 validation does not mean that a provider-backed LLM planner,
external adapter, runtime binding enablement, final Route F1 acceptance gate,
frontend selected-routing UI, or real business-agent result mapping is
implemented.

## R8-6B Internal LLM Placeholder Gate

R8-6B adds default-off internal LLM placeholders for fixed-DAG L2 conclusions.
Its narrow validation gate is:

```powershell
python -m ruff check src/react_agent/context.py src/react_agent/fixed_dag_llm_placeholders.py src/react_agent/fixed_dag_executor.py src/react_agent/graph.py tests/unit_tests/test_fixed_dag_llm_placeholders.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py
python -m pytest tests/unit_tests/test_fixed_dag_llm_placeholders.py tests/unit_tests/test_fixed_dag_executor.py tests/integration_tests/test_graph.py -q
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

This gate confirms that the default path remains deterministic and provider-free,
that `Context.enable_internal_llm_placeholders` /
`ENABLE_INTERNAL_LLM_PLACEHOLDERS=1` is default-off, that fake-provider tests can
exercise internal LLM placeholder L2 conclusions, and that provider/parser
failure falls back to deterministic pending conclusions.

Passing R8-6B validation does not mean external adapter readiness,
`/v1/agent/invoke` readiness, provider live readiness, `live_verified=true`,
`invoke_enabled_by_default=true`, production deployment readiness, or real
business-agent correctness. Deployed server processes remain deferred until
later live verification and runtime binding enablement work.

## R8-7B External Adapter Mapping Gate

R8-7B adds provider-free pure mapping functions for external fixed-DAG payloads.
Its narrow validation gate is:

```powershell
python -m ruff check src/react_agent/fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_adapter.py
python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py -q
python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

This gate confirms that already-available `agent_conclusion_v1` and
`data_bundle_v1` payload dictionaries can be mapped or rejected safely by a pure
adapter and validated against current fixed-DAG internal contracts.

Passing R8-7B validation does not mean HTTP integration, provider readiness,
`GET /health` readiness, `/v1/agent/compute` readiness,
`/v1/agent/invoke` readiness, runtime binding enablement, `live_verified=true`,
`invoke_enabled_by_default=true`, L3/L4 active executor mapping, or real
business-agent correctness. Deployed server agents remain deferred.

## R8-8C Compute Envelope Adapter Compatibility Gate

R8-8C extends the provider-free adapter to accept
`external_agent_compute_v0` as adapter input when it contains a supported L2
`agent_conclusion_v1` tool result. Its narrow validation gate is:

```powershell
python -m ruff check src/react_agent/fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_adapter.py
python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py -q
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

This gate confirms that a compute envelope dictionary can be mapped or rejected
by the pure adapter without HTTP, provider, runtime binding, graph, executor, or
public API changes.

Passing R8-8C validation does not mean `financial_data_service` passed
structured JSON health, does not replace the planned R8-8D
`value_ml_valuation` re-smoke, does not call `/health`,
`/v1/agent/compute`, or `/v1/agent/invoke`, and does not set
`live_verified=true` or `invoke_enabled_by_default=true`.

## R8-8D-ID/R8-8E Controlled Smoke Evidence Boundary

R8-8D-ID performed a controlled dev-only re-smoke for `value_ml_valuation`
after service-side identity remediation. The allowed live endpoints were limited
to `GET /health` and `POST /v1/agent/compute` on the dev service. The smoke did
not call `/v1/agent/invoke`, prod ports, providers, demo stack commands, or
fusion-gate.

R8-8E records the sanitized evidence in docs only. Its main-repo validation gate
is:

```powershell
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing R8-8E validation means the documentation-only evidence record is
consistent with the maintained reset quality surface. It does not mean runtime
bindings are enabled, `live_verified=true` is set,
`invoke_enabled_by_default=true` is set, production readiness is proven, or
external `/v1/agent/invoke` is safe to call by default.

## R8-8G Accelerated Controlled Smoke Evidence Boundary

R8-8G performs dev-only controlled health and compute smokes for a bounded
allowlist of candidate services. The only live endpoints allowed in this phase
are `GET /health` and `POST /v1/agent/compute` on explicitly selected dev ports.
The phase may perform small service-side response identity remediations, but it
does not change the main-system adapter identity gate, runtime bindings, graph,
executor, public API, public runtime, public mapping, frontend, or fixed DAG
roster.

R8-8G docs are updated only for candidates that pass health, compute, and
provider-free adapter mapping. Its main-repo validation gate is:

```powershell
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing R8-8G validation means the documentation-only evidence record remains
consistent with reset quality. It does not mean `/v1/agent/invoke` was called,
runtime bindings are enabled, `live_verified=true` is set,
`invoke_enabled_by_default=true` is set, production readiness is proven, or any
candidate may be invoked by default.

## R8-8H Expanded Controlled Compute Evidence Boundary

R8-8H expands the same dev-only controlled health and compute smoke pattern to a
bounded L2 candidate batch. The only live endpoints allowed in this phase are
`GET /health` and `POST /v1/agent/compute` on explicitly selected dev ports. The
phase may perform small service-side protocol remediations for fixed-DAG
identity, structured health JSON, compute envelope fields, and canonical L2
dimensions, but it does not change the main-system adapter identity gate,
runtime bindings, graph, executor, public API, public runtime, public mapping,
frontend, or fixed DAG roster.

R8-8H docs are updated only for candidates that pass health, compute, and
provider-free adapter mapping. Its main-repo validation gate is:

```powershell
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing R8-8H validation means the documentation-only evidence record remains
consistent with reset quality. It does not mean `/v1/agent/invoke` was called,
runtime bindings are enabled, `live_verified=true` is set,
`invoke_enabled_by_default=true` is set, L3/L4 active runtime integration is
enabled, production readiness is proven, or any candidate may be invoked by
default.

## R7-G/R7-H External Scaffold Package

R7-C/R7-D/R7-E/R7-F/R7-G external developer handoff work upgrades the repo-external
scaffold source package, keeps the tracked repo mirror in sync, expands the AI
coding handoff documentation, restores the v2.3 domain payload family, and
patches v2.3.1 semantic validators for risk members, manual review gates,
structured dimension members, normalized dates, macro directional weights, L4
score tolerance, and distinct reasoning stages. R7-H treats
`examples/fixed_dag_external_agent_scaffold/` as the tracked audit truth and
restores `E:\muti-agent\external_agent_scaffold` from that mirror when the
local distribution working copy is missing. Its validation uses:

```powershell
conda run --no-capture-output -n cline_env python -m pytest E:\muti-agent\external_agent_scaffold\tests -q
conda run --no-capture-output -n cline_env python -m ruff check E:\muti-agent\external_agent_scaffold
conda run --no-capture-output -n cline_env python -m pytest examples/fixed_dag_external_agent_scaffold/tests -q
conda run --no-capture-output -n cline_env python -m ruff check examples/fixed_dag_external_agent_scaffold
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
git diff --check
```

These commands can confirm that the maintained reset quality surface still
passes after docs, samples, schema validators, and scaffold tests are updated.
They do not call providers, do not call external `/v1/agent/invoke`, do not
start the demo stack, do not run fusion-gate, and do not prove that any
external service is live verified or safe to enable.

The scaffold tests are package-local validation. They are not part of the
default reset mainline unless a later phase explicitly changes the quality
policy.
