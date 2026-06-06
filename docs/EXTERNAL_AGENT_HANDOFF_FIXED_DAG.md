# Fixed DAG External Agent Handoff

This document is the entry point for developers who want to connect a business
agent to the current fixed DAG reset system.

It standardizes the integration boundary. It does not require every agent to
use the same internal implementation mode. A service may be implemented as a
machine-learning model, a rule system, a data service, an LLM agent, an LLM with
tools, or a hybrid system. The integration gate is whether the service exposes
the agreed boundary, returns payloads that the main-system adapter can map to
fixed DAG contracts, and passes the readiness ladder.

## Current System Mental Model

The active runtime is the fixed DAG reset skeleton:

```text
user input
  -> route_planner
  -> prepare_l1_context
  -> execute_fixed_dag
  -> final_emit
  -> memory_update
```

The current system facts are:

- The active catalog source is `config/fixed_dag/agent_catalog.json`.
- The active runtime binding source is `config/fixed_dag/runtime_bindings.json`.
- The active contract source is `src/react_agent/fixed_dag_contracts.py`.
- The active executor source is `src/react_agent/fixed_dag_executor.py`.
- The reset roster has 27 formal `snake_case` agent ids: L1=3, L2=18, L3=4,
  L4=2.
- External HTTP candidates are disabled by default and are not live verified.
- The reset mainline does not call providers or external `/v1/agent/invoke`
  endpoints.

The old `AGENT_TOOLS`, `config/agents/*.json`, and aNN ids are retained only as
legacy migration references. They are not the current fixed DAG handoff truth.

## Responsibilities

External agent developers own:

- Implementing and operating their own business service.
- Choosing the internal implementation mode.
- Providing `GET /health`.
- Providing `POST /v1/agent/invoke`.
- Providing `POST /v1/agent/compute` when the service needs backtest,
  batch, or point-in-time validation.
- Returning safe structured payloads with no secrets, no raw traceback, no raw
  provider response, and no chain-of-thought.
- Supplying sample requests, sample responses, evidence fields, data timestamps,
  known limitations, and local test results.

Main-system maintainers own:

- Choosing the target fixed DAG `agent_id`.
- Recording the external service id in `runtime_bindings.external_agent_id`.
- Writing or updating the adapter that maps external payloads into fixed DAG
  contracts.
- Keeping `invoke_enabled_by_default=false` until explicit readiness approval.
- Keeping `live_verified=false` until a live gate has been run and recorded.
- Ensuring public transcript output remains user/assistant only.

## ID Namespaces

Use three separate id namespaces in service schemas and samples:

| Field | Owner | Meaning |
| --- | --- | --- |
| `agent_id` | main system | Primary current fixed DAG id from `config/fixed_dag/agent_catalog.json`, such as `value_ml_valuation`. |
| `external_agent_id` | external service | Service id returned by `/health`, `/v1/agent/compute`, and `/v1/agent/invoke`, such as `valuation_ml`. |
| `legacy_agent_id` | main system | Optional migration note in `runtime_bindings.json`, such as `a16_ml_valuation`; never a primary current id. |

Do not use an aNN id as the active fixed DAG primary id. If `main_agent_id` is
mentioned, it must appear only in migration notes, not in the new request
schema or sample primary path.

## Choosing A Target Agent

1. Read `config/fixed_dag/agent_catalog.json`.
2. Pick the target `id` whose layer, dimension, role, input contract, and output
   contract match the service.
3. Check `config/fixed_dag/runtime_bindings.json` for the current binding
   status.
4. If the binding is `external_http_candidate`, it can enter readiness work but
   remains disabled until explicit approval.
5. If the binding is `pending_placeholder`, the service needs a new mapping
   decision before any live integration work.
6. If the binding is deterministic composite, decision, or report, treat it as
   a system seam rather than a normal external service target.

`sentiment_company_radar` belongs to the market dimension and routes only to
`market_composite`. It must not be used as a direct `risk_composite` input.

## Required Service Boundary

Minimum endpoint boundary:

```text
GET  /health
POST /v1/agent/invoke
```

Recommended point-in-time endpoint:

```text
POST /v1/agent/compute
```

The service should accept `external_agent_request_v0`-style requests and return
`external_agent_response_v0`-style responses. The main system adapter is
responsible for mapping those responses to fixed DAG contracts.

The service should support:

- `request_id`
- `status`
- `warnings`
- `errors`
- `confidence`
- `as_of`
- `data_as_of`
- `evidence`
- `event_flags` where relevant
- a structured `tool_result`

## Current Wrapper Compatibility Boundary

This scaffold defines the target fixed DAG handoff contract for new external
services. Existing repo compatibility wrappers may still construct compact
legacy-shaped payloads, including `main_agent_id` in context, until a later R8
adapter implementation replaces or bridges that path.

External developers should implement the fixed DAG scaffold contract documented
here and in `examples/fixed_dag_external_agent_scaffold/`. They should not
infer the target handoff contract from legacy wrapper files and should not add
`main_agent_id` to the new request schema. Main-system maintainers own any
adapter bridge between legacy wrapper compatibility payloads and this fixed DAG
scaffold contract.

## R7-C Source Package And Repo Mirror

R7-C upgrades the original repo-external source package in place:

```text
E:\muti-agent\external_agent_scaffold
```

The upgraded package is mirrored into the repo for review and versioned docs:

```text
examples/fixed_dag_external_agent_scaffold/
```

Use the repo path as the tracked canonical copy when reviewing changes. Use the
repo-external path as the distribution/source package for zip handoff. The
scaffold is for developer handoff and local contract tests only. It is not
registered in `react_agent.graph`, not listed as an active runtime package, and
not connected to `config/fixed_dag/runtime_bindings.json`.

The scaffold demonstrates:

- fixed DAG primary `agent_id`, such as `value_ml_valuation`
- external service `external_agent_id`, such as `valuation_ml`
- optional `legacy_agent_id` as a migration note only
- `GET /health`
- `POST /v1/agent/compute`
- `POST /v1/agent/invoke`
- a deterministic `compute_core` shared by compute and invoke
- `as_of`/`data_as_of`, evidence, confidence, event flags, typed errors, and
  fail-soft behavior

The sample rejects old aNN ids when they are used as the primary `agent_id`.
It does not use the old `main_agent_id` request field.

Developers may copy the scaffold shape, but they must replace the deterministic
sample business logic with their own service implementation and pass the
readiness ladder before any live integration can be considered.

## AI Coding Handoff For Developer Projects

R7-E expands the scaffold package's `AI_CODING_HANDOFF.md` for Codex, Claude
Code, or another coding agent adapting a developer-owned agent project.

Use it when a developer provides:

- the scaffold package
- an existing agent project
- a target fixed DAG `agent_id`
- optional `external_agent_id` and `legacy_agent_id`
- sample inputs, outputs, model files, data files, or owner notes

The AI coding handoff tells the coding agent to audit first, preserve the
business core, add a minimal fixed DAG service wrapper, implement `/health`,
`/v1/agent/compute`, and `/v1/agent/invoke`, add local contract tests, and
return a maintainer handoff bundle. It does not authorize runtime binding
changes, live invocation, or main-system runtime edits.

## What To Submit

Submit a handoff bundle with:

- Target fixed DAG `agent_id`.
- External `external_agent_id`.
- Optional migration-only `legacy_agent_id`.
- Health sample response.
- Invoke sample request and response.
- Compute sample request and response when applicable.
- Explanation of `tool_result` fields.
- Evidence and data source policy.
- Point-in-time policy for `as_of` and `data_as_of`.
- Known limitations and degraded/partial behavior.
- Local no-provider test commands and results.
- Optional `implementation_notes` describing whether the service is ML, rules,
  data service, LLM, tool-calling, or hybrid. This is not an integration gate.

Do not submit real secrets, API keys, endpoint credentials, raw provider
responses, raw traceback, chain-of-thought, or private user data.

## What Cannot Change In This Handoff

External service handoff does not change:

- the 27-agent fixed DAG roster
- `config/fixed_dag/agent_catalog.json`
- fixed DAG topology
- public transcript role rules
- provider readiness
- live external readiness
- production deployment status

It also does not restore:

- `value_financial_analysis`
- a 28-agent roster
- old route modes
- old Router-SFT or RARP/route-prior authority
- old Agent Catalog v2 authority
- old `AGENT_TOOLS` or `config/agents/*.json` as active fixed DAG truth

## Historical Scaffold Lineage

The historical `external_agent_scaffold_v2.2.1.zip` package was useful for
transport, endpoint, safety, `as_of`/`data_as_of`, evidence, event flag,
confidence, idempotency, graceful-degradation, and performance ideas.

R7-C migrates that lineage into the current fixed DAG scaffold package. The
current package replaces `main_agent_id` and old aNN primary ids with fixed DAG
`agent_id` values and keeps old aNN ids only as `legacy_agent_id` migration
notes. The package must not be copied into the active runtime or treated as
live-readiness evidence.
