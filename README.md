# langgraph-my-agent

This branch is the Fixed DAG reset branch. It replaces the old route-mode,
Router-SFT, route-prior, A01 contract dispatch, and Fair Fusion mainline with a
smaller deterministic fixed-DAG runtime skeleton.

R8-13H ports the sandbox-validated A-class integration slice into the
default-off demo path. It extends the external compute demo bridge so L1
`financial_data_service` and
`entity_relation_extractor` results can be mapped before L2 task construction,
and it adds sandbox registry entries for macro L2 `macro_commodity_pricing` and
`macro_index_valuation`. This is not production readiness evidence: it does not
call `/v1/agent/invoke`, does not modify `runtime_bindings.json`, does not set
live flags, and does not enable default external invocation.

Repository operations now use an explicit three-directory convention:
`/sdb/dlut/dev/langgraph-my-agent` is the main-system development authority,
`/sdb/dlut/sandbox/langgraph-my-agent-r8-a-class` is an experiment area, and
`/sdb/dlut/prod/langgraph-my-agent` is the runtime/deployment copy. See
`docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md` for the directory roles, sync policy,
documentation authority map, and external-agent repository ownership boundary.
Other agent repositories under `/sdb/dlut/dev/*` remain owned by their
developers; user sandbox agent experiments and developer-owned dev-agent
changes are synchronized to prod through separate owner-controlled flows.

The current next-phase roadmap is centralized in
`docs/NEXT_PHASE_ROADMAP_FIXED_DAG.md`. Use it as the first planning entry
point for new Codex sessions: it summarizes current progress, A/B/C agent work
classes, near-term end-to-end trace priorities, production compute/invoke
boundaries, and which docs should be compacted later.

CS1-C1X records the first accelerated post-backfill convergence wave. It adds
a source-controlled health identity validator, enforces request-`as_of`
anti-lookahead checks before external compute results enter DAG state, applies
scoped production wrapper patches for `market_stock_technical`,
`macro_analysis`, `market_ipo_investor_behavior`, and `value_composite`,
recovers the two L4 compute-only listeners, and writes sanitized artifacts under
`/tmp/lma-cs1c1x-bulk-remediation-20260622T081402Z`. It does not call external
invoke, does not change runtime bindings, does not set live flags, and does not
change business models or scoring logic.

CS1-C2X closes the C1X public-turn and temporal trace gaps. The external
compute bridge now projects requested `as_of` through compatible aliases,
workflow provenance avoids unsafe endpoint literals before artifact scrub, four
temporal-rejected services and the IPO compute wrapper were repaired, and
`market_capital_flow_chip` plus `market_composite` listeners were restored.
The sanitized trace artifacts live under
`/tmp/lma-cs1c2x-temporal-market-public-20260622T092218Z`. This remains a
controlled compute-only phase: no external invoke, provider call, runtime
binding change, live flag change, or model/scoring/fusion change.

CS1-C3X closes the macro L3 member-contract follow-up from C2X and records
source durability for prod-only wrapper work. Macro composite outputs now fail
closed unless members are unique formal macro L2 ids, and the production macro
wrapper projects exactly five formal macro slots without exposing local
stand-ins as public formal evidence. Owner handoff patches and durability
artifacts live under `/sdb/dlut/prod/backups/cs1c3x_20260622T103501Z` and
sanitized closeout artifacts live under
`/tmp/lma-cs1c3x-source-durability-20260622T103501Z`. This remains a controlled
compute-only/source-durability phase: no external invoke, provider call,
runtime binding change, live flag change, owner-dev repo write, or business
model/scoring/fusion change.

CS1-C3R follows up on C3X artifact and evidence-integrity gaps. It adds a
phase artifact checksum helper, fixes maintained trace L3 member summaries,
hardens real-contributor semantics across L3 adapters/report projection, and
patches the production `market_composite` wrapper so pending market slots keep
formal coverage but carry zero weight and no evidence contribution. Sanitized
artifacts live under
`/tmp/lma-cs1c3r-evidence-durability-20260622T121352Z`. `entity_relation_extractor`,
`sentiment_company_radar`, and `market_fund_manager_behavior` remain explicit
source/owner blockers.

BF-COMPLETE-X closes the two sandbox-to-prod backfill change-unit gaps for
`entity_relation_extractor` and `sentiment_company_radar`. The final ledger now
counts 31/31 current-relevant integration sandbox change units as present in
production by exact, equivalent, or stricter behavior. BF-CLOSE-R1 then
revalidated the transient `value_traditional_valuation` timeout without service
or runtime changes; the 21-agent trace mapped 21/21. Backfill scope is now
closed as `backfill_complete`. See
`docs/FULL_SANDBOX_PROD_BACKFILL_CLOSURE.md`.

POST-BF-B1X starts post-backfill production readiness foundation work. It keeps
the backfill ledger frozen at 31/31 and keeps the default product external
runtime limited to the two L4 compute-default services. The phase adds bounded
readiness metadata to entity/sentiment production wrappers, fixes the
`sentiment_company_radar` fixed-DAG `stock_sentiment` wrapper mapping to the
existing core `sentiments` subtask, adds private timing/caching stabilization
for `value_traditional_valuation`, records the three remaining formal L2
semantic blockers, and produces a non-L4 activation candidate set for a future
orchestration phase. See
`docs/POST_BF_B1X_PRODUCTION_READINESS_FOUNDATION.md`.

POST-BF-B2X adds the initial production non-L4 external compute orchestration
for the normal Web/API fixed-DAG path. It uses
`config/fixed_dag/non_l4_external_compute_policy.json` and
`src/react_agent/fixed_dag_production_external_compute.py`, not the demo bridge
and not L4 runtime bindings. The required 9 B1X agents plus the optional
degraded `macro_composite` now form the first production default non-L4 set;
L1 external defaults remain zero, and L4 still uses the existing two
`external_compute_default` bindings. See
`docs/POST_BF_B2X_NON_L4_RUNTIME_ACTIVATION_AND_RELEASE.md`.

P2S-BASELINE-X attempted to refresh the external-agent sandbox from current
production runtime source after the backfill/release cycle. It staged a new
26-agent source-bearing baseline under
`/sdb/dlut/sandbox/prod-baselines/20260623T050419Z/fixed-dag-services` and
archived the old sandbox under
`/sdb/dlut/sandbox/backups/p2s_pre_refresh_20260623T050419Z`. P2S-CLOSE-R1 then
resolved the sensitive-source blockers with sandbox-only sanitized derivatives,
omitted one unreachable legacy test file containing token-like material, and
switched `/sdb/dlut/sandbox/r8-13a/services/prod` to the refreshed 26-agent
baseline while preserving the old sandbox tree. Main-system sandbox refresh
remains dev-HEAD based, not production based. See
`docs/PROD_TO_SANDBOX_AGENT_BASELINE_REFRESH.md`.

SYNC-OPS-1 adds a read-only bidirectional external-agent sync planner MVP. It
source-controls `config/ops/agent_service_registry.json`,
`config/ops/agent_sync_policy.json`, Draft 2020-12 schemas, and a read-only
`agent-sync` CLI for inventory, baseline inspection, experiment validation,
B/S/P/D diffing, and immutable P2S/S2P/cycle plan generation. It does not
stage, apply, switch, lock, back up, restart, smoke, or write prod/sandbox/
owner-dev trees. See `docs/SYNC_OPS_1_READ_ONLY_PLANNER.md`.

SYNC-OPS-1R hardens the P2S plan model before write automation. P2S plans now
separate observed diff, future versioned-stage materialization, and activation
preconditions; backup/runtime-noise files are excluded, sanitized derivatives
are preserved by redacted structural fingerprint rather than raw replace
actions, and every Agent receives an explicit disposition. It is still
read-only and does not create stages, approvals, locks, backups, or sandbox
switches. See `docs/SYNC_OPS_1R_P2S_WRITE_SAFETY_REPAIR.md`.

SYNC-OPS-1R2 repairs recursive source coverage and baseline parity. P2S plans
now recurse through registered source/support subroots, explain every
historical baseline row and current production inventory row, and reconstruct
the expected safe tree under `/tmp` before any approval request is useful. See
`docs/SYNC_OPS_1R2_RECURSIVE_COVERAGE_REPAIR.md`.

SYNC-OPS-2A adds the P2S writer contract and temp-only transaction engine:
machine approval validation, environment snapshot binding, global plus
transaction locks, durable run artifacts, stage/verify/activate/rollback
primitives, and recovery journal tests. It only writes repo-external temporary
fixtures in this phase; real sandbox execution still requires a SYNC-OPS-2B
approval. See `docs/SYNC_OPS_2A_P2S_WRITER_DRY_RUN.md`.

SYNC-OPS-2A-R1 closes the source-selection gap before real P2S execution:
files are classified by role, hidden local/editor metadata, backups,
generated results, data/model assets, runtime noise, sensitive files, and
unknown files are excluded or blocked by policy, and `not_scanned` can no
longer become a copy action. The current real plan is rehearsed at full scale
under `/tmp` before a new awaiting-approval request is useful. See
`docs/SYNC_OPS_2A_R1_SOURCE_POLICY_AND_FULL_SCALE_REHEARSAL.md`.

Phase R3 upgrades the reset skeleton to plan-driven fixed-DAG execution. Phase
R4-A adds the fixed DAG catalog source and switches the backend public
`/api/agents` projection to the 27 `snake_case` reset agents. Phase R4-B adds
the fixed DAG runtime binding registry for deterministic, external-candidate,
and pending-placeholder runtime metadata. Phase R4-C isolates the legacy aNN
registry/bootstrap from the active fixed-DAG graph import path. Phase R5-B1
migrates the existing web frontend contract to `workflow_snapshot_v2`. Phase
R5-B2 rewrites the existing web workflow inspector around that fixed DAG
snapshot so stages, batches, dimensions, step result metadata, final source,
and provenance render as inspector data rather than public transcript content.
Phase R5-B2.6 localizes and polishes visible Chinese copy for the existing
fixed DAG inspector, Agents page, Settings page, public-safe skeleton answer,
and supporting frontend fixtures without changing the `workflow_snapshot_v2`
contract. Phase R5-C further simplifies the normal user-facing web surface:
engineering/backlog/readiness details move into workflow technical details,
Settings advanced diagnostics, docs, and tests instead of the default chat,
Agents, and Settings views.
Phase R5-C1 professionalizes the remaining business-facing Chinese copy so
dimension summaries, step descriptions, and answer-card evidence read as
product language rather than implementation notes.
Phase R6-B rebuilds the default reset quality mainline so it covers scoped
static checks, unit tests, public API tests, graph smoke tests, and frontend
typecheck/smoke/repo-external build validation without running archived
fusion-gate or live provider/external gates.
Phase R7-C upgrades the original repo-external scaffold source package at
`E:\muti-agent\external_agent_scaffold` into the fixed DAG handoff package and
syncs the tracked mirror under `examples/fixed_dag_external_agent_scaffold/`.
It remains sample-only contract material: it does not register the scaffold,
enable wrappers, modify runtime bindings, or live-verify external candidates.
Phase R7-D tightens external handoff documentation consistency around status
mapping, wrapper compatibility, package/mirror/zip distribution roles, and
developer handoff evidence without changing runtime behavior.
Phase R7-E expands the scaffold `AI_CODING_HANDOFF.md` into a developer-side
Codex / Claude Code operating manual for adapting an existing agent project
into a fixed DAG external service wrapper.
Phase R7-G upgrades that package to
`external-agent-scaffold-v2.3.1-fixed-dag`, patching risk-member L2 outputs,
manual-review risk gates, structured dimension members, normalized date
comparison, macro directional weights, L4 score tolerance, and distinct
reasoning stages while keeping fixed DAG ids, readiness boundaries, and
Non-Claims.
Phase R7-H repairs small consistency drift: frontend workflow fixtures now use
backend runtime binding `runtime_kind` literals, and the repo-external scaffold
working copy is restored from the tracked mirror when it is missing.
Phase R7-I adds a report-first web presentation mode for the existing assistant
answer card: the natural-language report remains the primary answer, while a
collapsed "研判思维链" disclosure summarizes the public-safe fixed DAG process
from `workflow_snapshot_v2`.
Phase R8-1 adds the selected routing contract foundation: `route_intent_v1`
and `selected_fixed_dag_plan_v1` validators are available for future controlled
dynamic routing, but the active graph still builds and validates the full
default fixed DAG.
Phase R8-2 adds the deterministic selected DAG compiler and selected executor
validation helpers. `route_intent_v1` can now be compiled into a dependency-
closed `selected_fixed_dag_plan_v1`, while the active graph default still uses
the full fixed DAG.
Phase R8-3 adds a provider-free route-intent planner seam: deterministic/mock
intent construction, a future LLM prompt contract, and JSON parser/normalizer
guards that target `route_intent_v1` only. It still does not enable selected
routing in the active graph by default.
Phase R8-4 adds a provider-free RouteEval baseline for `route_intent_v1`
selection quality. It evaluates task type, targets, selected dimensions,
selected agents, clarification, and fallback behavior against a small local
gold set, but it does not call an LLM/provider/external service and does not
enable selected routing.
Phase R8-5 wires selected routing into the graph behind
`Context.enable_selected_routing` / `ENABLE_SELECTED_ROUTING=1`. The default
active behavior remains full DAG; the selected path uses only the provider-free
route-intent seam and deterministic compiler, and compile/validation failure
falls back to the full DAG.
Phase R8-6B adds default-off internal LLM placeholders for L2 conclusions behind
`Context.enable_internal_llm_placeholders` /
`ENABLE_INTERNAL_LLM_PLACEHOLDERS=1`. When enabled, the executor may ask the
main-system model for bounded, public-safe placeholder observations for selected
or full L2 slots; provider failures, parse failures, or unsafe payloads fall
back to deterministic pending conclusions. L3/L4/report remain deterministic in
this first slice, and no external agent is invoked.
Phase R8-7B adds provider-free external payload adapter mapping in
`src/react_agent/fixed_dag_external_adapter.py`. The adapter is a pure function
layer for already-available payload dictionaries: first-slice support maps
`agent_conclusion_v1` into `conclusion_object_v1` and `data_bundle_v1` into the
current internal `data_bundle_v1`. It does not call HTTP, providers, `/health`,
`/v1/agent/invoke`, or any server-deployed agent; it does not change the active
graph, executor, runtime bindings, live flags, or fixed DAG roster.
Phase R8-8C extends that pure adapter seam to accept
`external_agent_compute_v0` as compute-envelope input for supported L2
`agent_conclusion_v1` tool results. This remains adapter-only compatibility:
it does not call endpoints, does not update runtime bindings, does not mark
services live verified, and does not make compute smoke evidence public
workflow truth. The R8-8B smoke result still leaves `financial_data_service`
blocked on structured JSON `/health`; `value_ml_valuation` requires an R8-8D
re-smoke before any readiness advancement wording.
Phase R8-8E records sanitized controlled readiness evidence after the
`value_ml_valuation` dev service identity remediation and R8-8D-ID re-smoke:
health passed, `/v1/agent/compute` passed, and the provider-free adapter mapped
the compute envelope into `conclusion_object_v1`. This is docs-only evidence. It
does not call `/v1/agent/invoke`, enable runtime bindings, set live flags,
update public transcript content, or prove production readiness.
Phase R8-8G accelerates controlled dev smoke for additional candidates:
`macro_analysis` and `value_traditional_valuation` now have sanitized
health+compute+adapter-mapping evidence. `value_traditional_valuation` required
a bounded dev service identity remediation; the main-system adapter gate,
runtime bindings, live flags, graph, executor, public API, frontend, and public
transcript boundary remain unchanged.
Phase R8-8H expands that docs-only controlled evidence batch to
`value_meta_valuation`, `value_research_synthesis`, and
`market_stock_technical` after bounded dev service protocol remediations. The
evidence is still health + compute + provider-free adapter mapping only; no
`/v1/agent/invoke`, runtime binding enablement, live flag, public transcript, or
L3/L4 active runtime change is implied.
Phase R8-8I broadens the same evidence boundary to
`sentiment_company_radar` as market-only L2 evidence after bounded dev service
protocol remediation. It still does not call `/v1/agent/invoke`, enable runtime
bindings, set live flags, update public transcript content, prove production
readiness, or create a sentiment-to-risk path.
Phase R8-8J expands the evidence boundary to L1 `financial_data_service` after
bounded dev service health and compute wrapper remediation. The provider-free
adapter can now map `external_agent_compute_v0.tool_result.data_bundle_v1` into
the internal `data_bundle_v1` contract, but this remains docs-only controlled
evidence with no `/v1/agent/invoke`, runtime binding enablement, live flag,
active graph L1 data integration, or production readiness claim.
Phase R8-8K expands the same evidence boundary to L1
`entity_relation_extractor` and risk L2 `risk_identification` /
`risk_compliance_review` after bounded dev service protocol remediations. The
provider-free adapter can now map
`external_agent_compute_v0.tool_result.entity_relation_bundle_v1` into the
internal `entity_relation_bundle_v1` contract; risk candidates map as
`agent_conclusion_v1 role=gate_member`. This remains docs-only controlled
evidence with no `/v1/agent/invoke`, runtime binding enablement, live flag,
active graph L1/L3/L4 integration, or production readiness claim.
Phase R8-8L records the remaining bounded risk L2 controlled evidence for
`risk_financial_fraud` and `risk_crash` after service-side wrapper
remediation. Both map as `agent_conclusion_v1 role=gate_member` into
`conclusion_object_v1`. Market and macro candidates that did not meet the
bounded L2 criteria remain deferred. This still does not call
`/v1/agent/invoke`, enable runtime bindings, set live flags, update public
transcript content, wire L3/L4 runtime paths, or prove production readiness.
Phase R8-8M records remaining bounded market L2 controlled evidence for
`market_capital_flow_chip` after service-side wrapper remediation and dev-only
service start. It maps as `agent_conclusion_v1 role=direction` into
`conclusion_object_v1`. Other remaining candidates stay deferred when their
payload is L3/regulator-shaped, their dev listener or compute endpoint is
missing, or their semantics are not clear enough for L2 evidence. This still
does not call `/v1/agent/invoke`, enable runtime bindings, set live flags,
update public transcript content, wire L3/L4 runtime paths, or prove production
readiness.
Phase R8-8N-DOCS persists the full R8-8N agent readiness audit into
`docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` and
`docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md`. These docs record the
27-agent matrix, controlled compute coverage, deferred/problem agents, service
patch backfill inventory, and developer prompt catalog. This is documentation
only: it does not call endpoints, enable runtime bindings, set live flags,
advance `/v1/agent/invoke`, change active graph runtime, or prove production
readiness.
Phase R8-8P rebaselines that readiness state against production endpoints.
Earlier R8-8G/H/I/J/K/L/M dev endpoint evidence is now historical only. The
production rebaseline found that only five external candidates currently have
production health, production compute, and adapter mapping pass evidence:
`risk_identification`, `risk_compliance_review`, `risk_financial_fraud`,
`risk_crash`, and `macro_analysis`. The production-first matrix and developer
prompt catalog have been rewritten around those results; no `/v1/agent/invoke`
was called, no runtime bindings were enabled, no live flags were set, and no
production default invocation is implied.
Phase R8-8P-DOCS-QA deepens those production-first docs into a developer
problem playbook: each failed/deferred agent now has a specific issue,
probable cause, owner action, maintainer action, resmoke boundary, and
copy-ready Chinese Codex / Claude Code prompt. This is documentation only; it
does not call endpoints, edit production services, change adapter logic, enable
runtime bindings, set live flags, or advance `/v1/agent/invoke`.
Phase R8-10B adds provider-free pure adapter mappings for L3 composite payloads:
`dimension_conclusion_v1` for value/market composites,
`risk_conclusion_v1` for the risk gate, and `macro_conclusion_v1` for the macro
regulator. All three map into the existing `dimension_composite_result_v1`
internal contract, including compute/response envelope tool results. This does
not call endpoints, enable runtime bindings, set live flags, wire active L3
runtime execution, or treat adapter tests as live readiness.
Phase R8-10C audits the four L3 services for protocol backfill readiness and
turns the findings into service-owner prompts. It observes process/source
metadata only: no `/health`, `/v1/agent/compute`, `/v1/agent/invoke`, prod or
dev endpoint call is made. The result is that `value_composite`,
`market_composite`, `risk_composite`, and `macro_composite` need service-side
wrapper or identity/runbook backfill before any controlled L3 smoke.
Phase R8-10D performs that bounded service-side wrapper backfill in the four
L3 service directories: value/market composites now expose fixed DAG
`dimension_conclusion_v1` wrappers, risk exposes a fixed DAG
`risk_conclusion_v1` gate wrapper, and macro exposes a fixed DAG
`macro_conclusion_v1` compute-envelope wrapper. The phase did not call
endpoints, did not restart services, did not enable runtime bindings or live
flags, and does not create L3 readiness evidence; controlled L3 smoke remains
R8-10E.
Phase R8-10D-SNAPSHOT adds a local handoff repository for those four L3 service
patches because the formal service source repositories are not available in
this environment. The snapshot at
`/sdb/dlut/service-shadow-repos/l3-composite-services` stores service notes,
the R8-10D manifest, and zero-context patch files only; it is not production
readiness evidence and is not the long-term service source of truth.
Phase R8-10E performs an authorized controlled production restart and
production `/health` + `/v1/agent/compute` smoke for the four L3 services.
`market_composite`, `risk_composite`, and `macro_composite` reached production
health + compute + adapter mapping evidence. `value_composite` remains blocked
on production health identity mismatch. This is still compute evidence only:
no `/v1/agent/invoke`, runtime binding enablement, live flags, public transcript
update, or default production invocation was performed.
Phase R8-10F remediates `value_composite` production health identity on port
`10015`, preserves the existing L3 `dimension_conclusion_v1` compute wrapper,
restarts only that service, and records production health + compute + adapter
mapping evidence for `value_composite`. This closes the R8-10E L3 compute
coverage gap while still avoiding `/v1/agent/invoke`, runtime binding
enablement, live flags, public transcript updates, and default production
invocation.
Phase R8-8Q remediates selected production L1/L2 protocol wrapper issues and
re-smokes only production `/health` plus `/v1/agent/compute` endpoints. The
phase adds production compute evidence for `value_traditional_valuation`,
`value_ml_valuation`, `value_meta_valuation`, `value_research_synthesis`,
`market_stock_technical`, `market_capital_flow_chip`,
`sentiment_company_radar` as market-only, and
`market_ipo_investor_behavior`. `financial_data_service` and
`macro_commodity_pricing` remain remediation items. No `/v1/agent/invoke`,
runtime binding enablement, live flag, public transcript update, or default
production invocation was performed.
Phase R8-11B runs the first tiny allowlist controlled production
`/v1/agent/invoke` smoke for `risk_identification`,
`risk_compliance_review`, `risk_crash`, `risk_financial_fraud`, and
`value_research_synthesis`. Each response mapped through the existing
provider-free adapter into `conclusion_object_v1` with `allow_llm=false` style
options. This is controlled invoke evidence only: runtime bindings remain
unchanged, no live flags are set, no public transcript content is updated, and
the fixed DAG graph still does not invoke production external services by
default.
Phase R8-12 adds a default-off external compute demo bridge. When
`ENABLE_EXTERNAL_COMPUTE_DEMO=1` and `EXTERNAL_COMPUTE_DEMO_ALLOWLIST` are both
set, the executor may call only allowlisted loopback production
`/v1/agent/compute` endpoints, map the results through the provider-free
adapter, and surface a Chinese demo report/workflow summary. With flags off, or
with an empty allowlist, the active graph remains the deterministic fixed DAG
skeleton. R8-12 does not call `/v1/agent/invoke`, does not change
`runtime_bindings.json`, does not set live flags, and does not make external
invocation the default runtime.
The runtime validates
`dag_steps[].depends_on`, computes deterministic `execution_batches`, emits
per-step `step_results`, and keeps the default path as a provider-free
placeholder skeleton. It is not a completed business analysis engine.

Phase R8-12B adds local remote-agent demo tunnel tooling for developers who
clone the repo to their own computer while the 16 demo agents continue running
on the server. Use `scripts/dev/start_agent_tunnels.sh` or
`scripts/dev/start_agent_tunnels.ps1` to create same-port SSH forwards bound to
`127.0.0.1`, then run the local API/Web with the R8-12 demo flags. See
`docs/LOCAL_REMOTE_AGENT_DEMO_RUNBOOK.md`. This is demo/dev only: no `.env`
secret is written, no `/invoke` call is made, production `100xx` ports are not
publicly exposed, and `runtime_bindings.json` remains unchanged.

Phase R8-12C wires report generation to a public-safe
`report_input_bundle_v1`. The bundle summarizes the L2 agent signals and L3
composite inputs that the report generator receives, then projects those
summaries into `workflow_snapshot_v2.stepResults` for the Web workflow detail
view. It does not store raw external responses, endpoints, secrets, error
stacks, or internal reasoning drafts, and it does not change runtime bindings,
live flags, or `/invoke` behavior. Production deployment requires syncing the
validated main-system code to `/sdb/dlut/prod/langgraph-my-agent` and restarting
the main-system service in a separate deployment step.

Phase R8-12D adds a default-off LLM report synthesizer. When
`ENABLE_LLM_REPORT_SYNTHESIS=1` is set, the main system can load the configured
chat model, pass only `report_input_bundle_v1` to the report synthesizer, and
replace the template report with a natural Chinese report that understands the
single-agent and composite-agent inputs. Invalid, unsafe, or unavailable model
output fails closed back to the R8-12C template report. This does not call
external `/v1/agent/invoke`, does not change runtime bindings, does not set
live flags, and does not expose raw external responses.

Version anchor: local tag `r8-12d-llm-report-synthesizer-fallback` marks this
fallback/demo state. It is not the final external `report_generator` agent
handoff; the formal multi-agent path should later make `report_generator`
consume `report_input_bundle_v1` and return `report_result_v1` through the
external-agent contract while this main-system synthesizer remains fallback.

Phase R8-13D packages the sandbox L3 demo and backfill plan without touching
production services. The package lives at
`/tmp/lma-r8-13d-handoff-package/20260612T023822Z` and contains the sandbox
main-system patch, four L3 service candidate patches, sanitized R8-13C trace
artifacts, and a manifest. See
`docs/R8_13D_SANDBOX_L3_BACKFILL_HANDOFF.md` for the exact service-by-service
changes, safe apply order, validation, rollback, and non-claims. This package
does not call endpoints, does not modify `/sdb/dlut/prod`, does not change
runtime bindings, and does not enable default external invocation.

Phase R8-13E applies those reviewed L3 wrapper patches to the four production
L3 service directories and records controlled production `/health` +
`/v1/agent/compute` smoke evidence. The changed service layer now accepts
bounded `context.upstream_outputs` for L3 composite requests. All four L3
services passed compute and adapter mapping after backfill. See
`docs/R8_13E_PRODUCTION_L3_BACKFILL_SMOKE.md`. This still does not call
`/v1/agent/invoke`, change runtime bindings, set live flags, or enable default
graph calls to production services.

Phase R8-13F restores the sandbox-proven main-system trace path in this branch:
`agent_task_v1`, `agent_evidence_bundle_v1`, and bounded L2
`context.upstream_outputs` propagation to allowlisted L3 production compute
calls. The reference E2E QA artifact
`/tmp/lma-r8-13f-prod-e2e-llm-report/20260612T030735Z` mapped 17 production
compute agents, used 5 explicit placeholder L2 slots, and generated a natural
Chinese report from the configured report model. See
`docs/R8_13F_END_TO_END_PRODUCTION_TRACE_QA.md`. This remains default-off demo
QA: no `/v1/agent/invoke`, runtime binding change, live flag, or default
production graph invocation is introduced.

Phase R8-13G remediates the three value L2 valuation services exposed by
R8-13F: `value_traditional_valuation`, `value_ml_valuation`, and
`value_meta_valuation` already computed `normalized.stance`, but omitted the
top-level `agent_conclusion_v1.stance` consumed by the fixed DAG adapter. The
production service wrappers now project the existing direction and confidence
to top-level fields, all three services pass production `/health` +
`/v1/agent/compute` + adapter mapping, and the configured-report E2E trace
`/tmp/lma-r8-13g-prod-e2e-llm-report/20260612T033912Z` includes them as usable
value evidence. See `docs/R8_13G_VALUE_L2_STANCE_REMEDIATION.md`. This is still
default-off demo/readiness work: no `/v1/agent/invoke`, runtime binding change,
live flag, valuation model change, or default production graph invocation is
introduced.

## Current Branch Scope

- Branch: `reset/fixed-dag-v1`.
- Reset base: `pre-fixed-dag-reset-20260604-1457`.
- Current phase: R8-13J documentation roadmap over the existing
  full/selected fixed DAG backend skeleton, R8-12 default-off external compute
  demo bridge, R8-12C/R8-12D evidence-bundle report synthesis, R8-13F
  end-to-end trace restoration, and R8-13G value L2 stance remediation.
- Current runtime milestone: R3 plan-driven fixed DAG execution orchestration.
- Runtime entry: `langgraph.json -> src/react_agent/graph.py:graph`.
- Public Python workflow contract: `workflow_snapshot_v2`.
- Public agent catalog: fixed DAG 27-agent `snake_case` projection from
  `config/fixed_dag/agent_catalog.json`.
- Production readiness problem playbook docs:
  `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` and
  `docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md`.
- Temporary L3 service handoff repository:
  `/sdb/dlut/service-shadow-repos/l3-composite-services`.
- Public web shell: migrated in place to consume the fixed DAG public contract;
  the current WorkflowPanel renders the R5-B2 fixed DAG inspector from
  `workflow_snapshot_v2`, with R5-B2.6 Chinese localization, R5-C
  user-facing simplification, and R5-C1 business-copy professionalization on
  the same payload. R7-I adds a collapsed report-first "研判思维链" disclosure
  above that technical inspector without changing the public contract.
- Selected routing contracts: R8-1 adds `route_intent_v1` and
  `selected_fixed_dag_plan_v1` in `fixed_dag_contracts.py`. They are additive
  planner/compiler targets for later R8 work and are not active runtime
  defaults. R8-2 adds `compile_selected_fixed_dag_plan`,
  `validate_selected_dag_steps`, and `topological_batches_for_selected_plan` as
  deterministic selected-routing compiler/validator seams, still without
  changing the active graph default. R8-3 adds
  `build_default_route_intent`, `FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT`,
  `build_route_intent_prompt`, `parse_route_intent_json`, and
  `normalize_route_intent` as provider-free planner seam pieces. R8-4 adds
  `src/react_agent/route_eval.py` and `tests/fixtures/route_eval_gold.jsonl`
  as a small deterministic RouteEval baseline for route intent selections.
  R8-5 adds `Context.enable_selected_routing` / `ENABLE_SELECTED_ROUTING=1`
  as a default-off graph boundary. Without that flag, the active
  `route_planner` node still builds the full default fixed DAG.
- Internal LLM placeholders: R8-6B adds
  `Context.enable_internal_llm_placeholders` /
  `ENABLE_INTERNAL_LLM_PLACEHOLDERS=1` as an independent default-off graph
  boundary for L2 conclusion slots only. This is not external adapter
  readiness, live integration, provider readiness, or a real business-agent
  output claim. Runtime bindings remain unchanged.
- External adapter mapping: R8-7B adds
  `src/react_agent/fixed_dag_external_adapter.py` as a provider-free pure mapping
  module. It accepts external scaffold payload dictionaries and returns
  validator-legal internal objects or controlled adapter failure records for the
  first supported families: `agent_conclusion_v1 -> conclusion_object_v1` and
  `data_bundle_v1 -> data_bundle_v1`. It is not an HTTP wrapper, does not load a
  provider, does not call deployed services, and is not wired into active graph
  execution. R8-8C additionally accepts `external_agent_compute_v0` as adapter
  input only when it contains a supported L2 `agent_conclusion_v1` tool result;
  the compute envelope is not graph state, readiness evidence, or runtime
  binding authority. R8-8E records one sanitized controlled dev smoke evidence
  item for `value_ml_valuation` after service-side identity remediation. The
  evidence remains docs-only and does not change runtime bindings, live flags,
  or active graph behavior. R8-8G adds the same docs-only evidence boundary for
  `macro_analysis` and `value_traditional_valuation`. R8-8H adds docs-only
  controlled evidence for `value_meta_valuation`, `value_research_synthesis`,
  and `market_stock_technical` after bounded dev service protocol remediation.
  R8-8I adds docs-only controlled evidence for `sentiment_company_radar` as
  market-only L2 evidence and preserves the no-risk-routing boundary. R8-8J
  adds docs-only controlled L1 evidence for `financial_data_service` and extends
  compute-envelope mapping to `data_bundle_v1` without wiring it into graph
  execution. R8-8K adds docs-only controlled L1 evidence for
  `entity_relation_extractor`, extends compute-envelope mapping to
  `entity_relation_bundle_v1`, and records risk L2 gate-member evidence for
  `risk_identification` and `risk_compliance_review` without wiring any L3/L4
  runtime path. R8-8L adds the same docs-only controlled evidence boundary for
  `risk_financial_fraud` and `risk_crash`; no new main-system adapter branch is
  needed, and L3 `risk_composite` / L4 decision runtime integration remains
  deferred. R8-8M adds docs-only controlled market L2 evidence for
  `market_capital_flow_chip`; remaining macro/market candidates that require
  L3 adapter design, owner semantic confirmation, or non-stub service metadata
  remain deferred.
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
  -> execute_fixed_dag
  -> final_emit
  -> memory_update
```

`execute_fixed_dag` walks the 27-agent `fixed_dag_plan_v1` by validated
dependencies, produces topological batches, records per-step execution results,
and fills the L2/L3/L4 placeholder result contracts.

R8-1 keeps this full DAG path as the regression baseline and fallback. It adds
`route_intent_v1` as a planner-output contract and
`selected_fixed_dag_plan_v1` as the future deterministic compiler/validator
target. `route_intent_v1` is not executable; the selected plan contract allows
omitted dimensions and agents only when they are explicitly recorded, keeps
`report_generator` always on for selected plans, requires risk and
`decision_synthesizer` for investment-judgment task types, and rejects legacy
route-mode fields, runtime binding fields, provider/external invocation claims,
and unsafe fallback text. R8-1 does not connect an LLM planner, does not change
`graph.py`, and does not enable selected execution.

R8-2 implements the deterministic compiler for that seam:
`compile_selected_fixed_dag_plan(route_intent, user_text, as_of)` validates the
intent, adds required L1/evidence seams, adds selected L2 steps, adds selected
dimension composites, includes `decision_synthesizer` for investment-judgment
task types, keeps `report_generator` always present, and emits a
dependency-closed `selected_fixed_dag_plan_v1`. Executor-side selected
validation is available through `validate_selected_dag_steps` and
`topological_batches_for_selected_plan`. The active `route_planner` node and
`execute_fixed_dag` path still use the full `fixed_dag_plan_v1` unless a later
phase explicitly changes the runtime.

R8-3 adds the planner seam that can produce `route_intent_v1` before compiler
handoff. `build_default_route_intent(question)` is deterministic and
provider-free; `FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT` and
`build_route_intent_prompt(question)` define the future LLM/semantic planner
protocol; `parse_route_intent_json` and `normalize_route_intent` parse or
fail-soft raw planner JSON into public-safe route intent. The planner seam never
outputs executable `dag_steps` or dependencies. The selected compiler remains
the only path from intent to selected DAG, and it is not wired into the active
graph default in R8-3.

R8-4 adds RouteEval for the route-intent seam:
`load_route_eval_cases(path)` reads a small JSONL gold set,
`evaluate_route_intents(cases, planner_fn)` evaluates deterministic/mock
planner output, and `route_eval_report_to_dict(report)` emits stable metrics.
The metrics cover task type accuracy, target exact-or-partial match, dimension
precision/recall/F1, agent precision/recall/F1, over-selection,
under-selection, clarification accuracy, and fallback rate. RouteEval does not
evaluate Star/Chain/Debate/Tree modes and does not call providers, search, or
external `/v1/agent/invoke`. The first 12-case fixture is a baseline only; the
future formal Route F1 gate should use a larger gold set.
R8-4 does not modify `src/react_agent/graph.py`, public workflow mapping,
frontend rendering, runtime bindings, provider/search readiness, or external
adapter readiness.

R8-5 wires the selected route intent and compiler pipeline into
`route_planner_node` behind an explicit default-off flag. With
`Context(enable_selected_routing=True)` or `ENABLE_SELECTED_ROUTING=1`, the
graph builds `route_intent_v1` through `build_default_route_intent`, compiles
it into `selected_fixed_dag_plan_v1`, and executes selected DAG steps through
the selected executor validation path. Compile or selected validation failure
falls back to the full `fixed_dag_plan_v1` with public-safe provenance
(`selected_routing_requested`, `selected_routing_fallback`, and a safe fallback
reason). R8-5 still does not call an LLM/provider, search backend, external
`/v1/agent/invoke`, or runtime binding adapter.

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

## Active Agent Catalog

R4-A makes the fixed DAG catalog the active backend catalog source:

- `config/fixed_dag/agent_catalog.json`
- `src/react_agent/fixed_dag_catalog.py`

The catalog is aligned to the v4 feedback workbook:

- `新架构_固定DAG_最终分层级智能体表_v4_反馈修正版.xlsx`

The public `/api/agents` endpoint now projects 27 enabled `snake_case` reset
agents with layer counts L1=3, L2=18, L3=4, L4=2. Its public shape remains
compatible with the existing `AgentCatalogResponse`, but in R4-A
`configCount`, `runtimeCount`, and `disabledIds` describe the fixed DAG reset
catalog, not the old aNN config catalog.

## Active Runtime Bindings

R4-B adds a backend-only runtime binding source:

- `config/fixed_dag/runtime_bindings.json`
- `src/react_agent/fixed_dag_runtime_registry.py`

The binding registry covers the same 27 fixed DAG ids as the active catalog and
records how each id currently maps to one of these runtime categories:

- deterministic skeleton seams
- external HTTP candidates
- pending placeholders

External HTTP candidates are disabled by default and are not live verified.
Legacy aNN ids may appear only as `legacy_agent_id` migration notes, never as
primary reset ids. Endpoint URLs and env var names are registry metadata for
later adapter work; R4-B does not call them.

The executor annotates `fixed_dag_step_result_v1` records with binding metadata
such as `runtime_kind`, `implementation_status`, `binding_source`,
`legacy_agent_id`, `external_agent_id`, `invoke_enabled`, and `live_verified`.
It does not include endpoint URLs or env var values in step results.

## Current Runtime Boundary

R3/R4-C keeps the graph deterministic and routes graph/public fallback
construction through contract, executor, and public mapping seams:

- `src/react_agent/fixed_dag_contracts.py`
- `src/react_agent/fixed_dag_executor.py`
- `src/react_agent/fixed_dag_runtime_registry.py`
- `src/react_agent/graph.py`
- `src/react_agent/prompts.py`
- `src/react_agent/router_parse.py`
- `src/react_agent/state.py`
- `src/react_agent/agent_types.py`
- `src/react_agent/public_contracts.py`
- `src/react_agent/public_mapping.py`
- `src/react_agent/public_runtime.py`
- `src/react_agent/public_api.py`

The graph state now carries `dag_execution`, `dag_step_results`, and
`execution_batches` in addition to the reset result contracts. R4-B step
results include runtime binding metadata for workflow inspection, but this does
not mean any external service was invoked.

R4-C adds an explicit legacy boundary:

- `src/react_agent/legacy_agent_registry.py` owns historical `AGENT_METADATA`
  and `AGENT_TOOLS`.
- `src/react_agent/graph_bootstrap.py` is legacy-only compatibility bootstrap.
- `src/react_agent/agents.py` keeps shared typing and lazy compatibility
  exports, but active fixed-DAG state imports types from `agent_types.py`.
- `config/agents/*.json` remains as migration/readiness input only.
- `src/react_agent/external_http_config.py` keeps offline external candidate
  metadata; `src/react_agent/external_http_agents.py` remains retained wrapper
  infrastructure, not live-verified runtime.

Importing `react_agent.graph` must not import or execute legacy bootstrap,
`AGENT_TOOLS`, default LLM/search placeholder registration, generic agent
registration, or HTTP wrapper implementation modules. `config/agents/*.json` is
still retained, but it is no longer the active reset public catalog or runtime
registration truth.

## Previous R3.6 Cleanup Boundary

R3.6 removed high-confidence dead local artifacts and legacy test fixtures that
were not active entry points, and added the v4 feedback workbook to the repo:

- `新架构_固定DAG_最终分层级智能体表_v4_反馈修正版.xlsx`

That workbook is the R4 baseline input for the `snake_case` catalog/runtime
registry. R4-A adds the backend catalog source and public projection. R3.6 did
not delete the old aNN catalog/config files, the existing web workflow
implementation, external wrapper production code, baseline/fusion regression
inputs, or tracked historical benchmark/trace artifacts that still need an
archive policy.

## Public Transcript Boundary

The product keeps a single assistant transcript. Internal graph steps, raw graph
messages, manager assignments, agent JSON, and provider raw responses must not
be treated as public transcript content.

The workflow inspector is a diagnostic panel. The Python public adapter projects
DAG stages, steps, dimensions, provenance, and final source as
`workflow_snapshot_v2` through reset contract seams. R3 also exposes
`executionBatches` and `stepResults` for the inspector. R4-B adds binding
metadata to `stepResults`. R5-B1 updates the frontend workflow/chat types,
streaming placeholder, mocks, and smoke fixtures to consume this public shape.
R5-B2 renders stage timeline, execution batches, dimension groups, selected
step result metadata, final source, and provenance in the inspector while
preserving the single user/assistant transcript boundary.
R5-B2.6 keeps that boundary and localizes the visible web copy, inspector
labels, status labels, mock/screenshot fixture copy, and deterministic
public-safe reset skeleton answer. It keeps technical ids, schema names, and
runtime enum values available where needed for debugging.
R5-C keeps the same public contracts but reduces engineering/status noise in
normal UI. Chat empty state, answer cards, workflow collapsed summaries, Agents
overview, and Settings default view are product-facing. Provider/search/live
readiness, raw runtime enums, and execution provenance remain available in
technical details, advanced diagnostics, docs, and tests.
R5-C1 keeps the same public contracts and further professionalizes business
copy in the default user surface: dimension summaries avoid route-wiring
explanations, step summaries avoid fixture/roster/transcript language, and
answer cards use "研判依据", "分析框架", "用户问题", and "流程记录" labels.
R7-I keeps the single user/assistant transcript and adds a public-safe
"研判思维链" disclosure below the assistant report. It is a structured process
summary derived from `workflow_snapshot_v2`, not hidden chain-of-thought or raw
runtime/provider/external output.

## Documentation Index

- `docs/INDEX.md` - reset documentation map.
- `docs/SYSTEM_MAP.md` - active runtime topology and phase map.
- `docs/ARCHITECTURE_FIXED_DAG.md` - fixed DAG skeleton and target ids.
- `docs/CONTRACTS.md` - runtime/public contract payload boundaries.
- `docs/FRONTEND_V2.md` - frontend/public transcript boundary.
- `docs/QUALITY.md` - safe quality commands for the reset branch.
- `docs/DECISIONS.md` - reset architecture decisions.
- `docs/CHANGELOG.md` - reset branch changelog.
- `docs/EXTERNAL_AGENT_HANDOFF_FIXED_DAG.md` - fixed DAG external developer
  handoff entry point.
- `docs/EXTERNAL_AGENT_PAYLOAD_MAPPING_FIXED_DAG.md` - mapping from external
  payload envelopes to fixed DAG contracts.
- `docs/EXTERNAL_AGENT_READINESS_LADDER_FIXED_DAG.md` - readiness ladder from
  docs-only review to explicit live invocation approval.
- `docs/CONTROLLED_READINESS_SMOKE_LOG.md` - sanitized internal log for
  controlled health/compute smoke evidence and non-claims.
- `docs/DEMO_EXTERNAL_COMPUTE_DAG_RUNBOOK.md` - default-off external compute
  demo setup, allowlist, and non-claims.
- `docs/LOCAL_REMOTE_AGENT_DEMO_RUNBOOK.md` - local remote-agent demo over SSH
  tunnel setup, troubleshooting, shutdown, and security boundaries.
- `docs/EXTERNAL_AGENT_SAMPLE_PAYLOADS_FIXED_DAG.md` - documentation-only
  endpoint and v2.3.1 domain payload samples.
- `examples/fixed_dag_external_agent_scaffold/` - tracked repo mirror of the
  upgraded v2.3.1 fixed DAG external scaffold package and its local tests.

## Safe Local Validation

Use the project conda environment when available. R6-B makes `mainline` the
default reset quality gate:

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode unit
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode public-api
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode graph-smoke
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode frontend
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
```

`frontend` uses TypeScript no-emit, the frontend smoke test, and a temporary
repo-external Vite build `--outDir`; it must not write `apps/web/dist`.

Do not use successful tests as production readiness evidence.

For R8-2 selected compiler changes, use the narrow additive gate:

```powershell
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent/fixed_dag_contracts.py src/react_agent/fixed_dag_executor.py tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_fixed_dag_contracts.py tests/unit_tests/test_fixed_dag_executor.py -q
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
git diff --check
```

These commands do not run provider live smoke, external live invoke, demo
stack, fusion-gate, frontend build, active graph selected execution, or live
selected routing.

R7-H restores `E:\muti-agent\external_agent_scaffold` from the tracked repo
mirror when that local distribution working copy is missing. Scaffold
validation can then run the restored repo-external package tests and ruff for
`E:\muti-agent\external_agent_scaffold`, the tracked repo mirror tests and ruff
for `examples/fixed_dag_external_agent_scaffold/`, then use the same
non-provider static and mainline commands. These checks do not call providers,
do not call external `/v1/agent/invoke`, and do not prove live external
readiness.

## Explicit Non-Claims

- No provider or live external service was verified by
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1/R6-B/R7-B/R7-C/R7-D/R7-E/R7-F/R7-G/R7-H/R7-I.
- No `external /v1/agent/invoke` call is part of
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1/R6-B/R7-B/R7-C/R7-D/R7-E/R7-F/R7-G/R7-H/R7-I validation.
- No demo stack startup is part of
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1/R6-B/R7-B/R7-C/R7-D/R7-E/R7-F/R7-G/R7-H/R7-I validation.
- No real business algorithms for individual agents are implemented in
  R3/R4-A/R4-B/R4-C/R5-B1/R5-B2/R5-B2.6/R5-C/R5-C1.
- R5-B2 completes the frontend inspector UI rewrite only; it does not change
  backend executor semantics, provider readiness, external readiness, or
  business-agent correctness.
- R5-B2.6 completes Chinese visible-copy localization and visual copy polish
  only; it does not add a runtime locale switch, change public schemas, or
  change fixed DAG topology, roster, provider readiness, external readiness, or
  business-agent correctness.
- R5-C completes user-facing simplification and diagnostic disclosure cleanup
  only; it does not change public schemas, fixed DAG topology, roster, provider
  readiness, external readiness, or business-agent correctness.
- R5-C1 completes user-facing business copy professionalization only; it does
  not change public schemas, fixed DAG topology, roster, provider readiness,
  external readiness, or business-agent correctness.
- R6-B rebuilds the default reset mainline quality gate only. It does not
  restore fusion acceptance, and `fusion-gate` remains archived/manual.
- R7-B adds external developer handoff docs, payload mapping docs, readiness
  ladder docs, sample payload docs, and a sample-only local scaffold. It does
  not register the scaffold into the graph, modify runtime bindings, enable
  external candidates, live-verify services, or force one internal
  implementation mode for external agents.
- R7-C upgrades the original repo-external scaffold source package and syncs a
  tracked repo mirror. It does not turn the scaffold into active runtime code,
  enable `runtime_bindings`, register wrappers, or prove live service
  readiness.
- R7-D only tightens external handoff wording and consistency. It does not
  change active runtime behavior, enable bindings, bridge legacy wrappers, or
  prove live readiness.
- R7-E only expands developer-side AI coding instructions for adapting
  external agent projects. It does not change service runtime behavior,
  schemas, samples, active runtime, runtime bindings, or live readiness.
- R7-G patches the scaffold v2.3.1 contract semantics and validators. It does
  not change active runtime behavior, enable bindings, bridge legacy wrappers,
  call providers, call external live invoke, or prove live readiness.
- R7-H only repairs frontend fixture metadata, documentation wording, and the
  local scaffold distribution working copy. It does not change active runtime
  behavior, runtime bindings, fixed DAG topology, provider readiness, or
  external live readiness.
- R7-I only adds a frontend report-first "研判思维链" presentation disclosure.
  It does not change public schemas, backend runtime behavior, runtime
  bindings, fixed DAG topology, provider/search readiness, external invocation,
  demo stack acceptance, or business-agent correctness.
- R8-1 only adds selected routing contracts and validators. It does not change
  active graph behavior, default full DAG fallback, runtime bindings, fixed DAG
  roster, provider/search readiness, external invocation, LLM planning,
  deterministic selected compilation, RouteEval, or external adapter readiness.
- R8-2 only adds deterministic selected DAG compilation and selected plan
  validation helpers. It does not change active graph behavior, default full DAG
  fallback, runtime bindings, fixed DAG roster, public workflow fields,
  frontend behavior, provider/search readiness, external invocation, LLM
  planning, RouteEval, or external adapter readiness.
- R8-3 only adds provider-free route-intent planner/prompt/parser seams. It
  does not change active graph behavior, enable selected routing, call
  providers/search, invoke external services, or add RouteEval/external adapter
  readiness.
- R8-4 only adds provider-free RouteEval helpers, a small local gold fixture,
  and unit coverage. It does not change active graph behavior, enable selected
  routing, add a provider-backed LLM planner, call external services, or create
  a formal >=80% Route F1 acceptance gate.
- R8-5 only adds default-off selected routing graph integration. It does not
  change the default full DAG behavior, call LLMs/providers/search, invoke
  external services, modify runtime bindings, change frontend behavior, or
  implement real business agents/external adapter readiness.
- Provider live smoke, external invoke checks, Router-SFT, RARP/route-prior,
  demo stack acceptance, and browser screenshot visual capture remain outside
  the default reset mainline.
- R4-C isolates legacy registry/bootstrap but does not delete
  `config/agents/*.json` or live-verify external candidates.
- No production auth, rate limit, HTTPS, deployment, or observability claim is made here.
- SYNC-OPS-1R2 repairs the read-only P2S planner's recursive source coverage.
  It adds full source/support-root inventory, historical baseline parity,
  current production coverage ledgers, stage projection digests, and `/tmp`
  reconstruction checks. It still does not write prod, sandbox, owner-dev,
  approval, lock, backup, stage, activate, endpoint, process, or artifact-store
  state.
- SYNC-OPS-2A-R1 closes P2S source selection and full-scale temp rehearsal
  before real execution approval. It still does not write prod, sandbox,
  owner-dev, real artifact-store, approval, lock, backup, stage, activate,
  endpoint, process, or environment-value state.
