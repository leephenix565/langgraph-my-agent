# Current Status

This is the current operational status entry for the Fixed DAG reset branch.
Use it for status and roadmap orientation before reading historical phase
records.

## Source Authority

- Branch: `reset/fixed-dag-v1`.
- Source authority: the current Git HEAD in `/sdb/dlut/dev/langgraph-my-agent`.
- Reset lineage anchor: `pre-fixed-dag-reset-20260604-1457`.
- This document intentionally avoids short-lived process identifiers and raw
  endpoint payloads.

## Runtime And Catalog

- The active graph remains `langgraph.json -> src/react_agent/graph.py:graph`.
- The formal catalog has 27 fixed DAG agent ids from
  `config/fixed_dag/agent_catalog.json`.
- Runtime binding authority remains
  `config/fixed_dag/runtime_bindings.json`.
- L4 `decision_synthesizer` and `report_generator` are the current
  compute-default external bindings. This is a compute path, not an invoke
  path.
- `default_external_invoke_enabled=false` remains the runtime-binding default.
  The two L4 compute-default rows also keep `invoke_enabled_by_default=false`.
- Non-L4 production external compute is governed by
  `config/fixed_dag/non_l4_external_compute_policy.json`, not by
  `runtime_bindings.json`. The policy is currently `enabled_by_default=true`
  and compute-only. Required enabled ids remain
  `value_traditional_valuation`, `value_ml_valuation`,
  `value_meta_valuation`, `market_ipo_investor_behavior`,
  `market_capital_flow_chip`, `risk_crash`, `macro_analysis`,
  `macro_index_valuation`, and `value_composite`. RQ3A adds optional enabled
  coverage rows for `value_research_synthesis`, `market_stock_technical`,
  `sentiment_company_radar`, `risk_financial_fraud`,
  `risk_identification`, `risk_compliance_review`,
  `macro_commodity_pricing`, `market_composite`, `risk_composite`, and
  `macro_composite`.

## Report Quality RQ2E Status

- Current target: `REPORT-QUALITY-RQ2E Controlled Online E2E Verification After
  Main-System Sync`.
- RQ2E live at commit `12faf7635a9e29b3392ca8c64e83924c0fbb2f4e` completed
  safely but scored `27/45`; RQ3A treats this as a production coverage and
  report-projection gap, not as sandbox drift or a reason to accept sandbox demo
  output.
- RQ2E is allowed only after preflight shows dev/prod/sandbox at the same
  approved HEAD, clean worktrees, matching catalog/runtime/non-L4 policy
  digests, authority docs in sync, and checksum-verifiable input artifacts.
- RQ2E acceptance uses the report-quality audit output for the controlled
  online E2E artifact: score `>=29/45`, `renderer_quality_gate.passed=true`,
  unsafe scan pass, `template_phrase_count<=8`,
  `answer_section_parity.parity_ratio>=0.90`, and
  `traceability.traceability_ratio>=0.85`.

## Sync Workflow Status

- The bidirectional agent sync validation topic is complete.
- The strict one-command publish-and-rebase workflow is operational.
- Final strict cycle: `cycle_strict_e7bc707d5b8b`.
- Current active external-agent baseline:
  `first-cycle-p2s_52d75b56543f`.
- Durable final cycle run:
  `/sdb/dlut/ops-artifacts/agent-sync/runs/run_cycle_strict_cycle_strict_e7bc707d5b8b_20260625T135349Z`.
- Future non-zero work should use the normal experiment workflow: fork an
  immutable baseline, register exact change units, generate exact S2P/P2S
  children, request machine approval, then execute the approved strict cycle.

## Repository Roles

- `/sdb/dlut/dev/langgraph-my-agent` is the main-system development authority.
- `/sdb/dlut/prod/langgraph-my-agent` is a runtime/deployment copy, not a source
  authority.
- `/sdb/dlut/sandbox/*` holds experiments and immutable baselines. The active
  baseline is not edited in place.
- External owner-dev repositories are read-only to this workflow unless a
  separate owner workflow grants write authority.

## Current Engineering Theme

Repository Authority & Active-Core Consolidation is complete. The final
closeout is `docs/REPOSITORY_CONSOLIDATION_CLOSEOUT.md`.

M4A found P4 count `0`, so M4B deletion implementation is skipped. Current
mode returns to normal maintenance and product engineering on top of the fixed
DAG, strict sync workflow, consolidated docs authority, active-core package
boundaries, and Context/State compatibility metadata. No field deletion, public
contract change, graph topology change, catalog change, or runtime binding
change is part of this closeout.

## Current Non-Claims

- Passing static or mainline quality is not production readiness by itself.
- Current docs do not add runtime bindings, live flags, process actions, or
  provider calls.
- Default validation and sync quality gates do not call `/v1/agent/invoke`.
- RQ2E authority and preflight work does not call `/v1/agent/invoke`, make a
  provider direct call, start/stop/signal services, retain raw service/provider
  responses, or read env values.
- Compute evidence must not be recorded as invoke evidence. `externalInvoked`
  and invoke-default flags are `/v1/agent/invoke` claims only; they are not
  proof that no `/v1/agent/compute` call occurred in a later explicit live
  verification phase.
- The smoke/evidence ledgers in `docs/history/` are historical evidence, not
  runtime or configuration authority.
- Public transcripts must not expose secrets, raw graph messages, provider raw
  responses, manager assignment internals, or agent JSON.

## Evidence And History

- Start with `docs/INDEX.md` for the current reading order.
- Historical phase ledgers live under `docs/history/` and are indexed by
  `docs/history/MANIFEST.json`.
- Sync operator procedures live in
  `docs/AGENT_SYNC_ONE_COMMAND_WORKFLOW.md` and
  `docs/CODEX_AGENT_SYNC_OPERATOR_WORKFLOW.md`.
