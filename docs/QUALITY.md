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

CS1-C2X controlled production health/compute and full logical trace artifacts
are manual readiness evidence. They are intentionally not added to default
mainline: mainline remains provider-free and external-endpoint-free. The C2X
regression coverage that belongs in mainline is limited to source-controlled
bridge, temporal guard, public mapping, executor, contracts, and docs tests.

CS1-C3X controlled macro smoke and the final integrated trace are also manual
readiness evidence. The durable mainline coverage is the source-controlled
adapter regression for formal macro members, plus docs tests and standard
static/mainline quality. Service-local focused tests for production wrappers
remain outside default mainline and must be run only in explicit controlled
service phases.

CS1-C3R adds a source-controlled phase artifact integrity helper and L3
real-contributor regression tests. The helper writes relative-path SHA256
manifests only after primary artifacts and validation files are finalized, and
stores verification output separately. Controlled production market-composite
health/compute and the final integrated trace remain manual readiness evidence
and are not added to default mainline.

POST-BF-B1X keeps service health/compute measurements and the 21-agent
controlled regression trace as explicit manual readiness evidence. Default
mainline remains provider-free and external-endpoint-free. The durable repo
coverage is documentation, contract, adapter, public-mapping, and graph tests;
live service timing samples, readiness metadata checks, and production wrapper
smokes stay outside default mainline unless a future phase creates fully mocked
source-controlled fixtures.

POST-BF-B2X adds source-controlled tests for the non-L4 production external
compute policy, validator, executor overlay, demo/production mutual exclusion,
fallback behavior, and public-safe provenance. The three-run dev and prod
canaries are release evidence and remain manual live gates; they are not added
to default mainline. Mainline must still be provider-free and must not call
`/v1/agent/invoke` or live external endpoints.

SYNC-OPS-1 adds a read-only bidirectional external-agent sync planner to the
static/unit quality surface. Its tests validate Draft 2020-12 schemas,
canonical hashes, registry invariants, filesystem safety, B/S/P/D diffing,
immutable plan generation, and unsupported write-command rejection. The planner
does not call `/health`, `/v1/agent/compute`, `/v1/agent/invoke`, providers, or
databases; it does not start, stop, restart, signal, or smoke processes; and it
does not write prod, sandbox, owner-dev, lock, backup, or artifact-store roots
in mainline.

## R8-8N-DOCS Readiness Documentation Boundary

R8-8N-DOCS persists the agent readiness matrix and developer prompt catalog in:

- `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md`
- `docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md`

This is a docs-only persistence phase. The default mainline still does not run
external `/v1/agent/invoke`, provider live smoke, prod service checks, demo
stacks, or fusion-gate. Passing static or mainline after this phase means the
maintained repository quality checks still pass; it does not mean any external
service is live verified or production ready.

## R8-8P Production Smoke Boundary

R8-8P production smoke is manual/live readiness work. It is not part of the
default reset mainline. Production smoke may call confirmed production
`/health` and `/v1/agent/compute` endpoints only in an explicit readiness phase.
It must not call `/v1/agent/invoke` unless a later invoke phase explicitly owns
that scope.

The default mainline remains provider-free and external-HTTP-free. Passing
mainline after R8-8P validates repository static, unit, integration, graph, and
frontend gates; it does not prove production service readiness, invoke
readiness, live verification, or default runtime invocation eligibility.

## R8-11B Controlled Invoke Smoke Boundary

R8-11B is manual/live readiness work and is not part of the default reset
mainline. It may call production `POST /v1/agent/invoke` only for a tiny
allowlist after source audit shows the invoke path can return structured
`tool_result` without a required provider call. The first allowlist used
`allow_llm=false` style options and recorded sanitized adapter-mapping evidence
only.

Passing R8-11B does not change `runtime_bindings.json`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
enable active graph calls to production services, and does not update public
transcript content. The default mainline remains provider-free and
external-HTTP-free.

## R8-12 Default-Off External Compute Demo Boundary

R8-12 introduces a demo bridge in the active executor, but the bridge remains
default-off and is not part of the default reset mainline. It can call
production `POST /v1/agent/compute` only when both of these are true:

- `ENABLE_EXTERNAL_COMPUTE_DEMO=1`
- `EXTERNAL_COMPUTE_DEMO_ALLOWLIST` contains one or more registered fixed DAG
  agent ids

With flags off or an empty allowlist, no bridge module is loaded and no
external HTTP call is made. The bridge never calls `/v1/agent/invoke`, never
uses dev endpoints as production evidence, and never changes
`runtime_bindings.json`.

R8-12 validation uses unit and integration tests with fake bridge transports.
The optional live demo smoke is manual demo acceptance and writes sanitized
artifacts under `/tmp/lma-r8-12-demo/`; it is not a default mainline gate and
does not prove production business correctness.

## R8-12B Local Remote-Agent Demo Tunnel Boundary

R8-12B adds local demo/dev SSH tunnel helpers and a runbook only. Validation
must not start the tunnel and must not call `/health`, `/v1/agent/compute`, or
`/v1/agent/invoke`. The scripts bind only `127.0.0.1`, use same-port forwards
for the R8-12 allowlist, and do not write `.env` or runtime binding files.

The allowlist example
`config/fixed_dag/external_compute_demo_allowlist.local.example.json` is a
documentation/config sample for developer setup. It is not runtime authority,
does not mark services live, and does not enable invoke by default.

## R8-12C Report Input Bundle Boundary

R8-12C is repository implementation work for report generation and public
workflow projection. It introduces `report_input_bundle_v1`, feeds it into
`build_report_result`, and exposes bounded `agent_evidence` /
`composite_evidence` summaries in `workflow_snapshot_v2.stepResults`.

The default reset mainline remains provider-free unless an existing test uses a
fake transport. R8-12C validation must not call production endpoints, must not
call `/v1/agent/invoke`, must not modify `runtime_bindings.json`, and must not
store raw external responses or endpoint URLs in graph state or Web fixtures.
Passing mainline means the public-safe report bundle and frontend projection
are contract-valid; it does not deploy the main system to production.

## R8-12D LLM Report Synthesis Boundary

R8-12D adds a default-off LLM report synthesizer for the final fixed-DAG
report. The synthesizer may call the configured chat model only when
`ENABLE_LLM_REPORT_SYNTHESIS=1` or `Context.enable_llm_report_synthesis=True`
is explicit. It receives only `report_input_bundle_v1` and must fail closed to
the template report if model loading, parsing, schema validation, or safety
checks fail.

Default static/mainline validation uses fake model transports only. It must not
call a real provider, must not call `/v1/agent/invoke`, must not call production
agent endpoints, must not write raw model output, and must not change runtime
bindings or live flags. A live demo may combine this flag with the R8-12
external compute demo flag, but that remains manual demo acceptance, not a
default quality gate.

## R8-13N L3 Explanation Static Coverage

R8-13N adds a default-off L3 LLM explanation seam. The default static quality
gate includes both the implementation module and its unit tests:

```powershell
python scripts/quality/run_quality.py --mode static
```

This static gate still uses fake model transports or provider-missing preflight
only. It must not call a real provider, production agent endpoint, demo stack,
or `/v1/agent/invoke`, and it must not change runtime bindings or live flags.

## R8-13D Sandbox L3 Backfill Handoff Boundary

R8-13D is a packaging and documentation gate. It may read sandbox artifacts,
read sandbox service copies, and write a handoff package under `/tmp`, but it
must not modify production service directories.

The package may include reviewable service patches and sanitized trace files.
It is not a production smoke result and is not runtime binding enablement.
Validation for this phase is repository static quality and diff hygiene only;
no endpoint call is required or allowed by the phase itself.

R8-13D does not call `/health`, `/v1/agent/compute`, or `/v1/agent/invoke`;
does not set live flags; does not update `runtime_bindings.json`; and does not
make sandbox L3 wrapper success a production readiness claim.

## R8-13E Production L3 Backfill Smoke Boundary

R8-13E is controlled production service work for the four L3 composite services
only. It may modify the protocol wrapper layer in those service directories,
run focused service tests, restart only ports `10015`, `10023`, `10016`, and
`10024`, and call production `/health` + `/v1/agent/compute` for those four
services.

R8-13E must not call `/v1/agent/invoke`, must not change
`runtime_bindings.json`, must not set `live_verified=true`, must not set
`invoke_enabled_by_default=true`, and must not enable default graph calls to
production services. Passing this phase proves controlled L3 protocol and
adapter mapping after backfill only.

## R8-13F End-to-End Trace QA Boundary

R8-13F is default-off demo QA for the fixed DAG production compute path. It may
run `scripts/dev/run_r8_13a_e2e_smoke.py` with explicit flags to call only
allowlisted loopback production `/v1/agent/compute` endpoints, pass bounded L2
`context.upstream_outputs` to L3 compute requests, and use the configured
report model when explicitly enabled.

R8-13F must not call `/v1/agent/invoke`, must not change
`runtime_bindings.json`, must not set `live_verified=true`, must not set
`invoke_enabled_by_default=true`, and must not store raw external responses,
endpoint URLs, credentials, traceback text, or provider raw output in the
repository.

Default static/mainline validation still does not call production endpoints,
providers, demo stacks, or `/v1/agent/invoke`. R8-13F E2E artifacts are manual
QA artifacts under `/tmp`, not default quality gate artifacts.

## R8-13G Value L2 Stance Remediation Boundary

R8-13G is controlled production service wrapper remediation for three value L2
valuation services. It may modify only service-side protocol wrapper files,
service-local tests, and service-local notes for
`value_traditional_valuation`, `value_ml_valuation`, and
`value_meta_valuation`; it must not modify valuation models, feature
engineering, scoring algorithms, data files, deployment configuration, runtime
bindings, or live flags.

R8-13G may restart only the affected production service ports and may call
production `/health` + `/v1/agent/compute` for those services. It must not call
`/v1/agent/invoke`. The E2E trace may use the default-off external compute
demo bridge and configured report model only under explicit flags.

Default static/mainline validation still does not call production endpoints,
providers, demo stacks, or `/v1/agent/invoke`. R8-13G artifacts are manual
readiness/demo artifacts under `/tmp`, not default quality gate artifacts.

## R8-8P-DOCS-QA Documentation Boundary

R8-8P-DOCS-QA is docs-only. It deepens the production matrix and developer
prompt catalog into remediation playbooks, but it does not call production or
dev endpoints, does not modify service code, does not change adapter logic, and
does not change runtime bindings or live flags.

Default mainline still does not run production smoke, external
`/v1/agent/invoke`, provider live checks, demo stacks, or fusion-gate. Passing
static/mainline after R8-8P-DOCS-QA means maintained repository docs and code
quality still pass; it does not mean any production service has been remediated
or newly verified.

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

## R8-8I Broaden Controlled Compute Evidence Boundary

R8-8I broadens the same dev-only controlled health and compute smoke pattern to
the L1 and remaining macro/market L2 candidate queue. Docs are updated only for
candidates that pass health, compute, and provider-free adapter mapping. In this
phase, `sentiment_company_radar` passed as market-only L2 evidence after bounded
service-side protocol remediation; it does not create or imply a risk route.

Allowed service-side remediation remains limited to fixed-DAG identity,
structured health JSON, compute envelope fields, and canonical adapter-facing
dimensions. Main-system runtime bindings, live flags, graph, executor, public
API, public runtime, public mapping, frontend, fixed DAG roster, L3/L4 active
runtime, and the main-system adapter identity gate remain unchanged.

R8-8I main-repo validation gate is:

```powershell
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing R8-8I validation means the documentation-only evidence record remains
consistent with reset quality. It does not mean `/v1/agent/invoke` was called,
runtime bindings are enabled, `live_verified=true` is set,
`invoke_enabled_by_default=true` is set, risk routing is enabled, L3/L4 active
runtime integration is enabled, production readiness is proven, or any candidate
may be invoked by default.

## R8-8J Controlled Compute Evidence Expansion Boundary

R8-8J expands the dev-only controlled health and compute smoke pattern to
`financial_data_service` as L1 data-service evidence. The phase permits bounded
service-side remediation for structured health JSON and an
`external_agent_compute_v0` compute wrapper with a concrete `data_bundle_v1`
tool result. It also permits the main-system adapter to add the provider-free
pure mapping branch for that compute-envelope input.

R8-8J does not change runtime bindings, graph, executor, public API, public
runtime, public mapping, frontend, fixed DAG roster, L3/L4 active runtime, or
default invocation behavior. Docs are updated only after health, compute, and
provider-free adapter mapping pass.

R8-8J main-repo validation gate is:

```powershell
python -m ruff check src/react_agent/fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_adapter.py
python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py -q
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing R8-8J validation means the documentation-only evidence record and
provider-free adapter mapping branch remain consistent with reset quality. It
does not mean `/v1/agent/invoke` was called, runtime bindings are enabled,
`live_verified=true` is set, `invoke_enabled_by_default=true` is set, active
graph L1 data integration is enabled, production readiness is proven, or any
candidate may be invoked by default.

## R8-8K Entity And Risk Controlled Compute Evidence Boundary

R8-8K expands the dev-only controlled health and compute smoke pattern to L1
entity-relation evidence and risk L2 gate-member evidence. The phase permits
bounded service-side remediation for structured health JSON, fixed-DAG identity,
canonical risk dimensions, `agent_conclusion_v1 role=gate_member`, and an
`external_agent_compute_v0` compute wrapper with a concrete
`entity_relation_bundle_v1` tool result. It also permits the main-system adapter
to add the provider-free pure mapping branch for that entity-relation
compute-envelope input.

R8-8K does not change runtime bindings, graph, executor, public API, public
runtime, public mapping, frontend, fixed DAG roster, L3/L4 active runtime, or
default invocation behavior. Docs are updated only after health, compute, and
provider-free adapter mapping pass.

R8-8K main-repo validation gate is:

```powershell
python -m ruff check src/react_agent/fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_external_adapter.py
python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py -q
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing R8-8K validation means the documentation-only evidence record and
provider-free adapter mapping branch remain consistent with reset quality. It
does not mean `/v1/agent/invoke` was called, runtime bindings are enabled,
`live_verified=true` is set, `invoke_enabled_by_default=true` is set, active
graph L1 entity integration is enabled, L3 risk composite integration is
enabled, L4 decision integration is enabled, production readiness is proven, or
any candidate may be invoked by default.

## R8-8L Remaining Risk And Market Controlled Compute Evidence Boundary

R8-8L expands the dev-only controlled health and compute smoke pattern to the
remaining bounded risk L2 candidates that can emit `agent_conclusion_v1
role=gate_member`. The phase permits bounded service-side remediation for
fixed-DAG identity, canonical risk dimensions, and risk-score exposure at the
service wrapper boundary. It does not permit forcing L3 `risk_conclusion_v1`,
dimension-composite payloads, macro payloads, or wider market protocol drift
into L2 contracts.

R8-8L does not change runtime bindings, graph, executor, public API, public
runtime, public mapping, frontend, fixed DAG roster, L3/L4 active runtime, or
default invocation behavior. Docs are updated only after health, compute, and
provider-free adapter mapping pass.

R8-8L main-repo validation gate is:

```powershell
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing R8-8L validation means the documentation-only evidence record remains
consistent with reset quality. It does not mean `/v1/agent/invoke` was called,
runtime bindings are enabled, `live_verified=true` is set,
`invoke_enabled_by_default=true` is set, L3 risk composite integration is
enabled, L4 decision integration is enabled, production readiness is proven, or
any candidate may be invoked by default.

## R8-8M Remaining L2 Controlled Compute Coverage Boundary

R8-8M expands the dev-only controlled health and compute smoke pattern to the
remaining bounded L2 candidates that can emit `agent_conclusion_v1` without
changing business logic. The phase permits bounded service-side remediation for
fixed-DAG identity, external service id preservation, canonical dimensions, and
safe dev-only service start when the root and command are explicit. It does not
permit forcing L3 macro/regulator payloads, dimension-composite payloads, or
larger scaffold/business outputs into L2 contracts.

R8-8M does not change runtime bindings, graph, executor, public API, public
runtime, public mapping, frontend, fixed DAG roster, L3/L4 active runtime, or
default invocation behavior. Docs are updated only after health, compute, and
provider-free adapter mapping pass.

R8-8M main-repo validation gate is:

```powershell
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing R8-8M validation means the documentation-only evidence record remains
consistent with reset quality. It does not mean `/v1/agent/invoke` was called,
runtime bindings are enabled, `live_verified=true` is set,
`invoke_enabled_by_default=true` is set, L3 market composite integration is
enabled, L4 decision integration is enabled, production readiness is proven, or
any candidate may be invoked by default.

## R8-10B L3 Adapter Pure Mapping Boundary

R8-10B adds unit-tested, provider-free pure adapter mappings for
`dimension_conclusion_v1`, `risk_conclusion_v1`, and `macro_conclusion_v1`.
The quality gate is code/static/unit validation only. It does not call
`/health`, `/v1/agent/compute`, `/v1/agent/invoke`, production ports, dev
ports, providers, or demo stacks.

R8-10B validation is:

```powershell
python -m ruff check src/react_agent/fixed_dag_external_adapter.py src/react_agent/fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_contracts.py
python -m pytest tests/unit_tests/test_fixed_dag_external_adapter.py tests/unit_tests/test_fixed_dag_contracts.py -q
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing this gate means only that already-available L3 payload dictionaries can
map locally into `dimension_composite_result_v1`. It does not enable runtime
bindings, set live flags, prove L3 service readiness, wire active graph L3
external execution, or permit default invocation.

## R8-10C L3 Service Backfill Audit Boundary

R8-10C is docs-only and read-only with respect to services. It may inspect
process metadata and shallow service source/docs, but it does not call
`/health`, `/v1/agent/compute`, `/v1/agent/invoke`, production ports, dev
ports, providers, or demo stacks. It does not modify service code.

R8-10C validation is:

```powershell
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing this gate means only that the L3 protocol backfill findings and service
owner prompts are documented. It does not create L3 health/compute evidence,
enable runtime bindings, set live flags, prove production readiness, or permit
default invocation.

## R8-10D L3 Service Wrapper Backfill Boundary

R8-10D modifies only the protocol wrapper layer in the four L3 service
directories and updates main-repo docs. It does not modify main-system `src/`,
`config/`, runtime bindings, graph, executor, public API/runtime/mapping, or
frontend code. It does not call `/health`, `/v1/agent/compute`,
`/v1/agent/invoke`, providers, prod/dev endpoints, or demo stacks, and it does
not restart services.

Service validation is limited to changed-file `py_compile` and focused local
pytest cases that exercise wrapper functions or in-process FastAPI handlers
with monkeypatched compute cores. These tests do not create L3 readiness
evidence; they only show that the local wrapper code is syntactically valid and
contract-shaped.

Main-repo validation remains:

```powershell
python scripts/quality/run_quality.py --mode static
git diff --check
python scripts/quality/run_quality.py --mode mainline
```

Passing this gate means the wrapper backfill has been documented and the main
repo remains healthy. It does not enable runtime bindings, set live flags, prove
L3 production readiness, or permit default invocation. Controlled L3 endpoint
smoke remains R8-10E.

## R8-10D-SNAPSHOT L3 Service Shadow Handoff Boundary

R8-10D-SNAPSHOT creates a local handoff repository at
`/sdb/dlut/service-shadow-repos/l3-composite-services` because the formal L3
service source repositories are not available in this environment. The shadow
repo stores service notes, the R8-10D manifest, and zero-context protocol patch
files only. It deliberately avoids mirroring full production directories,
runtime state, virtual environments, data, models, logs, and secret-bearing
deployment material.

This is a documentation and handoff control, not a runtime or readiness gate.
It does not call endpoints, restart services, enable runtime bindings, set live
flags, or create L3 smoke evidence. R8-10E still owns controlled L3 endpoint
verification after service owners confirm deployment or restart status.

## R8-10E L3 Production Controlled Smoke Boundary

R8-10E is manual/live readiness work for the four L3 production services only.
It is not part of default mainline and must remain outside normal CI. The
allowed endpoint calls are limited to production `GET /health` and
`POST /v1/agent/compute` for `10015`, `10016`, `10023`, and `10024`; it does
not call `/v1/agent/invoke`.

Passing this smoke records compute-level evidence only. It does not enable
runtime bindings, set `live_verified=true`, set
`invoke_enabled_by_default=true`, or prove production default invocation.

## R8-10F Value Composite Production Remediation Boundary

R8-10F is a scoped production remediation and smoke for `value_composite` on
port `10015` only. It may update the service protocol wrapper, restart that
single production service, and call production `GET /health` plus
`POST /v1/agent/compute` for that service. It must not call
`/v1/agent/invoke`, use dev ports as production evidence, or touch unrelated
services.

Passing this remediation records compute-level evidence only. It does not
enable runtime bindings, set `live_verified=true`, set
`invoke_enabled_by_default=true`, or prove production default invocation.

## R8-8Q Production L1/L2 Remediation Re-smoke Boundary

R8-8Q is manual/live readiness work for selected production L1/L2 services. It
is not part of default mainline and must remain outside normal CI. The allowed
endpoint calls are limited to confirmed production `GET /health` and
`POST /v1/agent/compute` for the named candidates; the phase must not call
`/v1/agent/invoke`, use dev endpoints as production evidence, or touch runtime
bindings.

Passing this remediation records compute-level evidence only. It does not
enable runtime bindings, set `live_verified=true`, set
`invoke_enabled_by_default=true`, prove production default invocation, or make
the active graph call production services by default.

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

## SYNC-OPS-1R Planner Safety Gate

SYNC-OPS-1R extends the read-only sync planner quality surface. Default static
and mainline gates may run schema, canonical hash, filesystem safety, inventory,
diff, P2S plan, CLI, archive-entry, and repo-external temp-root integration
tests. These tests must not write production, sandbox, owner-dev, or configured
artifact-store paths.

Required safety assertions include:

- old unsafe P2S plans fail validation;
- P2S stage roots are new versioned baseline paths, not active sandbox paths;
- ordinary copy actions have non-empty source hashes;
- backup/runtime-noise files are excluded;
- sanitized derivatives are preserved or blocked, never raw-replaced;
- all 26 external agents receive explicit dispositions;
- archive entry paths use POSIX `/`.

Future P2S stage/activate, S2P apply, lock acquisition, process action, and
endpoint smoke remain explicit live/write gates and are not part of default
mainline.

## SYNC-OPS-1R2 Recursive Coverage Gate

SYNC-OPS-1R2 expands the planner quality surface with recursive source
inventory, root/subroot preservation, historical baseline parity, current prod
coverage, stage projection digest, and temp-only reconstruction tests. These
tests may write repo-external `/tmp` materialization trees but must not write
production, sandbox, owner-dev, configured artifact-store, approval, lock,
backup, stage, activate, endpoint, or process state.

Required assertions include:

- nested packages, tests, configs, runbooks, `.gitignore`, HTML/CSS, and small
  text resources are recursively included when policy-safe;
- excluded directories are pruned before traversal;
- every historical baseline row has a terminal disposition;
- every current production inventory row has a terminal disposition;
- unresolved coverage is zero before an approval request is emitted;
- temp reconstruction digest matches the plan projection digest;
- duplicate stage destinations, raw secret findings, and backup/runtime-noise
  materialization are rejected.

## SYNC-OPS-2A P2S Writer Dry-Run Gate

SYNC-OPS-2A adds the writer contract to the maintained quality surface while
keeping all real server paths out of default mainline. Tests may create
repo-external `/tmp` approval, lock, artifact-store, stage, active, archive,
and rollback fixtures. They must not create `/sdb/dlut/ops-artifacts`, write
real prod/sandbox/owner-dev trees, call endpoints, or operate processes.

Required assertions include:

- approval records bind exact plan SHA and environment snapshot SHA;
- stage, activate, and rollback approvals are checked independently;
- global and transaction locks reject conflicts and wrong-owner release;
- artifact writes are atomic, relative, hashed, and path-traversal safe;
- P2S stage verifies planned source hashes, projection digest, secret scan, and
  validation profile;
- activation uses an independent candidate and reports zero hard links;
- rollback restores the archive and preserves the failed active tree;
- recovery journal state classifies resume versus rollback-required points.

## SYNC-OPS-2A-R1 Source Policy Gate

SYNC-OPS-2A-R1 extends the maintained quality surface with source-selection
regressions and full-scale temp rehearsal:

- hidden local/editor metadata, backup-pattern directories, generated
  artifacts, experiment results, reports, outputs, data assets, model assets,
  runtime noise, and sensitive files are excluded or blocked by role;
- no `copy_from_prod` action may carry `not_scanned`, unknown, sensitive, or
  non-materializable source categories;
- runtime static assets and test fixtures require explicit manifest evidence;
- no-extension files are sniffed and secret-scanned before classification;
- the actual current P2S plan must rehearse stage, verify, activate, rollback,
  no-hardlink check, secret scan, py_compile profile, and recovery in `/tmp`;
- real prod, sandbox, owner-dev, artifact-store, approval, lock, backup, stage,
  activation, endpoint, process, and env-value state remain untouched.

## SYNC-OPS-2A-R2 Executable Contract Gate

SYNC-OPS-2A-R2 adds executable-plan and staged-approval regressions:

- old read-only P2S plans fail validation with legacy marker and rollback
  skeleton blockers;
- new P2S plans include an executable writer contract and rollback contract;
- stage-only approval validates stage and verify but is rejected by activate;
- artifact-store preflight is read-only and exposes initialization blockers;
- transaction actions and Agent actions must match;
- one structured summary feeds plan, closeout, CLI, and terminal counts;
- full-scale temp rehearsal proves stage, verify, stage-only activate
  rejection, activation, rollback, no-hardlink, and digest checks.

Default gates still must not write real prod, sandbox, owner-dev, configured
artifact-store, approval, lock, stage, activation, endpoint, process, or
environment-value state.

## SYNC-OPS-2A-R3 Artifact-Store Bootstrap Gate

SYNC-OPS-2A-R3 adds bootstrap-specific quality coverage:

- bootstrap plans contain only exact `mkdir_exact` actions and one metadata
  write;
- plan, approval, and environment hashes are checked before bootstrap;
- bootstrap is idempotent when the store metadata is already valid;
- rollback removes only empty paths created by the same bootstrap run;
- non-empty store rollback is rejected;
- P2S stage rejects unbootstrapped stores before run artifact creation;
- temp rehearsal covers bootstrap, verify, idempotency, recovery, rollback,
  and P2S before/after-bootstrap behavior.

Default gates still must not create `/sdb/dlut/ops-artifacts`, write prod,
sandbox, owner-dev, real approvals, real locks, real stages, endpoints,
process state, or environment values.

## SYNC-OPS-2A-R4 Bootstrap Rollback Atomicity Gate

SYNC-OPS-2A-R4 extends bootstrap quality coverage with atomic rollback and
archive portability regressions:

- non-empty store rollback is a global no-op with `mutation_count=0`;
- blocked rollback leaves before/after tree listings unchanged;
- rollback deletes only paths present in the same-run ownership ledger;
- unknown files, foreign metadata, missing ledgers, and populated standard
  store directories all block rollback before any deletion;
- approval requests cannot satisfy the machine approval validator;
- approval requests use `requested_action_ids`, while approvals use
  `approved_action_ids`;
- ZIP/TAR artifact entry names are POSIX-only and reject backslashes,
  absolute paths, traversal components, duplicate normalized names, and
  symlink entries.

Default gates still must not create `/sdb/dlut/ops-artifacts`, write prod,
sandbox, owner-dev, real approvals, real locks, real bootstrap state, real
stages, endpoints, process state, or environment values.

## SYNC-OPS-2B0-R1 Durable Bootstrap Gate

SYNC-OPS-2B0-R1 records the one approved real bootstrap boundary:

- bootstrap plan hash and environment binding hash are independently
  recomputed before approval;
- machine approval binds both hashes and exact action ids;
- the request object remains invalid as an approval;
- only the ten approved directories and `STORE_METADATA.json` are written;
- verification checks modes, metadata, ownership ledger, unexpected paths, and
  secret findings;
- P2S replan is read-only and produces only an awaiting stage/verify request.

Default gates still must not write prod, sandbox, owner-dev, run P2S stage or
activation, update the baseline pointer, call endpoints, operate processes, or
read environment values.

## SYNC-OPS-2B1 Real Stage Verify Gate

SYNC-OPS-2B1 adds the first real versioned-stage verification evidence:

- plan, frozen environment, current environment, artifact store, machine
  approval, and source preflight are validated before stage creation;
- source preflight requires 1582 actions, 1581 physical writes, one shared
  noop, zero source drift, zero duplicate destinations, zero sensitive ordinary
  copies, zero `not_scanned` copies, and coverage ratio `1.0`;
- stage verify requires expected and actual projection digests to match, zero
  secret findings, zero hard compile failures, zero unexpected files, and zero
  source-stage hardlinks;
- compile validation writes bytecode to a `/tmp` cache, not into the versioned
  stage tree;
- active sandbox tree SHA and baseline pointer SHA must be unchanged after
  stage/verify.

Default gates still must not activate, roll back active sandbox state, update
the baseline pointer, call endpoints, operate processes, read environment
values, or write prod/owner-dev.

## SYNC-OPS-2B0 Bootstrap Execution Guard

SYNC-OPS-2B0 keeps the artifact-store bootstrap executor in the maintained
quality surface:

- real bootstrap execution fails closed when the current environment snapshot
  SHA differs from the plan-bound SHA;
- no machine approval is created for a stale environment;
- metadata payload construction supports a single final atomic
  `STORE_METADATA.json` replace with ownership ledger data present;
- stale bootstrap attempts leave real artifact-store, prod, sandbox,
  owner-dev, approval, lock, stage, endpoint, process, and environment-value
  state untouched.
- SYNC-OPS-2A-R5 supersedes exact full-snapshot binding for future bootstrap
  approvals with stable environment binding plus execution constraints.

## SYNC-OPS-2A-R5 Stable Environment Binding Gate

SYNC-OPS-2A-R5 adds bootstrap environment-binding regressions:

- exact free-space changes above the configured threshold do not invalidate
  approval;
- free space below `minimum_free_bytes` fails as a constraint, not as binding
  drift;
- owner-based access ignores unrelated supplementary-group observation drift;
- uid, mode, device, inode, path-state, symlink, access-basis, and relevant
  group drift still fail closed;
- legacy volatile environment snapshot contracts are rejected;
- `agent-sync environment explain-binding` exposes exact-bound, constraint,
  and diagnostic-only fields without writing real server paths.

Default gates still must not create `/sdb/dlut/ops-artifacts`, write prod,
sandbox, owner-dev, real approvals, real locks, real bootstrap state, real
stages, endpoints, process state, or environment values.
