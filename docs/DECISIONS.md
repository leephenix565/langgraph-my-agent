# Decisions

This document records reset branch decisions. It is intentionally short; deeper
historical context is preserved by the pre-reset tag.

## ADR-114: P2S Closeout Preserves Stage And Old Active Archive

Status: accepted for SYNC-OPS-2B2X.

Decision: successful P2S closeout preserves the immutable versioned stage and
the previous active baseline archive.

Reason: the stage is the activation authority and the archive is the rollback
source of record for the old active baseline.

Consequence: final closeout keeps the stage, archive, failed-new rollback proof,
durable run artifacts, and sha manifests.

Non-consequence: closeout does not delete historical baselines or rollback
evidence.

## ADR-113: Initial Activation And Post-Rollback Reactivation Use Separate Approvals

Status: accepted for SYNC-OPS-2B2X.

Decision: the first activation/rollback and the post-rollback final
reactivation use separate machine approval records bound to the same plan,
stage run, stage digest, artifact index, stage validation, and frozen pointer
candidate.

Reason: rollback validation intentionally returns the sandbox to the old active
state, so the final reactivation is a distinct state transition that needs its
own approval boundary.

Consequence: the second approval is created only after old active and old
pointer restoration proofs pass and no plan, stage, prod freshness, process, or
lock-scope drift is observed.

Non-consequence: the second approval cannot expand action scope, create a new
stage, or approve publish-and-rebase.

## ADR-112: P2S Release Closure Requires Activation, Rollback, And Reactivation

Status: accepted for SYNC-OPS-2B2X.

Decision: a production-to-sandbox release is not closed until activation,
rollback restoration, and final reactivation have all been proven against the
same immutable stage.

Reason: activation alone does not prove that the rollback contract can restore
the prior active baseline and pointer bytes if activation later needs to be
reversed.

Consequence: closeout artifacts record first activation, controlled rollback,
old active/pointer restoration, second approval, final reactivation, old archive
proof, immutable stage proof, and topic closure.

Non-consequence: this does not approve S2P, endpoint smoke, process action,
delete operations, or production-source mutation.

## ADR-111: P2S Stage/Verify Does Not Activate

Status: accepted for SYNC-OPS-2B1.

Decision: the first real P2S write after durable artifact-store bootstrap is
limited to versioned baseline stage and verify. It may write the approved
stage root and durable run artifacts, but it must not archive the active
sandbox, build an active candidate, update the baseline pointer, activate, or
roll back active state.

Reason: stage/verify produces the real stage digest and validation evidence
needed for a separate activation approval. Binding activation to the completed
stage run keeps the sandbox switch decision separate from source
materialization.

## ADR-110: Durable Artifact Store Is Bootstrapped Before P2S Stage

Status: accepted for SYNC-OPS-2B0-R1.

Decision: `/sdb/dlut/ops-artifacts/agent-sync` is initialized by a separate
stable-binding machine-approved bootstrap before any real P2S stage. The
bootstrap writes only the approved directory layout and `STORE_METADATA.json`.

Reason: P2S stage needs durable plans, approvals, runs, locks, validation, and
closeout evidence before it can safely write a versioned sandbox stage.
Separating store bootstrap from stage keeps infrastructure creation out of the
P2S transaction and makes the next approval scope stage/verify only.

## ADR-109: Environment Drift, Constraint Failure, And Diagnostics Are Distinct

Status: accepted for SYNC-OPS-2A-R5.

Decision: bootstrap execution reports stable authorization drift, execution
constraint failure, and diagnostic observation changes as separate outcomes.

Reason: exact identity, permission, and path-state drift must invalidate an
approval. Free-space shortages should block execution without pretending that
the approval hash changed, while diagnostic-only changes should remain
reviewable without forcing reapproval.

## ADR-108: Supplementary Groups Bind Only When Access Depends On Them

Status: accepted for SYNC-OPS-2A-R5.

Decision: supplementary groups are approval-bound only when the access basis is
`group` and the relevant group membership is required. Owner-based and
other-bit access record groups as observations.

Reason: group listings may vary across execution contexts even when owner-based
permission remains unchanged. Binding irrelevant groups caused false
environment drift in SYNC-OPS-2B0.

## ADR-107: Capacity Is An Execution Predicate

Status: accepted for SYNC-OPS-2A-R5.

Decision: bootstrap plans bind a deterministic `minimum_free_bytes` threshold,
not the exact current `free_bytes` observation.

Reason: disk free space naturally changes between approval and execution. The
safe question is whether enough space remains, not whether the byte count is
identical.

## ADR-106: Machine Approval Binds Stable Security Facts

Status: accepted for SYNC-OPS-2A-R5.

Decision: bootstrap machine approval binds
`environment_binding_sha256`, computed only from stable security facts. Dynamic
observations such as generated time, free-space sample, irrelevant groups, and
diagnostic stat details are excluded from that hash.

Reason: machine approval should fail closed on root identity, mode, uid,
device, inode, action path, path-state, symlink, access-basis, or relevant
group drift, without being invalidated by unrelated operational noise.

## ADR-105: Bootstrap Execution Rechecks Plan-Bound Environment

Status: accepted for SYNC-OPS-2B0.

Decision: artifact-store bootstrap execution must rebuild the current
environment immediately before writing and compare it to the plan-bound
authorization hash. In SYNC-OPS-2B0 this used the full environment snapshot
SHA; SYNC-OPS-2A-R5 supersedes that with stable
`environment_binding_sha256`.

Reason: updating the environment hash after approval would silently move the
approval boundary. R5 keeps that fail-closed rule for stable security facts and
moves volatile capacity/diagnostic observations out of the approval hash.

## ADR-104: Sync Archives Use POSIX Entry Paths

Status: accepted for SYNC-OPS-2A-R4.

Decision: durable sync archives must use POSIX `/` entry names and reject
backslashes, absolute paths, traversal components, normalized duplicates, and
symlink entries unless a future protocol explicitly approves them.

Reason: archive artifacts may be produced or inspected on multiple platforms.
Portable entry names prevent hidden path rewriting and extraction ambiguity.

## ADR-103: Approval Requests Are Not Machine Approvals

Status: accepted for SYNC-OPS-2A-R4.

Decision: bootstrap approval requests use `requested_action_ids` and
`status=awaiting_machine_approval`. Machine approvals use
`approved_action_ids`, `status=approved`, and the approval schema. A request
object must never satisfy the approval validator.

Reason: type confusion between a request and an approval could turn a planning
artifact into execution authorization.

## ADR-102: Bootstrap Ownership Is Per-Path

Status: accepted for SYNC-OPS-2A-R4.

Decision: `STORE_METADATA.json` records an ownership ledger for each path
created by the bootstrap run. Rollback may only remove ledger paths marked
`created_by_this_run=true`.

Reason: path names alone cannot prove ownership. Durable rollback must not
delete preexisting parents, foreign paths, or store content written after
bootstrap.

## ADR-101: Bootstrap Rollback Is All-Or-Nothing

Status: accepted for SYNC-OPS-2A-R4.

Decision: bootstrap rollback performs a full read-only preflight before any
delete. If the store is non-empty, foreign, unknown, or otherwise unsafe,
rollback returns `noop_not_safe_to_remove` with `mutation_count=0`.

Reason: deleting empty sibling directories before discovering later store
content partially damages the infrastructure root while reporting a no-op.

## ADR-100: P2S Plans Require Store Metadata Before Stage Approval

Status: accepted for SYNC-OPS-2A-R3.

Decision: a P2S plan generated before `/sdb/dlut/ops-artifacts/agent-sync`
contains valid store metadata is a blocked draft. It cannot request executable
stage approval, and writer commands reject it before creating run artifacts.

Reason: stage writes need a durable, already bootstrapped artifact store for
plans, approvals, journals, locks, validation, and closeout evidence.

## ADR-099: Bootstrap Creates Only Exact Approved Paths

Status: accepted for SYNC-OPS-2A-R3.

Decision: artifact-store bootstrap can create only the exact directories listed
in the bootstrap plan and write only `STORE_METADATA.json`. It never guesses
ownership, recursively creates arbitrary parents, chowns, chgrps, or sets
setuid/setgid bits.

Reason: the current parent and root are missing. Safe initialization must be a
reviewable infrastructure transaction, not a broad mkdir side effect.

## ADR-098: Artifact Store And Sandbox Filesystem Rules Are Separate

Status: accepted for SYNC-OPS-2A-R3.

Decision: artifact-store atomic writes require temp files in the same artifact
directory and fsync. Sandbox activation separately requires active, candidate,
and archive paths to satisfy atomic rename constraints.

Reason: coupling the artifact store to the sandbox filesystem would impose an
unnecessary storage constraint and confuse evidence persistence with sandbox
activation safety.

## ADR-097: Artifact Store Bootstrap Is One-Time Infrastructure

Status: accepted for SYNC-OPS-2A-R3.

Decision: durable artifact-store bootstrap is a one-time approved
infrastructure operation, not an implicit P2S stage side effect.

Reason: every P2S run needs artifacts, but each run must not independently
decide how to create the long-lived evidence root.

## ADR-096: Plan Metrics Use One Structured Summary Source

Status: accepted for SYNC-OPS-2A-R2.

Decision: P2S plan, closeout, CLI, and terminal metrics use the same structured
summary object for safe source, materialization, physical write, shared noop,
excluded, runtime asset, unresolved, and coverage counts.

Reason: earlier summaries mixed logical action counts with physical file writes.
A single summary prevents release notes and approval requests from drifting.

## ADR-095: Activation Approval Binds The Real Stage Closeout

Status: accepted for SYNC-OPS-2A-R2.

Decision: activation approval cannot be derived from the pre-stage plan alone.
It must bind the real stage run id, artifact index SHA, stage digest, validation
SHA, latest active pointer/tree, candidate path, and archive path.

Reason: activation mutates the active sandbox and pointer. It must be tied to
the stage that actually passed verification, not to a stale planned state.

## ADR-094: Artifact-Store Initialization Is An Approved Write Action

Status: accepted for SYNC-OPS-2A-R2.

Decision: if `/sdb/dlut/ops-artifacts/agent-sync` is missing, its
initialization is explicitly represented in the P2S execution contract and
requires stage approval.

Reason: creating the durable artifact store is a real filesystem write even
though it is not a sandbox baseline write.

## ADR-093: Executable Plans Cannot Retain Planner-Only Markers

Status: accepted for SYNC-OPS-2A-R2.

Decision: an executable P2S plan must not contain read-only planner markers,
rollback skeletons, or future-phase placeholders. The validator fails closed on
legacy markers.

Reason: the writer consumes the plan as a transaction contract. Planner-only
markers make the artifact ambiguous and unsafe for machine approval.

## ADR-092: First Real P2S Execution Uses Staged Approval

Status: accepted for SYNC-OPS-2A-R2.

Decision: the first real P2S run is split into stage/verify approval and a
later activation/rollback approval. Stage-only approval cannot archive the
active sandbox, switch the active path, update the pointer, or roll back active
state.

Reason: stage writes and active-sandbox mutation have different blast radii.
The second approval must be based on the real verified stage output.

## ADR-091: Backup And Deployment Artifacts Are Excluded From P2S

Status: accepted for SYNC-OPS-1R.

Decision: backup, predeploy, reject/orig, editor swap, and deployment snapshot
filenames are not source-bearing P2S materialization inputs. They may appear in
observed diff as runtime noise but must not become `copy_from_prod` actions.

Reason: production service roots can contain emergency backups or deployment
scratch files. Copying them into a new sandbox baseline would turn runtime
noise into experimental source authority.

Non-consequence: documented fixtures and normal versioned config files remain
eligible when they do not match backup/runtime-noise policy.

## ADR-090: Baseline-Local Metadata Is Not Production Source

Status: accepted for SYNC-OPS-1R.

Decision: sandbox-local metadata such as `SANDBOX_SECRET_REQUIREMENTS.md` is
preserved as baseline metadata, not copied from production and not modeled as a
prod-origin file action.

Reason: P2S-CLOSE-R1 generated this metadata to document sanitized sandbox
derivatives. Treating it as production source would create false source lineage
and could mask sensitive-source review needs.

Non-consequence: future automation may regenerate metadata, but only as an
explicit metadata action.

## ADR-089: Sensitive P2S Source Uses Redacted Structural Fingerprints

Status: accepted for SYNC-OPS-1R.

Decision: P2S plans must not ordinary-copy sensitive production source. For
sanitized derivatives, the planner records a redacted structural fingerprint
that replaces sensitive literals before hashing and stores only safe metadata.

Reason: the planner needs drift evidence without retaining or exposing
credential-like literals or hashes of those literals.

Non-consequence: the planner does not generate new sanitized code in
SYNC-OPS-1R. Manual derivative refresh remains a future explicitly approved
workflow.

## ADR-088: Observed Diff Is Not An Executable File-Action List

Status: accepted for SYNC-OPS-1R.

Decision: P2S observed diff explains current prod versus active/versioned
sandbox baseline. Executable future materialization is represented separately
as stage actions against a new versioned baseline path.

Reason: directly converting observations into add/replace actions hid
source-exclusion, sandbox-only metadata, and sanitized derivative semantics.

Non-consequence: observed diff remains useful for review, but it cannot by
itself authorize or execute writes.

## ADR-087: P2S Materializes A New Versioned Baseline Before Activation

Status: accepted for SYNC-OPS-1R.

Decision: P2S plans must materialize a new, missing versioned stage under the
sandbox baseline namespace before any future activation. File actions must not
target the active sandbox path.

Reason: active sandbox is the immutable current baseline and rollback source.
Writing into it directly would bypass target-drift checks and destroy the
previous baseline before validation.

Non-consequence: SYNC-OPS-1R still does not create the stage or switch the
baseline pointer; it only plans and validates.

## ADR-086: Sanitized Sandbox Derivatives Are Non-Publishable By Default

Status: accepted for SYNC-OPS-1.

Decision: sandbox-only sanitized derivatives in a production-derived baseline
must not be published back to production by default. An S2P planner must block
direct file actions from such derivatives unless a future explicit
prod-safe-config-refactor change unit and hash-bound approval record exists.

Reason: P2S-CLOSE-R1 intentionally replaced credential-bearing production
source with sandbox-only derivatives. Publishing those derivatives back to prod
could change runtime configuration semantics and erase production-only secure
source.

Non-consequence: this does not make production the owner source authority and
does not prevent a reviewed owner-safe refactor later.

## ADR-085: Publish-And-Rebase Defers P2S Until S2P Settles

Status: accepted for SYNC-OPS-1.

Decision: a cycle plan may reference an immutable S2P plan and approval
requirements, but it must defer P2S rebase generation until all started S2P
transactions settle against the real production after-state.

Reason: precomputing the future production tree would hide target drift,
rollback, partial success, and external owner deployments.

Non-consequence: this does not execute any S2P or P2S transaction in
SYNC-OPS-1.

## ADR-084: Active Sandbox Baseline Is Immutable

Status: accepted for SYNC-OPS-1.

Decision: the active external-agent sandbox baseline is not a writable
experiment workspace. Experiments must fork from the versioned baseline and
carry an experiment manifest that binds the base baseline id and hash.

Reason: after P2S-CLOSE-R1 the active sandbox path represents the current
production-derived baseline. Mutating it directly would destroy the B/S/P/D
diff source.

Non-consequence: this does not delete or rewrite old sandbox experiments.

## ADR-083: Static Service Registry Excludes Transient Process State

Status: accepted for SYNC-OPS-1.

Decision: `config/ops/agent_service_registry.json` stores stable Agent identity,
path, contract, ownership, transaction, and sync policy metadata only. PID,
listener state, process start time, elapsed time, raw command line, health
result, compute result, endpoint response, and environment values belong only
in generated runtime inventory snapshots.

Reason: plan hashes and registry hashes must remain stable across process
restarts and live diagnostics. Transient runtime state cannot be a source of
truth for sync planning.

Non-consequence: future apply/smoke phases may still collect bounded process
preflight evidence before a write transaction.

## ADR-082: Bidirectional Sync Uses Immutable Plans And Hash-Bound Approval

Status: accepted for SYNC-OPS-1.

Decision: external-agent P2S, S2P, and publish-and-rebase flows use immutable
canonical JSON plans. Any future write command must read a file-based approval
record bound to the exact plan SHA256. Chat acknowledgements are not machine
approval.

Reason: external Agent directories have different authorities and may drift
between planning and application. Hash-bound plans plus target-before hashes
are required to prevent stale or ambiguous writes.

Non-consequence: SYNC-OPS-1 implements only read-only planning and validation;
it does not apply, lock, back up, restart, smoke, or roll back.

## ADR-081: Sensitive Production Source Is Never Copied Verbatim Into Sandbox

Status: accepted for P2S-CLOSE-R1.

Decision: production source-bearing files that contain sensitive literals must
not be copied verbatim into sandbox baselines. A sandbox baseline may use a
sandbox-only sanitized derivative that replaces the sensitive literal with an
explicit environment-variable lookup and empty default, or it may omit a file
that is proven unreachable legacy/test material. Both paths require manifests,
line-range classification, source and derivative hashes, and offline validation.

Reason: the prod-to-sandbox baseline is meant to give future experiments a
current runtime-code starting point, not to spread production credentials or
private runtime material into sandbox.

Consequence: P2S-CLOSE-R1 resolved the `value_research_synthesis` and
`macro_index_valuation` blockers with sanitized derivatives, safely omitted one
unreachable legacy test file containing token-like test material, and then
switched the fixed external-agent sandbox path to the validated 26-agent
baseline.

Non-consequence: this does not modify production, owner-dev repositories,
service processes, runtime bindings, live flags, providers, endpoint behavior,
model/data assets, or owner source authority.

## ADR-080: External Agent Sandbox Experiments Rebase On Versioned Production Runtime Snapshots

Status: accepted for P2S-BASELINE-X.

Decision: after a completed external-agent backfill and production release
cycle, future external-agent sandbox experiments should start from a versioned
source-bearing snapshot of the current production runtime roots. The snapshot is
used only as an experiment baseline. It does not make production the owner-dev
source authority.

The main-system sandbox follows a different rule: it must be refreshed from the
current main-system dev HEAD, not from `/sdb/dlut/prod/langgraph-my-agent`.

Reason: production external-agent roots can contain user backfill, post-release
runtime fixes, and service-owner deployments that old sandbox trees do not
have. Starting new experiments from stale sandbox code risks reintroducing
fixed integration bugs.

Consequence: a prod-to-sandbox refresh must stage first, archive old sandbox
experiments, exclude secrets/runtime data/logs/cache/models/large datasets, and
switch the current sandbox only after validation. P2S-BASELINE-X staged a
26-agent baseline; P2S-CLOSE-R1 resolved the sensitive-source blockers and
switched the current sandbox path.

Non-consequence: this does not modify production, owner-dev repositories,
runtime bindings, live flags, service processes, or provider/invoke behavior.

## ADR-079: Non-L4 Production Compute Uses Dedicated Orchestration

Status: accepted for POST-BF-B2X.

Decision: initial non-L4 production external compute is implemented by a
dedicated policy and orchestration path:
`config/fixed_dag/non_l4_external_compute_policy.json`,
`src/react_agent/fixed_dag_non_l4_runtime_registry.py`, and
`src/react_agent/fixed_dag_production_external_compute.py`.

The path is separate from the default-off demo bridge and separate from the L4
`external_compute_default` runtime binding path. Demo mode suppresses
production non-L4 for that run. Non-L4 rollback uses
`DISABLE_NON_L4_EXTERNAL_COMPUTE_DEFAULT=1` and does not disable L4.

Reason: controlled demo evidence proved mappability but was not a production
runtime. Extending L4 runtime bindings to non-L4 would weaken the registry
contract that currently limits `external_compute_default` to
`decision_synthesizer` and `report_generator`.

Consequence: the initial production default set is the explicit B1X readiness
subset: 9 required agents plus optional degraded `macro_composite` after its
canary. Required failures fail soft to existing deterministic/pending
contracts and final answer emission continues. Public `externalInvoked` keeps
its existing no-`/invoke` meaning; actual compute activity is recorded in
private `production_external_compute_*` provenance.

Non-consequence: this does not edit `runtime_bindings.json`, set live flags,
enable `/v1/agent/invoke`, call providers, enable L1 external defaults, or
activate excluded agents.

## ADR-078: Production Readiness Is Separate From Runtime Activation

Status: accepted for POST-BF-B1X.

Decision: post-backfill production readiness may improve service liveness,
contract readiness, data readiness, latency, and semantic gates without
activating non-L4 agents in the default product runtime. The production
activation candidate set is an input to a later orchestration phase, not a
runtime binding edit.

Reason: the backfill ledger is closed, but normal user requests still have only
the two L4 `external_compute_default` services enabled. Controlled demo bridge
evidence proves mappable compute paths, not default runtime behavior.

Consequence: readiness docs now distinguish `service_alive`,
`contract_available`, `compute_available`, `data_dependency_ready`, and
`ready_for_default_runtime`. Entity and sentiment services can remain healthy
but degraded and explicitly not default-ready.

Non-consequence: this does not modify `runtime_bindings.json`, set live flags,
enable external invoke, call providers, or change model/scoring/feature/training
or fusion logic.

## ADR-077: Backfill Completeness Is A Change-Unit Ledger

Status: accepted for BF-COMPLETE-X.

Decision: sandbox-to-prod backfill completeness is measured by
current-relevant integration change units, not by agent readiness, health-pass
counts, or owner-dev durability. A unit is complete when production has exact,
semantic-equivalent, or stricter verified behavior for the sandbox integration
fix.

Reason: using 27-agent coverage or owner-dev source status conflates separate
workstreams and misstates sandbox-to-prod backfill progress.

Consequence: BF-COMPLETE-X keeps the denominator at the audited 31 units,
closes the two remaining entity/sentiment units, and records final-trace
validation separately from the ledger ratio. BF-CLOSE-R1 then revalidated the
transient `value_traditional_valuation` timeout, so backfill scope status is
`complete` and integrated trace status is recorded separately as `pass`.

Non-consequence: this does not authorize copying entire sandbox directories,
changing runtime bindings, or treating owner-dev acceptance as a prerequisite
for production backfill completion.

## ADR-076: L3 Real Contributors Are Not The Same As Formal Slots

Status: accepted for CS1-C3R evidence integrity closure.

Decision: L3 composites may retain formal member slots for coverage tracking,
but only members with current-run usable status, positive confidence, and
bounded business material may be treated as real contributors. Pending, error,
zero-confidence, no-evidence, deterministic-placeholder, or failed-external
fallback slots must have zero weight and must not appear as contributors,
evidence refs, or main report members.

Reason: CS1-C3X showed market formal slots for `sentiment_company_radar` and
`market_fund_manager_behavior` with zero confidence but positive weight and
public report wording. That made missing evidence look like real contribution.

Consequence: adapters, deterministic L3 builders, trace summaries, and report
projection now separate formal coverage slots from real evidence contribution.

Non-consequence: this does not change business fusion algorithms, model
weights, features, scoring, training, data sources, or runtime bindings.

## ADR-075: Prod Wrapper Evidence Requires Owner-Source Durability

Status: accepted for CS1-C3X source durability closure.

Decision: a production wrapper patch is not considered durable merely because
it passed live smoke. It must either be present in the owner-dev source or have
a reviewable owner handoff patch with before/after hashes, dry-run apply
status, test plan, and rollback notes.

Reason: CS1-C1X and CS1-C2X intentionally patched production runtime copies
for controlled readiness. Those runtime copies are nongit service directories
and can drift away from service-owner repositories.

Consequence: readiness docs now distinguish live production evidence from
source durability. Owner handoff artifacts live outside the main-system repo
under production backup roots.

Non-consequence: this does not authorize modifying owner-dev repositories and
does not copy external service source into the main-system repo.

## ADR-074: External L3 Members Must Be Formal And Dimension-Scoped

Status: accepted for CS1-C3X macro contract closure.

Decision: external L3 composite member packets must use unique formal fixed-DAG
member ids for their dimension. Service-local aliases, Chinese names, legacy
ids, and local diagnostic stand-ins may not masquerade as formal DAG members.

Reason: CS1-C2X exposed a macro packet where local `valuation_index` and
`industry_hotspot` stand-ins were mixed with formal macro upstream outputs.
That made report material look thicker than the formal DAG evidence actually
was.

Consequence: the macro adapter now fails closed on noncanonical or duplicate
macro members, and the macro service wrapper projects only the five formal
macro L2 slots. Missing formal members may remain pending/partial with zero
weight.

Non-consequence: this does not change macro regime, dimension weights, risk
sensitivity, value/market/risk composites, or any business fusion algorithm.

## ADR-073: Public Trace Acceptance Requires Pre-Scrub Safety

Status: accepted for CS1-C2X public boundary closure.

Decision: controlled trace runners must validate the real PublicTurn and
Workflow objects before artifact scrub. Scrubbing remains defense in depth for
stored artifacts, but it is not allowed to be the reason a public contract is
safe.

Reason: CS1-C1X produced a valid sanitized artifact but the unsanitized workflow
still carried an unsafe endpoint literal in provenance limitations, and its
runner called `build_assistant_turn` with the wrong argument shape.

Consequence: future trace QA must call `build_assistant_turn(full_state,
"replay")`, validate the PublicTurn/AnswerCard/Workflow models, and scan the
original public object for unsafe markers before serialization.

Non-consequence: this does not expose raw graph state, raw service responses,
provider output, endpoints, or hidden reasoning in public transcript content.

## ADR-072: Request-As-Of Requires Real Data-Window Compliance

Status: accepted for CS1-C2X temporal service closure.

Decision: service-side historical fixes must make the business data window
respect requested `as_of`; changing only the response date label is not a valid
fix. The main-system bridge projects the requested date through compatible
aliases, and the temporal guard remains fail-closed if a service still returns
future-dated material.

Reason: CS1-C1X showed services that were reachable and adapter-compatible but
ignored the requested historical boundary because they read different `as_of`
field names or fell back to latest data.

Consequence: controlled compute evidence for a historical request must show
`as_of` and `data_as_of` no later than the request date before it can enter
report input bundles.

Non-consequence: this does not change service models, training vintages,
scoring logic, feature engineering, or fusion algorithms.

## ADR-071: Request-As-Of Is A Hard Cross-Request Boundary

Status: accepted for CS1-C1X readiness convergence.

Decision: external compute results that carry dates must satisfy
`mapped.as_of <= requested_as_of` and
`mapped.data_as_of <= requested_as_of` before they are allowed into fixed-DAG
state or report bundles. The bridge owns this cross-request check because it
has the requested `as_of`; the pure adapter continues to validate only payload
internal consistency.

Reason: CS1-B2X showed services returning 2026 dates for a 2024-12-31 request.
Accepting those mapped objects would turn endpoint availability into
look-ahead evidence. The correct behavior is fail-closed with a bounded reason
and deterministic/pending fallback.

Consequence: services with future-dated outputs can be health-compatible and
still be rejected from evidence bundles for historical requests.

Non-consequence: this does not change scoring, service models, runtime
bindings, or public transcript contracts.

## ADR-070: External Health Identity Has Migration Profiles

Status: accepted for CS1-C1X readiness convergence.

Decision: health identity validation is separated from compute adapter
identity. Health may pass through `canonical`,
`explicit_bridge_compatibility`, or `registered_legacy_compatibility` profiles
only when ids and aliases are source-controlled and source/port ownership has
been verified by the caller.

Reason: CS1-B1/CS1-B2X showed multiple production services with fixed-DAG
compatible compute wrappers but service-local health `agent_id` fields. Treating
all such payloads as health failures was too strict for migration auditing, but
loosening compute identity would be unsafe.

Consequence: compatibility health pass is explicit migration debt. It may
allow a controlled compute probe, but it is not canonical service-contract
completion and does not prove compute/adapter/invoke/runtime readiness.

Non-consequence: compute adapter identity remains strict. Fuzzy matching,
Chinese-name matching, legacy `aNN` primary ids, and routing
`sentiment_company_radar` to risk remain forbidden.

## ADR-069: L4 Default Runtime Uses Compute-Only External Bindings

Status: accepted for R8-13Q runtime enablement.

Decision: `decision_synthesizer` and `report_generator` now use
`external_compute_default` runtime bindings. The executor reads these bindings
and calls the L4 services through `/v1/agent/compute` without enabling the
default-off demo bridge and without calling `/v1/agent/invoke`.

Reason: the L4 services were implemented and validated as compute-only
decision/report services. Reusing invoke-oriented fields or the demo bridge as
the default runtime path would blur the evidence boundary and make rollback
unclear.

Consequence: L4 default runtime is now controlled by `runtime_bindings.json`.
`disable_external_compute_default` can disable the default path for tests or
rollback while keeping deterministic L4 behavior available.

Non-consequence: this does not enable `/v1/agent/invoke`, does not modify
`.env`, and does not make non-L4 external candidates default runtime services.

## ADR-068: L4 Runtime Binding Needs Schema and Executor Support Before Config Edit

Status: accepted for R8-13P preflight.

Decision: R8-13P adds `build_l4_runtime_binding_phase_plan` as a non-mutating
preflight. Even with a fully ready runtime-review evidence package, the plan
does not allow a direct edit to `config/fixed_dag/runtime_bindings.json`.
Current runtime bindings only model deterministic L4 seams and disabled
external HTTP candidates; they do not model an enabled external L4
`/v1/agent/compute` default path.

Reason: changing the JSON alone would either violate the existing validator or
misuse invoke-oriented fields for compute-only L4 services. The correct next
implementation phase must extend the runtime binding schema and teach the
executor how to use an external compute default path for the two L4 ids.

Consequence: the next implementation work is not a blind config edit. It is a
scoped runtime schema/executor phase with rollback tests. The current preflight
still reports `runtime_bindings_changed=false` and `config_edit_allowed=false`.

Non-consequence: this does not call endpoints, does not edit `.env`, does not
edit runtime bindings, does not set live/default flags, and does not enable
external L4 by default.

## ADR-067: R8-13O Candidate Evidence Still Requires Operator Approval

Status: accepted for R8-13O evidence closure.

Decision: R8-13O adds `build_l4_runtime_review_candidate_package` as the
repo-recorded L4 runtime review evidence package. It marks provider compute
evidence, transcript safety evidence, and rollback-plan evidence as passing
based on current repository artifacts. It deliberately keeps
`operator_approval` failing until a user explicitly approves opening a runtime
binding phase.

Reason: three of the four runtime-review prerequisites can be backed by current
files and tests, but runtime binding approval is an operator decision. Treating
a generic "continue" instruction as approval to edit runtime configuration would
collapse the safety boundary established in R8-13L through R8-13N.

Consequence: the project can now show a concrete candidate package whose only
remaining blocker is `operator_approval_missing`. This makes the next gate
clear without editing `config/fixed_dag/runtime_bindings.json`.

Non-consequence: this does not call endpoints, does not modify `.env`, does not
edit runtime bindings, does not set live/default flags, and does not make L4
external services the default graph path.

## ADR-066: L4 Runtime Review Evidence Package Is Required Before Binding Phase

Status: accepted for R8-13N review packaging.

Decision: R8-13N adds `fixed_dag_l4_runtime_review_evidence_package_v1` through
`build_l4_runtime_review_evidence_package`. The package requires four safe
evidence records before it can report
`ready_for_explicit_runtime_binding_phase`: provider compute pass, transcript
safety pass, rollback plan readiness, and operator approval. Each record must
pass and include a safe artifact reference; unsafe text or missing references
keep the package blocked.

Reason: L4 provider-backed compute is now possible, but changing default runtime
behavior requires a stricter handoff than an ad hoc checklist. The evidence
package makes the review repeatable and prevents runtime binding changes from
being justified by vague or unsafe evidence.

Consequence: maintainers can assemble evidence without calling endpoints or
editing config. The package embeds the R8-13M dry run and keeps the same
non-actions: no endpoint call, no `.env` change, no runtime binding edit, no
live flag change, and no default invoke change.

Non-consequence: `ready_for_explicit_runtime_binding_phase` is not runtime
approval and does not modify `config/fixed_dag/runtime_bindings.json`. A
separate user-approved runtime-binding phase must still own any actual config
edit.

## ADR-065: L4 Runtime Binding Dry Run Is Metadata Only

Status: accepted for R8-13M dry-run design.

Decision: R8-13M adds `fixed_dag_l4_runtime_binding_dry_run_v1` through
`build_l4_runtime_binding_dry_run`. The dry run reads current deterministic L4
runtime bindings and produces a review plan for `decision_synthesizer` and
`report_generator`, including proposed compute URLs, readiness booleans,
blocking reasons, and next action. It never writes
`config/fixed_dag/runtime_bindings.json` and always reports
`runtime_bindings_changed=false`, `default_runtime_enabled=false`, and
`invoke_endpoint_required=false`.
Current L4 binding flags are explicitly scoped as
`deterministic_internal_l4_seam`; proposed external L4 flags remain false in the
dry-run output.

Reason: after R8-13J/R8-13K/R8-13L, the project has provider-backed L4 compute
evidence, transcript-safety regression tests, and a runtime review checklist.
The next useful step is to make the future runtime review executable as a
repeatable metadata check before any configuration edit.

Consequence: maintainers can tell whether missing prerequisites are
`provider_compute_pass`, `transcript_safety_pass`, `rollback_plan_ready`, or
`operator_approval` without touching runtime config. Even when all booleans are
true, the output is only `ready_for_runtime_binding_review`; a separate phase
must still own any real runtime binding edit.

Non-consequence: this does not call endpoints, does not modify `.env`, does not
edit `config/fixed_dag/runtime_bindings.json`, does not set `live_verified=true`
or `invoke_enabled_by_default=true`, does not call `/v1/agent/invoke`, and does
not make external L4 services default graph dependencies.

## ADR-064: L4 Provider Compute Pass Does Not Enable Runtime Binding

Status: accepted for R8-13L runtime review preparation.

Decision: R8-13J provider-backed `/v1/agent/compute` pass for
`decision_synthesizer` and `report_generator` is accepted as L4 compute
readiness evidence, but not as default runtime enablement. The active
`runtime_bindings.json` rows for these ids remain deterministic L4 seams:
`deterministic_decision` and `deterministic_report`, with no external agent id,
environment variable, or default URL. Any future move to a default external L4
runtime path requires a separate runtime-binding phase.

Runtime review checklist:

- public answer safety: mapped `report_result_v1.answer`, sections, evidence
  cards, and limitations must remain free of raw provider output, secrets,
  endpoint URLs, tracebacks, raw external JSON, and chain-of-thought markers;
- workflow detail safety: public workflow step results must not expose provider
  raw responses, endpoint URLs, credentials, or internal LLM drafts;
- fallback and rollback: provider timeout, invalid JSON, unsafe output, or
  adapter failure must fall back to deterministic L4 results without breaking
  final answer emission;
- operator control: runtime binding changes must be reviewable, reversible, and
  scoped only to the two L4 ids;
- provider hygiene: credentials stay in process environment or secret storage,
  never in docs, logs, runtime bindings, public payloads, or test artifacts;
- evidence separation: `/v1/agent/compute` evidence must not be described as
  `/v1/agent/invoke` evidence.

Consequence: R8-13K/R8-13L can strengthen tests and documentation while
leaving active runtime behavior unchanged. Provider-backed L4 compute can be
used only through explicit default-off allowlists until a later phase owns
runtime binding edits.

Non-consequence: this ADR does not call endpoints, does not modify `.env`, does
not edit `config/fixed_dag/runtime_bindings.json`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, and does
not make external L4 services default graph dependencies.

## ADR-063: L4 Decision And Report Agents Use Default-Off Compute Handoff Before Runtime Enablement

Status: accepted for dev main-system handoff and controlled validation.

Decision: the main system now treats `decision_synthesizer` and
`report_generator` as formal L4 agent ids that can be overlaid through the
default-off external compute demo bridge. `decision_synthesizer` consumes a
bounded view of the current-run L3 dimension results and returns
`decision_result_v1`; `report_generator` consumes the bounded decision result
plus `report_input_bundle_v1` and returns `report_result_v1`. Both mappings are
compute-only, allowlist-only, and validated by the main-system adapter before
they can replace deterministic fallback outputs.

Reason: the fixed DAG roster has always included two L4 agents, but keeping
them only as internal deterministic seams made it impossible to validate the
teacher-facing requirement that final decision synthesis and final report
generation can be owned by agents with the same status as the other DAG nodes.
At the same time, L4 is the public transcript boundary, so direct runtime
enablement would be unsafe without an explicit bounded-contract handoff first.

Consequence: controlled sandbox or dev validation can run L4 as external
`/v1/agent/compute` services without changing runtime bindings or live flags.
If an external `report_generator` result maps successfully, the executor must
not overwrite it with the internal LLM report synthesis seam in the same run.
The public answer card may carry structured report sections, evidence cards,
and limitations from `report_result_v1`, but it must not expose raw graph
messages, raw agent JSON, raw provider output, endpoint URLs, tracebacks,
secrets, or internal reasoning drafts.

Non-consequence: this does not make L4 production-ready, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
modify `config/fixed_dag/runtime_bindings.json`, does not call external
`/v1/agent/invoke`, and does not turn demo `/compute` evidence into invoke or
production readiness evidence. Production L4 readiness still requires a
separate service-owner path, controlled `/health` + `/v1/agent/compute`
evidence, adapter mapping review, and explicit runtime-binding review.

## ADR-062: R8-13J Adds A Next Phase Roadmap Without Runtime Change

Status: accepted.

Decision: the main-system docs now include
`docs/NEXT_PHASE_ROADMAP_FIXED_DAG.md` as the current roadmap entry point. The
roadmap consolidates current fixed DAG progress, A/B/C agent work classes,
near-term demo trace and A-class remediation priorities, medium/long-term
runtime preparation, and documentation cleanup guidance.

Reason: the project accumulated accurate but distributed status across the
readiness matrix, smoke log, demo runbooks, changelog, ADRs, and phase handoff
docs. A new Codex session can understand the repository, but only after reading
many files. The roadmap gives future sessions one planning-oriented entry point
without deleting the audit trail.

Consequence: future planning should start with the roadmap, then drill into the
readiness matrix and smoke log for evidence. The roadmap is not runtime
authority, does not modify `runtime_bindings.json`, does not set live flags,
does not call endpoints, and does not promote demo evidence into production
readiness.

## ADR-056: R8-13I Defines Dev Sandbox Prod Roles And Documentation Authority

Status: accepted.

Decision: the main-system repository now documents a three-directory operating
model on this server. `/sdb/dlut/dev/langgraph-my-agent` is the source-controlled
development authority, `/sdb/dlut/sandbox/langgraph-my-agent-r8-a-class` is an
experiment area, and `/sdb/dlut/prod/langgraph-my-agent` is a runtime/deployment
copy. The docs index points to `docs/REPO_ENVIRONMENT_AND_DOCS_GUIDE.md` as the
current guide for directory roles, sync policy, and documentation authority.

Reason: recent R8-12/R8-13 work used all three directories. Without an explicit
operating model, it is easy to mistake sandbox experiments or prod runtime
copies for the long-term source of truth. The project also accumulated many
phase-specific documents; deleting them would lose audit and rollback context,
but leaving them unclassified makes the current authority hard to find.

Consequence: future main-system work should be committed and pushed from dev,
sandbox work should be backfilled into dev before it becomes authoritative, and
prod should be updated from stable pushed commits. Phase documents remain
historical records until a dedicated docs-compaction phase merges them into
current authority documents. Other `/sdb/dlut/dev/*` agent repositories remain
owned by their respective developers; user sandbox agent experiments and
developer-owned dev-agent changes reach prod through separate owner-controlled
flows.

## ADR-055: R8-13H Tests A-Class L1/L2 Bridge In Sandbox Before Prod Backfill

Status: accepted for sandbox validation.

Decision: R8-13H ports sandbox-validated default-off external compute bridge
support for A-class remediation candidates into the main development branch.
L1 `financial_data_service` and
`entity_relation_extractor` may be mapped into the executor before L2
`agent_task_v1` construction, and macro L2 `macro_commodity_pricing` /
`macro_index_valuation` may be allowlisted as `agent_conclusion_v1` compute
candidates.

Reason: L2 agents need structured data and entity evidence in their task
payloads. Calling L2 compute while L1 remains placeholder makes the demo look
connected while still starving downstream agents of the evidence they are
supposed to read.

Consequence: the sandbox can validate the data-flow shape without touching
production services, runtime bindings, live flags, or `/v1/agent/invoke`. This
does not create production readiness evidence. Production re-smoke and service
owner backfill remain separate phases.

## ADR-001: Fixed DAG Replaces Route Mode Routing

Status: accepted for reset runtime.

Decision: the main architecture is a fixed topological DAG with explicit stages
and dimension composites.

Reason: the reset needs deterministic structure, clearer public workflow
projection, and fewer historical branches.

Consequence: old mode prompt/parser/state/public workflow code is not active
runtime authority in R3.

## ADR-002: snake_case Runtime IDs Replace aNN IDs

Status: accepted for reset target; active for backend catalog projection in
R4-A, runtime binding metadata in R4-B, and legacy boundary isolation in R4-C.

Decision: target formal agents use descriptive `snake_case` ids.

Reason: ids should carry stable role meaning and avoid coupling new architecture
to old catalog numbering.

Consequence: the fixed DAG catalog uses `snake_case` ids as active reset public
catalog truth. Legacy aNN config files remain as explicit migration/readiness
input but are not active reset graph registration truth.

## ADR-003: Sentiment Radar Belongs To Market L2

Status: accepted for reset runtime.

Decision: the company sentiment radar belongs in the market dimension as an L2
signal, not as a cross-cutting risk input and not as a fifth dimension composite.

Reason: v4 feedback aligned the radar to market sentiment, heat, and attention.
Risk handling remains owned by explicit risk L2 agents and the risk composite.

Consequence: L3 has four composites: value, market, risk, and macro.
`sentiment_company_radar` routes to `market_composite` only.

## ADR-004: Pre-Reset Tag Preserves Old History

Status: accepted.

Decision: old docs, data, archive tests, and training lineage removed in R1-A
are recovered through `pre-fixed-dag-reset-20260604-1457`.

Reason: the active reset branch should stay small and unambiguous.

Consequence: current docs should not link old lineage as active authority.

## ADR-005: Frontend Shell Is Retained For Later In-Place Rewrite

Status: accepted for reset.

Decision: R1-B keeps `apps/web` while replacing the Python public workflow
contract.

Reason: the frontend workflow inspector rewrite is separate from the runtime
protocol skeleton.

Consequence: frontend v2 is deferred to R5.

## ADR-006: R1-B Uses Deterministic Provider-Free Skeleton

Status: accepted.

Decision: R1-B active runtime does not call providers, search, external agents,
A01 contract dispatch, mode-based manager assignment, baseline sidecar, or Fair
Fusion. It emits deterministic placeholder objects with reset schemas.

Reason: this phase validates protocol topology before business implementations
or live service readiness.

Consequence: tests can claim skeleton import/invoke/public projection only; they
cannot claim live analysis, provider readiness, external readiness, or production
readiness.

## ADR-007: V4 Feedback Sets The 27-Agent Formal Roster

Status: accepted for reset runtime.

Decision: the active reset roster has 27 formal agent ids: L1=3, L2=18, L3=4,
L4=2. The enterprise financial analysis target is removed.

Reason: the v4 feedback table is the reset roster authority for R1-B-Delta.

Consequence: tests and docs must not describe pre-delta target counts as current
runtime facts.

## ADR-008: R2 Uses Contract And Function Seams

Status: accepted for reset runtime.

Decision: fixed DAG payloads are generated through deterministic constructors,
normalizers, and validators in `fixed_dag_contracts.py`.

Reason: graph nodes and public workflow fallbacks need stable protocol objects
before business algorithms, registry migration, or frontend workflow UI work.

Consequence: R2 hardens the skeleton contracts but does not implement real
business agents, provider readiness, external service readiness, frontend v2, or
mainline/fusion-gate reset quality gates. These seams are the prerequisite for
R3 executor orchestration.

## ADR-009: R3 Uses Plan-Driven Fixed DAG Executor

Status: accepted for reset runtime.

Decision: after L1 preparation, the active graph delegates deterministic
orchestration to `execute_fixed_dag`.

Reason: execution order should be derived from validated
`dag_steps[].depends_on`, not from hand-maintained graph fanout nodes.

Consequence: runtime emits `fixed_dag_execution_v1`, `execution_batches`, and
`fixed_dag_step_result_v1`; public workflow snapshots include
`executionBatches` and `stepResults`. The executor remains deterministic and
provider-free.

Non-consequence: R3 does not implement real business agents, provider readiness,
external readiness, R5 frontend rewrite, R6 quality gates, or production
deployment.

## ADR-010: R3.6 Keeps Cleanup Narrow

Status: accepted for reset hygiene.

Decision: R3.6 may remove only high-confidence dead files, ignored/generated
local artifacts, and explicitly unreferenced legacy fixtures. It also commits
the v4 feedback workbook as an R4 input.

Reason: R3.5 inventory identified separate ownership for R4 catalog migration,
R5 frontend workflow rewrite, R6 quality/mainline/fusion rebuild, external
readiness, and historical artifact archive policy.

Consequence: R3.6 does not delete `config/agents`, external wrappers,
`apps/web`, baseline/fusion regression inputs, `assets/reference`, or historical
`log/tmp/outputs` artifacts.

Non-consequence: adding the workbook does not complete the R4 registry
migration, and cleanup does not prove provider, external, frontend v2,
mainline/fusion-gate, or production readiness.

## ADR-011: R4-A Uses Fixed DAG Catalog For Public Agent Projection

Status: accepted for backend catalog projection.

Decision: `config/fixed_dag/agent_catalog.json` is the active reset backend
catalog source, and `/api/agents` projects its 27 `snake_case` agents through
the existing public `AgentCatalogResponse` shape.

Reason: public workflow steps already use fixed DAG ids. Keeping `/api/agents`
on old aNN config metadata makes the public catalog disagree with runtime DAG
steps and hides the R4 target roster.

Consequence: in R4-A, `/api/agents` reports `configCount=27`,
`runtimeCount=27`, `disabledIds=[]`, and layer counts L1=3, L2=18, L3=4, L4=2.
Old `config/agents/*.json` remains in the repo as legacy migration input for
external wrapper and cleanup phases, but it is no longer the active reset public
catalog truth.

Non-consequence: R4-A does not implement real business agents, provider/live
readiness, external endpoint mapping, frontend workflow UI rewrite,
mainline/fusion-gate rebuild, or production deployment.

## ADR-012: R4-B Uses Runtime Bindings As Metadata, Not Live Invocation

Status: accepted for backend runtime binding registry.

Decision: `config/fixed_dag/runtime_bindings.json` is the active backend
runtime binding metadata source, and
`src/react_agent/fixed_dag_runtime_registry.py` validates it against the fixed
DAG catalog. Executor step results are annotated with binding metadata such as
runtime kind, implementation status, legacy migration id, external agent id,
invoke-enabled flag, and live-verified flag.

Reason: R4 needs an explicit bridge from fixed DAG `snake_case` ids to
deterministic seams, pending placeholders, and legacy external HTTP candidate
metadata before any later adapter or readiness work can be safely attempted.

Consequence: runtime binding ids must exactly match the 27 fixed DAG catalog
ids. External HTTP candidates are disabled by default and not live verified.
Legacy aNN ids are migration notes only and never primary reset ids.

Non-consequence: R4-B does not change active DAG topology, does not invoke
providers or external `/v1/agent/invoke` endpoints, does not expose binding
fields through `/api/agents`, does not complete frontend v2, does not rebuild
mainline/fusion gates, and does not prove production readiness.

## ADR-013: R4-C Isolates Legacy Registry From Active Fixed DAG Runtime

Status: accepted for reset runtime.

Decision: legacy aNN `AGENT_METADATA`, `AGENT_TOOLS`, metadata loading, and
bootstrap behavior live behind explicit compatibility modules. Active
`react_agent.graph` imports fixed-DAG contracts, executor, state, graph entry,
catalog, and binding seams only; it must not import or execute
`legacy_agent_registry`, `graph_bootstrap`, default LLM/search placeholder
registration, generic agent registration, or external HTTP wrapper
implementation modules.

Reason: the reset branch needs a clean runtime authority before frontend DAG UI,
external handoff docs, and later quality gate rebuilds. Keeping old registry
globals on the graph import path made legacy config appear to be active runtime
truth.

Consequence: `config/agents/*.json` is retained as migration/readiness input,
`legacy_agent_id` remains metadata in runtime bindings and step results, and
external HTTP wrapper infrastructure remains available but not live verified or
invoked by the fixed-DAG graph. The old valuation-only facade and unreferenced
JSON helper were removed after references were migrated or absent.

Non-consequence: R4-C does not implement business agent algorithms, does not
enable external candidates, does not call providers or external
`/v1/agent/invoke`, does not rewrite frontend v2, and does not rebuild
mainline/fusion gates.

## ADR-014: R5-B1 Migrates The Web Contract Before The Full Inspector Rewrite

Status: accepted for frontend contract migration.

Decision: R5-B1 updates the existing `apps/web` shell in place so frontend
workflow/chat types, streaming placeholder state, fixed DAG mocks, and smoke
fixtures consume `workflow_snapshot_v2` with `finalSource=reset_skeleton`.
The current WorkflowPanel is only minimally adapted to render DAG stages,
steps, dimension groups, execution batches, completed steps, and public
provenance.

Reason: the public adapter already emits the fixed DAG payload. Keeping the web
app on `layerPlan`, `layerMode`, `agentSteps`, `fusionSteps`, and
`mainline/baseline/fused` would make frontend tests and demos validate the old
contract instead of the active reset contract.

Consequence: frontend mocks now use the 27 enabled `snake_case` fixed DAG
catalog and v2 workflow snapshots. Public transcript remains user/assistant
text only; workflow, step results, execution batches, and runtime binding
metadata remain inspector/debug data, not transcript turns.

Non-consequence: R5-B1 does not change Python backend contracts, executor
topology, runtime bindings, `/api/agents` schema, provider readiness, external
candidate invocation, production deployment, or later quality gates. It also
does not complete the richer R5-B2 DAG timeline, dependency graph,
per-step drilldown, or evidence view.

## ADR-015: R5-B2 Rewrites The Workflow DAG Inspector UI

Status: accepted for frontend inspector UI rewrite.

Decision: R5-B2 keeps the single public user/assistant transcript and rewrites
the existing `apps/web` WorkflowPanel around `workflow_snapshot_v2`. The
inspector renders fixed DAG stage timeline, execution batches, dimension
groups, selectable DAG steps, public-safe step result metadata, final source,
and provenance. Step result metadata may show runtime kind, implementation
status, invoke-enabled status, live-verified status, and warnings.

Reason: R5-B1 aligned the frontend contract with the public fixed DAG payload.
R5-B2 makes that payload inspectable without creating separate public agent chat
lanes and without changing backend runtime authority.

Consequence: frontend mocks, smoke tests, and screenshot fixtures now validate
the inspector against `workflow_snapshot_v2` while preserving transcript safety.
`stepResults`, `executionBatches`, and runtime binding metadata remain
inspector/debug data, not transcript turns.

Non-consequence: R5-B2 does not change Python backend contracts, executor
topology, catalog source, runtime bindings, `/api/agents` schema, provider
readiness, external candidate invocation, production deployment, or later
quality gates. It does not prove business-agent correctness or live service
readiness.

## ADR-016: R5-C Keeps Normal UI Product-Facing And Moves Diagnostics Behind Disclosure

Status: accepted for frontend product polish.

Decision: R5-C keeps the single public user/assistant transcript and the
`workflow_snapshot_v2` contract, but changes the normal `apps/web` experience
to product-facing Chinese copy. Chat empty state, assistant answer cards,
workflow collapsed summaries, Agents overview, and Settings default view should
not prominently display backlog/readiness language such as pending
implementation, provider missing, external not ready, or live verification
status. Runtime enum values, provenance, provider/search/readiness flags, and
limitations remain available in expanded workflow technical details, Settings
advanced diagnostics, docs, and tests.

Reason: R5-B2/R5-B2.6 made the fixed DAG payload visible and localized, but the
normal UI still read like an engineering checklist. Product users need a calmer
research surface while reviewers still need exact technical boundaries.

Consequence: frontend mocks, smoke tests, screenshot fixture copy, public-safe
answer copy, and related assertions now validate user-facing simplification and
advanced diagnostic disclosure without changing schema, topology, or runtime
authority.

Non-consequence: R5-C does not change fixed DAG topology, roster, runtime
bindings, `/api/agents` schema, provider readiness, external candidate
invocation, production deployment, or later quality gates. It does not
prove business-agent correctness or live service readiness.

## ADR-017: R5-C1 Business Copy Avoids Implementation Notes In Default UI

Status: accepted for frontend product copy.

Decision: R5-C1 keeps the same public contracts and disclosure model, but
removes remaining implementation-note wording from default user-facing copy.
Dimension summaries should explain value, market, risk, and macro analysis in
business terms. Step summaries should not mention screenshot fixtures, rosters,
path wiring, metadata, or transcript boundaries. Answer cards should present
evidence as "研判依据" with "分析框架", "用户问题", and "流程记录" items.

Reason: R5-C reduced major engineering/status noise, but screenshots showed
remaining copy still explained internal wiring rather than user value. Business
users need professional product language by default, while reviewers can still
inspect raw protocol values in expanded technical details.

Consequence: frontend mocks, screenshot fixtures, smoke tests, public-safe
answer copy, and docs now validate default-surface business copy and guard
against fixture/roster/transcript/path-wiring terms reappearing in ordinary
chat surfaces.

Non-consequence: R5-C1 does not change fixed DAG topology, the 27-agent roster,
runtime bindings, public schemas, provider readiness, external candidate
invocation, production deployment, or later quality gates. It does not
prove business-agent correctness or live service readiness.

## ADR-018: R6-B Rebuilds Reset Mainline And Archives Fusion Gate

Status: accepted for reset quality.

Decision: `scripts/quality/run_quality.py --mode mainline` is the default
fixed-DAG reset quality gate and runs static, unit, public-api, graph-smoke,
and frontend. It does not run `fusion-gate`.

Reason: the reset branch needs a non-provider, non-live, non-artifact default
quality closure that matches the active fixed-DAG runtime and frontend shell.
The old mainline mixed in the historical fusion regression gate, and the old
frontend mode could write `apps/web/dist`.

Consequence: the frontend mode performs TypeScript no-emit, frontend smoke,
and Vite build with a temporary repo-external `--outDir`. PR/push CI no longer
blocks on fusion-gate. `fusion-gate` remains explicit archived/manual lineage.
Provider live smoke remains optional live/manual or scheduled.

Non-consequence: R6-B does not change fixed DAG topology, the 27-agent roster,
runtime bindings, public schemas, frontend product UI, provider readiness,
external `/v1/agent/invoke` readiness, production deployment, Router-SFT, or
RARP/route-prior lineage. Passing reset mainline does not prove live services
or restored fusion acceptance.

## ADR-019: R7-B Standardizes Fixed DAG External Handoff By Contract

Status: accepted for external developer documentation.

Decision: R7-B external developer onboarding is standardized through fixed DAG
ids, runtime binding metadata, contract mapping, sample payloads, a sample-only
local scaffold, and an explicit readiness ladder. The handoff does not require
every external agent to use the same internal implementation mode.

Reason: later external services may be implemented as deterministic services,
machine-learning services, data services, LLM services, LLM-with-tools services,
or hybrids. The reset architecture needs stable boundary contracts and review
evidence without coupling the platform to one implementation style.

Consequence: new docs and the sample scaffold define how external envelopes
should map to `conclusion_object_v1`, `dimension_composite_result_v1`,
`decision_result_v1`, `report_result_v1`, `data_bundle_v1`, and
`entity_relation_bundle_v1`; how readiness moves from docs-only review to
controlled live verification; and what cannot be treated as runtime truth.

Non-consequence: R7-B does not change fixed DAG topology, the 27-agent roster,
runtime bindings, public schemas, frontend product UI, provider readiness,
external `/v1/agent/invoke` readiness, production deployment, Router-SFT, or
RARP/route-prior lineage. It does not register the sample scaffold into the
graph, enable a wrapper, live-verify an external service, restore old `aNN`
catalog authority, restore `value_financial_analysis`, or route
`sentiment_company_radar` into risk.

## ADR-020: R7-C Keeps External Scaffold Source And Repo Mirror Aligned

Status: accepted for external developer package governance.

Decision: R7-C upgrades the original repo-external scaffold source package at
`E:\muti-agent\external_agent_scaffold` and syncs its contents into the tracked
repo mirror `examples/fixed_dag_external_agent_scaffold/`. The package uses
fixed DAG `agent_id`, `external_agent_id`, and migration-only `legacy_agent_id`
fields; it does not use old `main_agent_id` or aNN primary ids in the current
schema path.

Reason: external developers receive the repo-external package, while reviewers
need a tracked copy for diffs, docs, tests, and changelog history. Maintaining
one package shape in both locations prevents the old v2.1-v2.2.1 scaffold
lineage, `AGENT_TOOLS`, `config/agents`, and aNN id assumptions from drifting
back into handoff instructions.

Consequence: scaffold docs, schemas, service code, samples, and tests must stay
aligned between the external source package and the repo mirror. Local tests
may prove endpoint shape, schema mapping, typed errors, anti-lookahead,
confidence bounds, evidence, event flags, and no-provider/no-external-call
sample behavior.

Non-consequence: R7-C does not change fixed DAG topology, the 27-agent roster,
runtime bindings, public schemas, frontend product UI, provider readiness,
external `/v1/agent/invoke` readiness, production deployment, Router-SFT, or
RARP/route-prior lineage. It does not register the scaffold into the graph,
enable a wrapper, live-verify an external service, restore
`value_financial_analysis`, restore a 28-agent roster, or route
`sentiment_company_radar` into risk.

## ADR-021: R7-D Separates Scaffold Contract From Legacy Wrapper Compatibility

Status: accepted for external handoff documentation consistency.

Decision: R7-D keeps the fixed DAG scaffold contract authoritative for new
external services and documents legacy wrapper compatibility as a maintainer
bridge concern. External developers should implement `agent_id`,
`external_agent_id`, `legacy_agent_id`, `/health`, `/v1/agent/compute`, and
`/v1/agent/invoke` as shown in the scaffold package, not the older
`main_agent_id` wrapper context shape.

Reason: the repo still retains legacy external wrapper compatibility code for
old aNN services, but the fixed DAG reset branch must not let that compatibility
shape become the current handoff contract. R7-D also clarifies status mapping
across external service status, adapter decision, and fixed DAG validator
status.

Consequence: source package docs, repo mirror docs, payload mapping docs,
quality docs, and changelog now describe the same handoff boundary. The sample
mapper reads `legacy_agent_id` from the response being mapped instead of a
global sample constant.

Non-consequence: R7-D does not change active runtime behavior, fixed DAG
topology, the 27-agent roster, runtime bindings, public schemas, frontend
product UI, provider readiness, external `/v1/agent/invoke` readiness,
production deployment, Router-SFT, or RARP/route-prior lineage. It does not
enable wrappers, set `live_verified=true`, set `invoke_enabled_by_default=true`,
restore `value_financial_analysis`, restore a 28-agent roster, or route
`sentiment_company_radar` into risk.

## ADR-022: R7-E Expands Developer-Side AI Coding Handoff

Status: accepted for external scaffold developer workflow.

Decision: R7-E expands `AI_CODING_HANDOFF.md` in the fixed DAG external
scaffold package into a full Codex / Claude Code operating manual. The manual
targets developer-side adaptation work: audit an existing agent project,
preserve its business core, add a minimal fixed DAG external service wrapper,
implement `/health`, `/v1/agent/compute`, and `/v1/agent/invoke`, add local
contract tests, run local validation, and return a maintainer handoff bundle.

Reason: external developers may hand this scaffold zip and their own agent
project to coding tools. The tool needs enough instructions to adapt the
developer project without drifting into main-system runtime edits,
`AGENT_TOOLS`, `config/agents`, runtime binding enablement, provider calls, or
live external invocation.

Consequence: the scaffold package and repo mirror now contain a copy-paste
prompt, adaptation patterns, implementation-mode-neutral guidance, test
requirements, validation commands, and final response format for coding agents.

Non-consequence: R7-E does not change service runtime behavior, fixed DAG
topology, the 27-agent roster, runtime bindings, public schemas, frontend
product UI, provider readiness, external `/v1/agent/invoke` readiness, or
production deployment. It does not enable wrappers, set `live_verified=true`,
set `invoke_enabled_by_default=true`, restore `value_financial_analysis`,
restore a 28-agent roster, or route `sentiment_company_radar` into risk.

## ADR-023: R7-F Restores v2.3 Domain Payload Superset

Status: accepted for external scaffold contract coverage.

Decision: R7-F upgrades the external scaffold package to
`external-agent-scaffold-v2.3-fixed-dag`. It restores the v2.3 domain payload
family (`agent_conclusion_v1`, `dimension_conclusion_v1`,
`risk_conclusion_v1`, `macro_conclusion_v1`, `decision_conclusion_v1`,
`eval_record_v1`, `fixed_dag_plan_v1`, and `data_bundle_v1`) and adds
scaffold-local semantic validators while preserving fixed DAG three-id rules,
canonical dimensions, readiness boundaries, and Non-Claims.

Reason: the R7-C/R7-D/R7-E scaffold had the correct fixed DAG handoff shape but
was too thin for L3 composites, L4 decision synthesis, evaluation/replay,
planning, and L1 data bundle handoff. External developers need role-specific
payload contracts before R8 adapter work can safely bridge real services.

Consequence: the repo-external package, repo mirror, package docs, sample
payloads, tests, README, index, payload mapping, readiness ladder, contracts,
system map, quality docs, ADRs, and changelog now describe the same v2.3
compatibility superset.

Non-consequence: R7-F does not change active runtime behavior, fixed DAG
topology, the 27-agent roster, runtime bindings, public schemas, frontend
product UI, provider readiness, external `/v1/agent/invoke` readiness, or
production deployment. It does not enable wrappers, set `live_verified=true`,
set `invoke_enabled_by_default=true`, restore `value_financial_analysis`,
restore a 28-agent roster, or route `sentiment_company_radar` into risk.

## ADR-024: R7-G Patches v2.3.1 External Scaffold Contracts

Status: accepted for external scaffold contract patch.

Decision: R7-G upgrades the external scaffold package to
`external-agent-scaffold-v2.3.1-fixed-dag`. It patches the R7-F v2.3 payload
family by adding L2 `gate_member` semantics, safe L2 `raw_output` and
`quality` dictionaries, `manual_review` risk gates, canonical
`DimensionMember[]` composites, normalized point-in-time date comparison,
macro `dimension_weights` restricted to `value` and `market`, L4 score
tolerance `0.01`, and distinct reasoning-stage validation.

Reason: R7-F restored the right payload family, but review showed that several
contracts were too thin for risk-member L2 agents, risk fusion, value/market
composite recomputation, mixed date formats, and L4 score/trace review.

Consequence: the repo-external package, tracked repo mirror, package docs,
sample payloads, tests, README, index, payload mapping, readiness ladder,
sample docs, contracts, system map, quality docs, ADRs, and changelog now
describe the v2.3.1 contract patch.

Non-consequence: R7-G does not change active runtime behavior, fixed DAG
topology, the 27-agent roster, runtime bindings, public schemas, frontend
product UI, provider readiness, external `/v1/agent/invoke` readiness, or
production deployment. It does not enable wrappers, set `live_verified=true`,
set `invoke_enabled_by_default=true`, restore `value_financial_analysis`,
restore a 28-agent roster, or route `sentiment_company_radar` into risk.

## ADR-025: R7-H Repairs Reset Consistency Drift Without Runtime Change

Status: accepted for minimal consistency repair.

Decision: R7-H aligns frontend workflow fixtures and smoke assertions with the
backend runtime binding `runtime_kind` literals, restores the local
repo-external scaffold distribution working copy from the tracked mirror when
it is missing, and updates current documentation wording around R7-C/R7-D/R7-G
phase boundaries.

Reason: Phase 1 audit found small drift between frontend mock metadata and
backend binding truth, plus documentation that treated
`E:\muti-agent\external_agent_scaffold` as an always-present source package
even when the current filesystem only had the tracked mirror.

Consequence: the frontend fixture now uses backend runtime metadata literals,
the tracked mirror remains the audit truth for scaffold content, and the local
repo-external path is documented as a restored distribution working copy.

Non-consequence: R7-H does not change active runtime behavior, fixed DAG
topology, the 27-agent roster, runtime bindings, public schemas, provider
readiness, external `/v1/agent/invoke` readiness, or production deployment. It
does not enable wrappers, set `live_verified=true`, set
`invoke_enabled_by_default=true`, or register the scaffold into the graph.

## ADR-026: R8-1 Adds Selected Plan Contracts Without Changing Active Runtime

Status: accepted for selected routing contract foundation.

Decision: R8-1 adds `route_intent_v1` and `selected_fixed_dag_plan_v1` to
`src/react_agent/fixed_dag_contracts.py` as additive contracts and validators.
The default graph still uses `build_default_fixed_dag_plan`,
`validate_fixed_dag_plan`, and the full 27-agent `fixed_dag_plan_v1` path.

Reason: controlled dynamic routing needs a safe boundary before any LLM or
semantic planner is connected. The planner should produce intent, not raw DAG
dependencies or runtime binding changes. A later deterministic compiler can
translate that intent into a validator-legal selected plan while preserving
full-DAG fallback.

Consequence: `route_intent_v1` records task type, targets, selected dimensions,
selected agents, per-agent briefs, confidence, clarification/fallback metadata,
and provenance. `selected_fixed_dag_plan_v1` records selected dimensions,
selected agents, omitted dimensions, omitted agents, selected stages/steps/DAG
steps, route intent, and fallback metadata. Validators allow explicit dimension
and agent omission, require `report_generator` for selected plans, require risk
and `decision_synthesizer` for investment-judgment task types, keep
`sentiment_company_radar` market-only, reject `value_financial_analysis`, reject
legacy aNN ids and Star/Chain/Debate/Tree dispatch, and reject provider,
external, runtime binding, and unsafe fallback claims.

Non-consequence: R8-1 does not change active runtime behavior, `graph.py`, the
executor default path, fixed DAG topology, the 27-agent roster, catalog,
runtime bindings, runtime registry, public workflow contracts, frontend UI,
provider/search readiness, external `/v1/agent/invoke` readiness, or production
deployment. It does not add an LLM planner, selected DAG compiler, selected
execution, RouteEval suite, or external adapter.

## ADR-027: R8-2 Compiles Route Intent Into Selected DAG Without Enabling Active Runtime

Status: accepted for deterministic selected compiler foundation.

Decision: R8-2 adds `compile_selected_fixed_dag_plan` to compile valid
`route_intent_v1` objects into dependency-closed `selected_fixed_dag_plan_v1`
plans. It also adds selected executor validation helpers:
`validate_selected_dag_steps` and `topological_batches_for_selected_plan`.

Reason: R8-1 established selected contracts, but selected route intent was not
yet an executable selected DAG shape. The next safe step is deterministic
compilation under system-owned rules: the compiler, not an LLM, adds fixed
L1/evidence seams, selected L2 steps, selected composites, policy-gated
decision synthesis, report output, dependencies, and omission metadata.

Consequence: selected plans can now be compiled and validated as complete
selected sub-DAGs without requiring the full 27-agent DAG. The full
`fixed_dag_plan_v1` validator and active graph default remain the regression
baseline. `route_intent_v1` remains planner intent, and
`selected_fixed_dag_plan_v1` is the compiler output target.

Non-consequence: R8-2 does not change active runtime behavior, `graph.py`,
route planner default behavior, fixed DAG topology, the 27-agent roster,
catalog, runtime bindings, runtime registry, public workflow contracts,
frontend UI, provider/search readiness, external `/v1/agent/invoke` readiness,
or production deployment. It does not add an LLM planner, RouteEval suite,
external adapter, or live selected execution path.

## ADR-028: R8-3 Adds Route Intent Planner Seam Behind Default-Off Boundary

Status: accepted for provider-free planner seam preparation.

Decision: R8-3 adds a route-intent planner seam without changing the active
runtime default. `build_default_route_intent` provides deterministic/mock
`route_intent_v1` output for tests and future feature-flag experiments.
`FIXED_DAG_ROUTE_INTENT_SYSTEM_PROMPT` and `build_route_intent_prompt` define
the future LLM or semantic planner contract. `parse_route_intent_json` and
`normalize_route_intent` normalize raw planner JSON into `route_intent_v1` or a
safe clarification/fallback intent.

Reason: R8-1 and R8-2 created selected routing contracts and deterministic
selected DAG compilation, but route planning still needed a safe seam before
any provider-backed planner could be introduced. The planner must output intent
only; the deterministic compiler remains responsible for executable selected
DAG structure, dependencies, L4 inclusion, omission metadata, and validation.

Consequence: the route-intent prompt and parser reject or fail-soft executable
DAG fields, dependency fields, runtime binding changes, removed ids, legacy
numbered ids, selected sentiment-to-risk misuse, investment intents without
risk, and live invocation claims. Unknown agents can be filtered only when
valid selected agents remain. The full `fixed_dag_plan_v1` default graph path
and full DAG fallback remain the regression baseline.

Non-consequence: R8-3 does not change active runtime behavior, `graph.py`,
route planner default behavior, fixed DAG topology, the 27-agent roster,
catalog, runtime bindings, runtime registry, public workflow contracts,
frontend UI, provider/search readiness, external `/v1/agent/invoke` readiness,
or production deployment. It does not add an active LLM planner, RouteEval
suite, external adapter, live selected execution path, or selected public
workflow projection.

## ADR-029: R8-4 Evaluates Route Intent Selections Before Enabling Active Routing

Status: accepted for provider-free route evaluation baseline.

Decision: R8-4 adds RouteEval as an offline deterministic evaluation seam for
`route_intent_v1`. The evaluator scores task type, targets, selected
dimensions, selected agents, clarification behavior, fallback behavior,
over-selection, and under-selection against a small repo fixture. It does not
evaluate legacy Star/Chain/Debate/Tree modes and does not call providers,
search, external services, or the active graph.

Reason: R8-1 through R8-3 created selected-routing contracts, deterministic
selected compilation, and planner/parser seams, but controlled dynamic routing
still needs a repeatable quality loop before any active selected-routing switch
or provider-backed planner is enabled. Evaluating intent selections first keeps
LLM output away from executable DAG dependencies and preserves the deterministic
compiler boundary.

Consequence: `src/react_agent/route_eval.py` can load JSONL gold cases and
evaluate deterministic/mock planner output or parser-normalizer output with
stable provider-free metrics. The first fixture is intentionally small and is a
baseline only; later RouteEval work should expand the gold set before using
Route F1 as an acceptance threshold.

Non-consequence: R8-4 does not change active runtime behavior, `graph.py`,
route planner default behavior, fixed DAG topology, the 27-agent roster,
catalog, runtime bindings, runtime registry, public workflow contracts,
frontend UI, provider/search readiness, external `/v1/agent/invoke` readiness,
or production deployment. It does not add active selected routing, a live LLM
planner, external adapter readiness, live selected execution, or a final >=80%
Route F1 gate.

## ADR-030: R8-5 Wires Selected Routing Behind A Default-Off Graph Boundary

Status: accepted for default-off graph integration.

Decision: R8-5 wires provider-free selected routing into `route_planner_node`
behind `Context.enable_selected_routing` / `ENABLE_SELECTED_ROUTING=1`. The
default graph path remains the full `fixed_dag_plan_v1`. When explicitly
enabled, the graph builds `route_intent_v1` through the deterministic/mock
planner seam, compiles it into `selected_fixed_dag_plan_v1`, executes it through
selected executor validation, and falls back to the full DAG on compile or
selected validation failure.

Reason: R8-1 through R8-4 established contracts, deterministic compilation,
planner/parser seams, and offline RouteEval. The next safe step is to connect
the selected pipeline under an explicit runtime boundary while keeping the
full DAG default as the regression baseline.

Consequence: selected routing can now be exercised in graph smoke tests without
provider, search, external invocation, runtime binding changes, frontend
changes, or direct LLM-generated DAG dependencies. Selected executions produce
selected step results and selected-subset workflow snapshots. Fallbacks record
public-safe provenance with `selected_routing_requested`,
`selected_routing_fallback`, provider/external false flags, and safe fallback
codes.

Non-consequence: R8-5 does not change default active behavior, fixed DAG
topology, the 27-agent roster, catalog, runtime bindings, runtime registry,
frontend UI, provider/search readiness, external `/v1/agent/invoke` readiness,
or production deployment. It does not add a provider-backed LLM planner,
external adapter readiness, final Route F1 acceptance threshold, or real
business-agent implementation.

## ADR-031: R8-6B Uses Default-Off Internal LLM Placeholders Before External Integration

Status: accepted for default-off L2 placeholder implementation.

Decision: R8-6B adds internal LLM placeholders for fixed-DAG L2 conclusions
behind `Context.enable_internal_llm_placeholders` /
`ENABLE_INTERNAL_LLM_PLACEHOLDERS=1`. The default path remains deterministic.
When explicitly enabled, the executor may call the main-system model to produce
bounded JSON placeholder observations for selected or full L2 slots. Provider
missing, provider configuration errors, parse failures, or unsafe content fall
back to the deterministic pending conclusion.

Reason: server-side business agent directories and processes exist, but they
have not completed fixed-DAG external adapter readiness, live verification, or
runtime binding enablement. The reset runtime needs a bounded way to carry L2
functional slots without claiming those external services are active. Keeping the
placeholder internal, default-off, and L2-only preserves the runtime boundary
while preparing later adapter work.

Consequence: `src/react_agent/fixed_dag_llm_placeholders.py` becomes the active
internal placeholder seam for R8-6B. Successful placeholder conclusions are
`conclusion_object_v1` with `status=partial`, confidence capped at `0.4`, and
`provenance.runtime_path=internal_llm_placeholder`. L3 composites, L4 decision
synthesis, and report generation remain deterministic summaries.

Non-consequence: R8-6B does not enable external `/v1/agent/invoke`, search,
runtime binding changes, `live_verified=true`, `invoke_enabled_by_default=true`,
fixed DAG roster changes, `value_financial_analysis`, sentiment-to-risk routing,
legacy `AGENT_TOOLS`/`config/agents`/aNN authority, frontend rewrite, or
production deployment. Deployed-but-deferred inventory remains documentation
evidence, not runtime authority.

## ADR-032: R8-7B Adds Provider-Free External Payload Adapter Mapping

Status: accepted for pure adapter mapping first slice.

Decision: R8-7B adds `src/react_agent/fixed_dag_external_adapter.py` as a
provider-free, HTTP-free mapping layer from already-available external fixed-DAG
payload dictionaries into current internal contracts. The first supported
families are `agent_conclusion_v1 -> conclusion_object_v1` and
`data_bundle_v1 -> data_bundle_v1`. Unsupported payload families return
controlled adapter failure records or remain future work.

Reason: R8-7A found that the v2.3.1 scaffold payload family is available and
well-tested, but the active main system had no fixed-DAG contract adapter. The
next safe step is pure mapping and safety validation before any health, compute,
invoke, wrapper bridge, executor integration, or runtime binding enablement
work.

Consequence: external L2 direction payloads can be normalized into
validator-legal `conclusion_object_v1`; risk `gate_member` payloads can map only
when the primary id is a current fixed-DAG risk L2 id, with `risk_score`
preserved in provenance; external data bundles can be compressed into the
current narrow internal `DataBundle` shape. Adapter output sets
`provider_invoked=false` and `external_invoked=false` because the mapper itself
performs no live call.

Non-consequence: R8-7B does not call HTTP, providers, `/health`,
`/v1/agent/compute`, `/v1/agent/invoke`, or deployed server agents. It does not
change `graph.py`, `fixed_dag_executor.py`, public API/runtime/mapping modules,
runtime bindings, live flags, the fixed DAG roster, frontend code, L3/L4 active
mapping, external readiness levels, or production deployment. Passing adapter
tests does not imply `live_verified=true` or `invoke_enabled_by_default=true`.

## ADR-033: R8-8C Accepts external_agent_compute_v0 As Adapter Input Only

Status: accepted for compute-envelope adapter compatibility.

Decision: R8-8C treats `external_agent_compute_v0` as a provider-free adapter
input envelope only. When a compute envelope contains a concrete supported L2
`agent_conclusion_v1` `tool_result`, the adapter reuses the existing conclusion
mapper and records the input envelope schema in provenance.

Reason: R8-8B controlled smoke showed `value_ml_valuation` health passing and
`/v1/agent/compute` returning HTTP 200 with an `external_agent_compute_v0`
envelope whose tool result family was `agent_conclusion_v1`. The R8-7B adapter
rejected that outer envelope as unsupported even though the nested payload
family is already in scope.

Consequence: `src/react_agent/fixed_dag_external_adapter.py` can map supported
compute-envelope L2 conclusions without adding HTTP calls, provider calls,
graph/executor integration, runtime binding changes, or live flags. A compute
envelope that declares a tool result schema but lacks a concrete `tool_result`
returns the controlled failure `compute_tool_result_missing`.

Non-consequence: R8-8C does not make `external_agent_compute_v0` graph state,
live readiness evidence, or runtime-binding authority. It does not repair
`financial_data_service`; that service remains blocked on structured JSON
`/health`. `value_ml_valuation` remains deferred until an R8-8D controlled
re-smoke validates the patched adapter boundary. Passing adapter tests does not
imply `live_verified=true` or `invoke_enabled_by_default=true`.

## ADR-034: R8-8E Records Value ML Controlled Compute Evidence Without Runtime Binding Enablement

Status: accepted for controlled readiness evidence logging.

Decision: R8-8E records sanitized controlled health, compute, and adapter
mapping evidence for `value_ml_valuation` after service-side identity
remediation and R8-8D-ID re-smoke. The evidence lives in documentation only and
references repo-external sanitized artifacts.

Reason: R8-8D showed that the service compute response used the external service
id as the primary `agent_id`, which the main-system adapter correctly rejected.
The right remediation is to fix the dev service response identity to emit fixed
DAG `agent_id=value_ml_valuation` and `external_agent_id=valuation_ml`, then
record the controlled smoke evidence without relaxing main-system identity
validation.

Consequence: `value_ml_valuation` now has documented dev-only evidence for
structured health, `/v1/agent/compute`, and provider-free adapter mapping into
`conclusion_object_v1`. The evidence can inform later invoke-readiness and
runtime-binding review.

Non-consequence: R8-8E does not change main-system adapter gates, graph,
executor, public API, public runtime, public mapping, frontend, fixed DAG
roster, or runtime bindings. It does not call `/v1/agent/invoke`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
claim prod readiness, and does not update public transcript content.

## ADR-035: R8-8G Records Additional Controlled Compute Evidence Without Runtime Enablement

Status: accepted for accelerated controlled readiness evidence logging.

Decision: R8-8G records sanitized controlled health, compute, and adapter
mapping evidence for additional dev services that pass the bounded smoke gate.
In this phase, `macro_analysis` passed without service patching, and
`value_traditional_valuation` passed after bounded dev service identity
remediation.

Reason: R8-8D-ID proved the remediation pattern for services that still emit an
external service id as primary `agent_id`. R8-8G applies that pattern only where
needed and keeps the main-system adapter strict: the fixed DAG id remains the
primary `agent_id`, and the external service id remains `external_agent_id`.

Consequence: `macro_analysis` and `value_traditional_valuation` now have
documented dev-only evidence for structured health, `/v1/agent/compute`, and
provider-free adapter mapping into `conclusion_object_v1`. The evidence can
inform later invoke-readiness and runtime-binding review.

Non-consequence: R8-8G does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, or fixed DAG roster. It does not call `/v1/agent/invoke`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
claim prod readiness, and does not update public transcript content.

## ADR-036: R8-8H Expands Controlled Compute Evidence Without Runtime Enablement

Status: accepted for expanded controlled readiness evidence logging.

Decision: R8-8H records sanitized controlled health, compute, and adapter
mapping evidence for an expanded L2 dev-service batch. In this phase,
`value_meta_valuation`, `value_research_synthesis`, and
`market_stock_technical` passed after bounded service-side protocol remediation
where needed.

Reason: R8-8G established a safe service-side remediation pattern for deployed
dev services that were already close to the fixed DAG external payload family
but still emitted service-owned ids or non-canonical dimensions at the adapter
boundary. R8-8H applies that pattern to additional L2 candidates while keeping
the main-system adapter strict: fixed DAG ids remain primary `agent_id`, service
ids remain `external_agent_id`, and adapter-facing dimensions use canonical
English fixed DAG values.

Consequence: the three R8-8H services now have documented dev-only evidence for
structured health, `/v1/agent/compute`, and provider-free adapter mapping into
`conclusion_object_v1`. The evidence can inform later invoke-readiness and
runtime-binding review, but remains documentation-only.

Non-consequence: R8-8H does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, L3/L4 active runtime, or fixed DAG roster. It does not call
`/v1/agent/invoke`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not claim prod readiness, and does not
update public transcript content.

## ADR-037: R8-8I Broadens Controlled Compute Evidence Without Runtime Enablement

Status: accepted for broadened controlled readiness evidence logging.

Decision: R8-8I records sanitized controlled health, compute, and adapter
mapping evidence for `sentiment_company_radar` after bounded service-side
protocol remediation. The evidence is market-only L2 evidence and is recorded
in documentation only.

Reason: the dev `company_radar_agent` service was already close to the fixed DAG
external compute-envelope family but still emitted service-owned identity and
Chinese-domain dimension fields at the adapter boundary. The correct remediation
is service-side: the fixed DAG id becomes primary `agent_id`, the service-owned
id remains `external_agent_id`, and the adapter-facing dimension is canonical
`market`. The main-system adapter identity gate remains strict.

Consequence: `sentiment_company_radar` now has documented dev-only evidence for
structured health, `/v1/agent/compute`, and provider-free adapter mapping into
`conclusion_object_v1` with `market_composite` output routing. The evidence can
inform later invoke-readiness and runtime-binding review.

Non-consequence: R8-8I does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, L3/L4 active runtime, or fixed DAG roster. It does not call
`/v1/agent/invoke`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not claim prod readiness, does not update
public transcript content, and does not create or imply any
`sentiment_company_radar` risk route.

## ADR-038: R8-8I-QA Completes Sentiment Radar Evidence Logging Without Runtime Enablement

Status: accepted for documentation QA completion.

Decision: R8-8I-QA records that the `sentiment_company_radar` controlled
readiness evidence is fully represented in the reset documentation set:
controlled smoke log, readiness ladder, quality boundary, changelog, README, and
decision log. The evidence remains market-only health, compute, and
provider-free adapter mapping evidence.

Reason: R8-8I produced a successful dev-only controlled smoke for
`sentiment_company_radar`, and the follow-up QA pass ensures that the evidence
is not misread as live readiness, runtime binding enablement, risk routing, or
production readiness.

Consequence: downstream R8-8J work can proceed with a clean documentation
baseline for prior market-only evidence. The evidence can inform later
invoke-readiness and runtime-binding review, but it remains documentation-only.

Non-consequence: R8-8I-QA does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, L3/L4 active runtime, or fixed DAG roster. It does not call
`/v1/agent/invoke`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not claim prod readiness, does not update
public transcript content, and does not create or imply any
`sentiment_company_radar` risk route.

## ADR-039: R8-8J Expands Controlled Compute Evidence Without Runtime Enablement

Status: accepted for controlled L1 readiness evidence logging.

Decision: R8-8J records sanitized controlled health, compute, and adapter
mapping evidence for `financial_data_service` after bounded dev service
protocol remediation. The main-system adapter is extended only as a
provider-free pure mapper so `external_agent_compute_v0` envelopes with concrete
`data_bundle_v1` tool results can map to the internal `data_bundle_v1`
contract.

Reason: the earlier R8-8B smoke showed the L1 data service blocked on an
unstructured health boundary. The dev service was close enough for a bounded
service-side wrapper fix: structured health JSON plus a fixed-DAG compute
envelope around data-bundle evidence. The adapter needed a narrow L1
compute-envelope branch, but runtime bindings and active graph behavior remain
separate readiness concerns.

Consequence: `financial_data_service` now has documented dev-only evidence for
structured health, `/v1/agent/compute`, and provider-free adapter mapping into
`data_bundle_v1`. The evidence can inform later invoke-readiness and
runtime-binding review, but remains documentation-only.

Non-consequence: R8-8J does not change runtime bindings, graph, executor, public
API, public runtime, public mapping, frontend, L3/L4 active runtime, or fixed
DAG roster. It does not call `/v1/agent/invoke`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
claim prod readiness, does not update public transcript content, and does not
wire L1 data service output into active graph execution.

## ADR-040: R8-8K Extends Controlled Compute Evidence Without Runtime Enablement

Status: accepted for entity-relation and risk controlled readiness evidence
logging.

Decision: R8-8K records sanitized controlled health, compute, and adapter
mapping evidence for `entity_relation_extractor`, `risk_identification`, and
`risk_compliance_review` after bounded dev service protocol remediation. The
main-system adapter is extended only as a provider-free pure mapper so
`external_agent_compute_v0` envelopes with concrete
`entity_relation_bundle_v1` tool results can map to the internal
`entity_relation_bundle_v1` contract.

Reason: entity relation is an L1 fixed-DAG dependency, while the two risk
services are L2 risk gate-member signals. The deployed dev services were close
to the external compute-envelope family but needed service-side identity,
wrapper, and role/dimension normalization. The correct boundary remains strict:
fixed DAG ids are primary `agent_id` values, service-owned ids remain
`external_agent_id`, risk services emit `agent_conclusion_v1 role=gate_member`,
and L3 `risk_conclusion_v1` remains a separate later integration concern.

Consequence: the three R8-8K services now have documented dev-only evidence for
structured health, `/v1/agent/compute`, and provider-free adapter mapping into
either `entity_relation_bundle_v1` or `conclusion_object_v1`. The evidence can
inform later invoke-readiness and runtime-binding review, but remains
documentation-only.

Non-consequence: R8-8K does not change runtime bindings, graph, executor,
public API, public runtime, public mapping, frontend, L3/L4 active runtime, or
fixed DAG roster. It does not call `/v1/agent/invoke`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
claim prod readiness, does not update public transcript content, and does not
wire L1 entity-relation or risk L2 outputs into active graph execution.

## ADR-041: R8-8L Records Remaining Risk And Market Controlled Compute Evidence Without Runtime Enablement

Status: accepted for remaining risk controlled readiness evidence logging and
market-candidate deferral.

Decision: R8-8L records sanitized controlled health, compute, and adapter
mapping evidence for `risk_financial_fraud` and `risk_crash` after bounded dev
service protocol remediation. The two services remain L2 risk gate-member
signals represented as `agent_conclusion_v1 role=gate_member`, mapped through
the existing provider-free adapter into `conclusion_object_v1`. The market and
macro candidates that did not meet the bounded-remediation criteria remain
deferred.

Reason: the two risk dev services were deployed and listening but emitted
service-owned identities, Chinese risk dimensions, and `role=gate` values at
the adapter boundary. The correct remediation is service-side wrapper
normalization: fixed DAG ids become primary `agent_id` values, service-owned
ids remain `external_agent_id`, risk dimensions are canonical `risk`, and risk
scores are bounded before adapter mapping. This preserves the main-system
adapter identity gate and avoids forcing L3 `risk_conclusion_v1` or unrelated
market/macro payloads into L2 contracts.

Consequence: `risk_financial_fraud` and `risk_crash` now have documented
dev-only evidence for structured health, `/v1/agent/compute`, and
provider-free adapter mapping into `conclusion_object_v1`. The evidence can
inform later invoke-readiness and runtime-binding review, but remains
documentation-only.

Non-consequence: R8-8L does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, L3/L4 active runtime, or fixed DAG roster. It does not call
`/v1/agent/invoke`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not claim prod readiness, does not update
public transcript content, does not route sentiment to risk, and does not wire
any risk L2 output into L3 `risk_composite` or L4 decision runtime.

## ADR-042: R8-8M Extends Remaining L2 Controlled Compute Evidence Without Runtime Enablement

Status: accepted for remaining L2 controlled readiness evidence logging and
deferred-candidate classification.

Decision: R8-8M records sanitized controlled health, compute, and adapter
mapping evidence for `market_capital_flow_chip` after bounded dev service
protocol remediation. The service remains an L2 market direction signal
represented as `agent_conclusion_v1 role=direction`, mapped through the
existing provider-free adapter into `conclusion_object_v1`. Other R8-8M
candidates remain deferred when they emit L3/regulator semantics, have larger
protocol drift, lack a dev listener or compute endpoint, or lack non-stub
service metadata.

Reason: the money-flow service had clear source, a documented dev port, and a
bounded wrapper path into the existing L2 direction payload family. The correct
remediation is service-side identity and dimension normalization: fixed DAG id
`market_capital_flow_chip` is the primary `agent_id`, service-owned id
`money_flow` remains `external_agent_id`, and the adapter-facing dimension is
canonical `market`. Services with macro regulator payloads or broader scaffold
payload drift should not be forced into L2 direction contracts.

Consequence: `market_capital_flow_chip` now has documented dev-only evidence
for structured health, `/v1/agent/compute`, and provider-free adapter mapping
into `conclusion_object_v1`. The evidence can inform later invoke-readiness and
runtime-binding review, but remains documentation-only.

Non-consequence: R8-8M does not change runtime bindings, main-system adapter
identity gates, graph, executor, public API, public runtime, public mapping,
frontend, L3/L4 active runtime, or fixed DAG roster. It does not call
`/v1/agent/invoke`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not claim prod readiness, does not update
public transcript content, and does not wire any market L2 output into L3
`market_composite` or L4 decision runtime.

## ADR-043: R8-8N-DOCS Persists Agent Readiness Matrix Without Runtime Enablement

Status: accepted for readiness documentation persistence.

Decision: R8-8N-DOCS persists the R8-8N read-only audit into
`docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` and
`docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md`. The matrix records the full
27-agent fixed DAG roster, controlled compute evidence, deferred/problem
agents, service patch backfill inventory, and next developer actions. The
prompt catalog gives service owners copy-ready Codex / Claude Code prompts for
service-side backfill, wrapper fixes, semantic deferrals, and future L3/L4
adapter design.

Reason: the R8-8N audit produced operationally useful readiness state, but the
audit phase was intentionally read-only. Persisting the matrix and prompt
catalog in maintained docs gives downstream developers a stable handoff without
changing runtime behavior.

Consequence: developers now have repository-local documentation for which
agents have controlled compute evidence, which remain deferred, and which
service-side protocol patches must be backfilled into service-owned
repositories before invoke audit or runtime binding work.

Non-consequence: R8-8N-DOCS does not call endpoints, does not call providers,
does not call `/v1/agent/invoke`, does not modify runtime bindings, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
change graph, executor, public API, public runtime, public mapping, frontend,
adapter logic, external service code, or fixed DAG roster, and does not prove
production readiness.

## ADR-044: R8-8P Rebaselines Agent Readiness Against Production Endpoints

Status: accepted for production readiness rebaseline.

Decision: R8-8P separates production endpoint evidence from the earlier dev
controlled smoke evidence. The fixed DAG readiness matrix is now production
first: production endpoint discovery, production `/health`, production
`/v1/agent/compute`, and provider-free adapter mapping determine production
endpoint status. Earlier R8-8G/H/I/J/K/L/M dev endpoint evidence is retained only as
historical debugging and backfill input.

Reason: the previous matrix documented useful controlled compute evidence, but
most of that evidence came from dev ports. Production readiness cannot be
inferred from dev endpoints. A production rebaseline is required before any
invoke audit, runtime binding preparation, or live verification review.

Consequence: only services with production health pass, production compute
pass, and production adapter mapping pass can be considered candidates for a
later production invoke audit. Services that passed in dev but fail production
identity, health, compute, or semantic gates must go through production
remediation/backfill and production resmoke.

Non-consequence: R8-8P does not call `/v1/agent/invoke`, does not modify
runtime bindings, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not change graph, executor, public API,
public runtime, public mapping, frontend, fixed DAG roster, adapter logic, or
production service code, and does not enable production default invocation.

## ADR-045: R8-8P-DOCS-QA Turns Production Rebaseline Into Developer Remediation Playbook

Status: accepted for production readiness documentation refinement.

Decision: R8-8P-DOCS-QA deepens
`docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` into a production problem playbook
and rewrites `docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md` as a copy-ready
Chinese remediation prompt catalog. Each failed/deferred production candidate
now has a specific issue, likely cause, owner action, maintainer action,
resmoke boundary, and prompt id. The prompts distinguish dev historical
evidence, production failure, production remediation, redeployment, and
production resmoke.

Reason: R8-8P established the production endpoint baseline, but service owners
need a concrete handoff that tells them exactly what failed and what to fix.
Generic prompt categories were not enough for production backfill work because
identity pairs, production endpoints, payload families, local tests, and
resmoke boundaries differ by agent.

Consequence: downstream developers can hand a specific prompt to Codex /
Claude Code or a service owner for `financial_data_service`,
`entity_relation_extractor`, `sentiment_company_radar`, value/market identity
fixes, `macro_commodity_pricing`, macro semantic decisions, L3/L4 design, and
future invoke-audit preparation. The current production matrix remains based
only on R8-8P production endpoint evidence.

Non-consequence: R8-8P-DOCS-QA does not call endpoints, does not call
providers, does not call `/v1/agent/invoke`, does not modify runtime bindings,
does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not change graph, executor, public API,
public runtime, public mapping, frontend, adapter logic, external service code,
or fixed DAG roster, and does not prove production default invocation
readiness. Dev evidence remains historical/backfill input only.

## ADR-046: R8-10B Maps L3 Composite Payloads Without Enabling Runtime

Status: accepted for provider-free adapter compatibility.

Decision: R8-10B adds pure mappings from L3 external payload families into the
existing internal `dimension_composite_result_v1` contract. Value and market
composites use `dimension_conclusion_v1`; risk composite uses
`risk_conclusion_v1`; macro composite uses `macro_conclusion_v1`. The adapter
accepts these payloads directly or inside `external_agent_compute_v0` /
`external_agent_response_v0` envelopes. Macro `dimension_weights` are restricted
to `value` and `market`; risk remains an independent gate and macro remains a
regulator rather than a direction vote.

Reason: L3 composites need member weights, gate semantics, macro regime, and
bounded provenance that L2 `agent_conclusion_v1` cannot represent. Mapping the
explicit L3 payload families lets service owners backfill correct wrappers and
lets the main system validate sanitized payloads without relaxing L2 identity
or dimension gates.

Consequence: `fixed_dag_external_adapter.py` can now map L3 payload dictionaries
into validator-legal `dimension_composite_result_v1` objects, and unit tests
cover direct plus envelope forms. The deterministic macro placeholder uses the
same value/market-only weight key policy.

Non-consequence: R8-10B does not call endpoints, does not call providers, does
not call `/v1/agent/invoke`, does not modify runtime bindings, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
wire active L3 runtime execution, does not change graph/executor/public
API/frontend behavior, does not modify external services, and does not prove
L3 production readiness.

## ADR-047: R8-10C Sends L3 Services To Protocol Backfill Before Smoke

Status: accepted for L3 service readiness documentation.

Decision: R8-10C records that the four L3 services must complete service-owner
protocol backfill before controlled L3 health/compute smoke. The main-system
adapter already supports L3 payload families from R8-10B, but that local mapper
does not make the services ready. `value_composite` needs a true
`agent_id=value_composite` L3 value wrapper; `market_composite` needs fixed DAG
member id normalization; `risk_composite` needs R8-10B-compatible fixed id,
canonical dimension, flat gate, and risk-only contributing agents; and
`macro_composite` needs fixed id/runbook alignment around `macro_conclusion_v1`.

Reason: smoking a service before its identity and payload family are aligned
would either fail predictably or encourage weakening the adapter gates. The
safer path is to give service owners precise backfill prompts, keep runtime
bindings disabled, and only run controlled L3 smoke after the service-side
wrappers are redeployed.

Consequence: `docs/AGENT_READINESS_MATRIX_FIXED_DAG.md` now includes an L3
service protocol backfill audit table, and
`docs/DEVELOPER_AGENT_FIX_PROMPTS_FIXED_DAG.md` now includes four
service-specific L3 backfill prompts.

Non-consequence: R8-10C does not call endpoints, does not call providers, does
not call `/v1/agent/invoke`, does not modify service code, does not modify
runtime bindings, does not set live flags, does not wire active L3 runtime
execution, and does not create L3 production readiness evidence.

## ADR-048: R8-10D Backfills L3 Service Wrappers Before Controlled Smoke

Status: accepted for bounded L3 service protocol implementation.

Decision: R8-10D applies service-side protocol wrapper patches for the four L3
composites before any controlled endpoint smoke. `value_composite` and
`market_composite` use adapter-facing `dimension_conclusion_v1`; `risk_composite`
uses `risk_conclusion_v1` with a flat gate action; and `macro_composite` uses
`macro_conclusion_v1` with value/market-only `dimension_weights`. The changes
are restricted to service wrapper/schema/test layers and main-repo
documentation.

Reason: R8-10B made the main-system adapter capable of pure L3 mapping, and
R8-10C showed that service payload shape was still the gating issue. Backfilling
the wrappers first avoids weakening adapter identity/dimension gates and gives
R8-10E a meaningful controlled smoke target.

Consequence: the local service directories now contain fixed DAG L3 wrapper
paths and focused tests. A repo-external backup and manifest record the
non-git service changes at
`/tmp/lma-r8-10d-l3-service-backup/20260610T142216Z/service_patch_manifest.json`.
Service owners still need to backfill these changes into source-controlled
service repositories where applicable.

Non-consequence: R8-10D does not call `/health`, does not call
`/v1/agent/compute`, does not call `/v1/agent/invoke`, does not call providers,
does not restart services, does not modify runtime bindings, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
change main-system graph/executor/public API/frontend behavior, does not enable
active L3 runtime execution, and does not prove L3 production readiness.

## ADR-049: R8-10D-SNAPSHOT Uses A Shadow Handoff Repo For L3 Service Patches

Status: accepted for temporary service patch handoff.

Decision: because the formal source repositories for the four L3 composite
services are not available in this environment, R8-10D-SNAPSHOT records the
R8-10D service wrapper patches in a local shadow handoff repository at
`/sdb/dlut/service-shadow-repos/l3-composite-services`. The shadow repository
contains service notes, the R8-10D manifest, and zero-context patch files. It
does not mirror whole production directories.

Reason: committing directly inside `/sdb/dlut/prod/...` would treat deployed
production directories as source-of-truth repositories and risks capturing
runtime state, virtual environments, logs, data, models, or secret-bearing
deployment material. A separate shadow repo gives developers a reviewable
handoff artifact while preserving the long-term requirement that service owners
backfill patches into formal source-controlled repositories.

Consequence: service owners can inspect one local repository to understand the
L3 wrapper changes and apply them to their eventual formal service repos. The
four production service directories also include
`FIXED_DAG_PROTOCOL_BACKFILL.md` notes that point to the backup manifest and
shadow repo.

Non-consequence: R8-10D-SNAPSHOT does not call endpoints, does not restart
services, does not modify runtime bindings, does not set live flags, does not
prove that running services loaded the patched files, and does not create L3
production readiness evidence. Controlled endpoint verification remains
R8-10E.

## ADR-050: R8-10E Records L3 Production Compute Evidence Without Runtime Enablement

Status: accepted for L3 production controlled compute evidence.

Decision: R8-10E performs authorized controlled restart and production
`/health` + `/v1/agent/compute` smoke for the four L3 production services.
`market_composite`, `risk_composite`, and `macro_composite` produced production
compute payloads that mapped through the main-system L3 adapter into
`dimension_composite_result_v1`. `value_composite` failed closed at health
identity validation and did not proceed to compute.

Reason: R8-10B added pure L3 adapter mapping and R8-10D backfilled service
wrappers, but neither phase proved that production processes had loaded the
wrappers. R8-10E provides compute-level production evidence while preserving
the runtime boundary.

Consequence: the readiness matrix and controlled smoke log can list the three
passing L3 services as production compute evidence candidates for later invoke
audit planning. `value_composite` remains a service-side remediation item.

Non-consequence: R8-10E does not call `/v1/agent/invoke`, does not modify
runtime bindings, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not update public transcript content,
does not wire active graph/runtime L3 execution, and does not prove production
default invocation readiness.

## ADR-051: R8-10F Remediates Value Composite Health Identity Before Readiness Evidence

Status: accepted for scoped L3 production service remediation.

Decision: R8-10F fixes the `value_composite` production health identity on
`127.0.0.1:10015`, keeping `agent_id=value_composite`,
`external_agent_id=composite_valuation`, and
`fixed_dag_agent_id=value_composite` in structured
`external_agent_health_v0`. It also preserves the existing fixed DAG L3 compute
wrapper and verifies that production compute maps through the main-system
adapter into `dimension_composite_result_v1`.

Reason: R8-10E showed the value composite production service had loaded enough
wrapper code for L3 compute but still advertised the value-ML sample identity
from `/health`, so the readiness smoke correctly skipped compute fail-closed.
Readiness evidence should only advance after the service advertises the correct
production identity and the compute envelope maps through the existing adapter
without relaxing identity gates.

Consequence: `value_composite` joins the L3 production compute evidence set.
The service wrapper now rejects unintended value members at the protocol layer
by only emitting fixed DAG value L2 member ids.

Non-consequence: R8-10F does not call `/v1/agent/invoke`, does not modify
runtime bindings, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not change main-system adapter gates,
does not update public transcript content, and does not prove production
default invocation readiness.

## ADR-052: R8-8Q Remediates Production Compute Endpoints Without Runtime Enablement

Status: accepted for scoped production L1/L2 remediation and compute evidence.

Decision: R8-8Q applies bounded production service protocol-wrapper
remediations for selected L1/L2 candidates and then re-smokes only production
`GET /health` and `POST /v1/agent/compute`. The phase records new production
compute evidence for `value_traditional_valuation`, `value_ml_valuation`,
`value_meta_valuation`, `value_research_synthesis`,
`market_stock_technical`, `market_capital_flow_chip`,
`sentiment_company_radar`, and `market_ipo_investor_behavior`.

Reason: R8-8P showed that several services had dev evidence but production
wrappers still emitted service ids, legacy ids, Chinese dimension labels, or
missing envelope identity fields. The smallest safe remediation is to fix the
production protocol wrapper and re-run controlled compute smoke without
relaxing main-system adapter gates.

Consequence: the readiness matrix and controlled smoke log can list the eight
remediated L1/L2 services as production compute evidence candidates for later
invoke audit planning. `financial_data_service`, `entity_relation_extractor`,
`market_fund_manager_behavior`, `macro_commodity_pricing`, and semantic-deferred
macro services remain outside the pass set.

Non-consequence: R8-8Q does not call `/v1/agent/invoke`, does not modify
runtime bindings, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not update public transcript content,
does not wire active graph/runtime external execution, and does not prove
production default invocation readiness.

## ADR-053: R8-11B Runs First Controlled Production Invoke Smoke Without Runtime Enablement

Status: accepted for a tiny production invoke evidence allowlist.

Decision: R8-11B audits production `/v1/agent/invoke` source paths and then
runs a controlled invoke smoke for five low-risk services only:
`risk_identification`, `risk_compliance_review`, `risk_crash`,
`risk_financial_fraud`, and `value_research_synthesis`. The smoke uses
production endpoints, no-LLM style request options, sanitized artifacts, and
the existing provider-free fixed-DAG adapter to validate the returned
`tool_result`.

Reason: R8-8Q and R8-10E/F created production health + compute + adapter
mapping evidence, but compute evidence is below L4 invoke evidence in the
readiness ladder. A very small allowlist lets the project validate the invoke
transport and tool-result mapping boundary without enabling runtime bindings
or broad production invocation.

Consequence: the readiness matrix and controlled smoke log can mark the five
services as having controlled production invoke evidence. They may proceed to a
runtime-binding preparation review, but the config remains unchanged until a
separate approved phase owns that work.

Non-consequence: R8-11B does not push, does not modify runtime bindings, does
not set `live_verified=true`, does not set `invoke_enabled_by_default=true`,
does not make the fixed DAG graph call production services by default, does not
update public transcript content, does not weaken adapter identity gates, and
does not prove production business correctness.

## ADR-054: R8-12 Uses Default-Off Compute Bridge For Demo Before Runtime Enablement

Status: accepted for demo-only fixed DAG external compute integration.

Decision: R8-12 adds a default-off bridge that can call allowlisted production
`/v1/agent/compute` endpoints from `execute_fixed_dag_plan` only when an
explicit demo flag and allowlist are both set. Responses must map through the
provider-free fixed-DAG adapter before replacing L2/L3 placeholder outputs.

Reason: the project needs a same-day web demo that shows structured external
agent outputs flowing through the fixed DAG workflow, but runtime binding
enablement and broad production invocation are separate readiness phases. The
smallest safe bridge is demo-only, allowlisted, loopback-only, compute-only,
and fail-soft back to deterministic placeholders.

Consequence: the local API/Web demo can display a Chinese fixed-DAG report with
value, market, risk, and macro summaries sourced from mapped production compute
responses. Tests cover default-off behavior, allowlist enforcement, loopback
and `/invoke` rejection, mapping success, fallback, selected routing
coexistence, and public-safe output.

Non-consequence: R8-12 does not call `/v1/agent/invoke` from the bridge, does
not modify `runtime_bindings.json`, does not set `live_verified=true`, does not
set `invoke_enabled_by_default=true`, does not make external services default
graph dependencies, does not update public transcript content with raw external
responses, and does not prove production business correctness.

## ADR-055: R8-12B Uses SSH Tunnels For Local Demo Access To Remote Agents

Status: accepted for local demo/dev tooling.

Decision: R8-12B documents and scripts a same-port SSH tunnel workflow for
developers who run the main fixed-DAG project locally while the external
production agents remain on the server. The helpers forward only the 16 R8-12
demo allowlist ports from local `127.0.0.1` to remote `127.0.0.1`, use
`ExitOnForwardFailure=yes`, and refuse to proceed when a required local port is
already in use.

Reason: the R8-12 bridge intentionally accepts only loopback production
compute endpoints and an explicit allowlist. SSH local forwarding preserves
that loopback-only boundary for a developer laptop without exposing the
production `100xx` service ports to the public network or introducing a new
remote proxy surface.

Consequence: a developer can clone the repo locally, start the tunnel, run the
local API/Web with the R8-12 demo flags, and see the same external-compute
workflow shape against server-hosted agents. The sample allowlist JSON is
handoff documentation only; the current bridge still uses environment flags
and the built-in same-port demo registry.

Non-consequence: R8-12B does not start an SSH tunnel during validation, does
not call `/health`, `/v1/agent/compute`, or `/v1/agent/invoke`, does not store
SSH passwords or write `.env`, does not modify `runtime_bindings.json`, does
not set `live_verified=true`, does not set `invoke_enabled_by_default=true`,
and does not expose production agent ports on `0.0.0.0`.

## ADR-056: R8-12C Feeds Report Generation From Public-Safe Evidence Bundles

Status: accepted for fixed DAG report generation and workflow projection.

Decision: R8-12C introduces `report_input_bundle_v1` as the bounded input
package for the fixed DAG report generator. The executor builds the bundle from
current L2 conclusions, L3 composite results, risk gate, macro regulator, and
decision context, then passes it to `build_report_result`. The same summaries
are projected into `workflow_snapshot_v2.stepResults` as `agent_evidence` and
`composite_evidence` so the Web workflow details can show what each single
agent and composite agent contributed to the final report.

Reason: the R8-12 demo could already call allowlisted production `/compute`
services and map the results into internal contracts, but the final report did
not explicitly consume or expose the detailed L2/L3 input bundle. A bounded
report input contract makes the report generator's inputs auditable without
turning raw external payloads into public transcript content.

Consequence: report text and workflow details can explain the individual agent
signals, composite members, risk gate, and macro regulator that shaped a fixed
DAG answer. Tests validate default-off behavior, report bundle validation, no
raw leakage, and frontend rendering of the bounded summaries.

Non-consequence: R8-12C does not call production endpoints, does not call
`/v1/agent/invoke`, does not modify `runtime_bindings.json`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, does not
make external services default runtime dependencies, and does not deploy the
main system to `/sdb/dlut/prod/langgraph-my-agent`. Production rollout requires
a separate backup, sync, validation, and restart step for the main-system
service.

## ADR-057: R8-12D Uses Default-Off LLM Synthesis For Final Reports

Status: accepted for explicit demo/runtime flag use.

Decision: R8-12D adds a default-off LLM report synthesis seam. When
`Context.enable_llm_report_synthesis` or `ENABLE_LLM_REPORT_SYNTHESIS=1` is
explicitly set, the main system may load the configured chat model and ask it
to produce a `report_result_v1` from `report_input_bundle_v1`. The synthesizer
does not receive raw external responses or endpoint URLs, and invalid or unsafe
model output fails closed to the template report.

Reason: R8-12C made the report generator's L2/L3 inputs auditable, but the
report remained template-shaped. The target demo and user workflow require the
report generator to understand the single-agent and composite-agent inputs and
write a natural Chinese final report. The safest first step is to give the
model only the bounded public-safe input bundle and keep the feature behind an
explicit flag.

Consequence: an explicit demo can combine the R8-12 external compute bridge
with R8-12D LLM report synthesis so active agent evidence informs the final
natural-language report. Public workflow provenance may show
`providerInvoked=true` when this path actually invokes the configured model.

Version management: the local annotated tag
`r8-12d-llm-report-synthesizer-fallback` anchors the current implementation
state. The tag labels this as a main-system fallback/demo seam before a formal
external `report_generator` service is wired through the fixed DAG
external-agent contract.

Future direction: the formal multi-agent implementation should move primary
report synthesis behind the `report_generator` agent contract:
`report_input_bundle_v1` in, `report_result_v1` out, with controlled compute
evidence before any invoke or runtime-binding phase. The R8-12D synthesizer can
remain as a safe fallback when that external service is unavailable.

Non-consequence: R8-12D does not call external agent `/v1/agent/invoke`, does
not modify `runtime_bindings.json`, does not set `live_verified=true`, does not
set `invoke_enabled_by_default=true`, does not make provider use default, does
not store raw model output, and does not deploy the main system to production.

## ADR-058: R8-13D Packages Sandbox L3 Repairs Before Production Backfill

Status: accepted for R8-13D handoff.

Decision: R8-13D does not directly modify the four production L3 service
directories. Instead, it packages the successful sandbox R8-13C main-system
patch, sanitized E2E trace, and reviewable candidate service patches under
`/tmp/lma-r8-13d-handoff-package/20260612T023822Z`.

Reason: the four L3 composite services need production backfill, but direct
production edits should happen only after a reviewer can inspect the exact
patch, target files, validation plan, and rollback path. A package-first phase
keeps the demonstrated sandbox flow reproducible without turning it into
unreviewed production runtime behavior.

Consequence: service owners and maintainers can review per-service patches for
`value_composite`, `market_composite`, `risk_composite`, and
`macro_composite`. The next phase may apply one patch at a time with
service-local backup, focused validation, controlled restart, and production
`/health` + `/v1/agent/compute` smoke.

Non-consequence: R8-13D does not modify `/sdb/dlut/prod`, does not call
`/v1/agent/invoke`, does not change `runtime_bindings.json`, does not set
`live_verified=true`, does not set `invoke_enabled_by_default=true`, and does
not prove production readiness for the L3 services.

## ADR-059: R8-13E Backfills Production L3 Wrappers Without Runtime Enablement

Status: accepted for controlled production L3 protocol backfill.

Decision: R8-13E applies the reviewed R8-13D service wrapper patches to the
four production L3 composite service directories. The patches add support for
bounded `context.upstream_outputs` so `value_composite`, `market_composite`,
`risk_composite`, and `macro_composite` can synthesize their L3 payloads from
the current run's L2 outputs.

Reason: the sandbox R8-13C trace proved the intended orchestration shape, but
the formal production L3 services still needed the same protocol wrapper
behavior before a production controlled smoke could verify it. Applying only
the protocol wrapper layer keeps the business algorithms and deployment
configuration unchanged.

Consequence: the four L3 production services now pass controlled production
`/health` + `/v1/agent/compute` smoke with adapter mapping. The smoke artifact
root is `/tmp/lma-r8-13e-prod-l3-smoke/20260612T024649Z`.

Non-consequence: R8-13E does not call `/v1/agent/invoke`, does not change
`runtime_bindings.json`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, and does not enable default graph calls to
production external services.

## ADR-060: R8-13F Restores End-to-End Agent Task Trace Without Runtime Enablement

Status: accepted for default-off demo QA.

Decision: R8-13F restores the sandbox-proven main-system trace path in the
reset branch. The executor now builds `agent_task_v1` instructions,
`agent_evidence_bundle_v1`, and report input bundles that expose each agent's
bounded task, inputs, output summary, and evidence quality. The default-off
compute bridge may send bounded current-run L2 `context.upstream_outputs` to
allowlisted L3 production compute endpoints.

Reason: after R8-13E, the four production L3 services could accept upstream
outputs, but the active main-system demo bridge still did not send them. That
meant an end-to-end run could pass protocol checks without proving that L3
composites consumed the current run's L2 evidence. R8-13F fixes that main
system gap and makes the trace auditable from user question to final report.

Consequence: the R8-13F QA run
`/tmp/lma-r8-13f-prod-e2e-llm-report/20260612T030735Z` mapped 17 production
compute agents and produced a natural Chinese report from the configured
report model. The trace also exposed service quality problems, including
`direction_stance_missing` in three value L2 services and placeholder macro
slots.

Non-consequence: R8-13F does not call `/v1/agent/invoke`, does not change
`runtime_bindings.json`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not enable default graph calls to
production services, and does not store raw external responses or provider raw
output in the repository.

## ADR-061: R8-13G Backfills Value L2 Direction Stance Without Runtime Enablement

Status: accepted for controlled production service remediation.

Decision: R8-13G fixes the three production value L2 valuation service wrappers
that returned `normalized.stance` but omitted the top-level
`agent_conclusion_v1.stance` field required by the fixed DAG adapter. The
services now project the already-computed direction and confidence to top-level
`stance` / `confidence` while preserving the existing business payload.

Reason: R8-13F proved the end-to-end trace path but exposed
`direction_stance_missing` for `value_traditional_valuation`,
`value_ml_valuation`, and `value_meta_valuation`. This was a protocol shape
gap, not a valuation-model gap. Fixing it service-side keeps the main adapter
strict and avoids relaxing the fixed DAG identity or direction contract.

Consequence: after service-local validation and controlled restart, all three
value L2 services passed production `/health`, production
`/v1/agent/compute`, and main-system adapter mapping. The R8-13G E2E trace
`/tmp/lma-r8-13g-prod-e2e-llm-report/20260612T033912Z` includes those three
services as usable value-side evidence in the final configured-report run.

Non-consequence: R8-13G does not call `/v1/agent/invoke`, does not change
`runtime_bindings.json`, does not set `live_verified=true`, does not set
`invoke_enabled_by_default=true`, does not enable default graph calls to
production services, and does not change valuation models, feature
engineering, scoring algorithms, data files, or deployment configuration.

## ADR-062: R8-13N Keeps L3 LLM Use Language-Only and Default-Off

Status: accepted for main-system report-material enrichment.

Decision: R8-13N adds a default-off main-system L3 explanation synthesizer
behind `Context.enable_llm_l3_explanation` /
`ENABLE_LLM_L3_EXPLANATION=1`. The seam may read public-safe current-run L2
conclusions and deterministic L3 composite results, then add bounded Chinese
`research_points` and `provenance.llm_explanation` to L3 outputs before
decision/report generation. It must preserve deterministic L3 fusion fields:
`stance`, `confidence`, `status`, `gate`, `veto`, `penalty`, `risk_score`,
`regime`, `risk_sensitivity`, `dimension_weights`, member weights, and
contributing agents.

Reason: final reports need better L3 conflict explanation, but L3 fusion must
remain auditable, deterministic, and contract-valid. Letting an LLM recompute
weights, gates, risk scores, or statuses would make the graph hard to verify
and would blur placeholder/partial evidence boundaries. A language-only layer
lets reports explain available material while keeping the fixed-DAG math and
quality gates owned by deterministic builders or external composite services.

Consequence: when explicitly enabled and successfully invoked, public workflow
`providerInvoked` may be true even if final report synthesis remains on the
fallback path, because the L3 explanation layer used a provider. The execution
provenance separately records `llm_l3_explanation_*` and
`llm_report_synthesis_*` fields so traces can distinguish the two provider
uses. Missing provider credentials, unsafe output, invalid JSON, schema
mismatch, or failed post-application validation keeps the original
deterministic L3 results.

Non-consequence: R8-13N does not call external agent `/v1/agent/invoke`, does
not change `runtime_bindings.json`, does not set `live_verified=true`, does not
set `invoke_enabled_by_default=true`, does not make provider use default, does
not store raw model output, and does not make placeholder agents real evidence.

## ADR-063: R8-13Q Enables L4 Compute-Default Runtime Only

Status: accepted for approved L4 runtime binding phase.

Decision: R8-13Q introduces an explicit `external_compute_default` runtime kind
for L4 services and switches only `decision_synthesizer` and `report_generator`
to production-source `/v1/agent/compute` defaults on ports `10025` and
`10026`. The executor first builds deterministic L4 fallback payloads, then
uses the runtime binding to call the L4 compute service and accepts the result
only after adapter validation. `invoke_enabled_by_default` remains false, and
the runtime registry rejects `/v1/agent/invoke` URLs for this runtime kind.

Reason: the L4 decision/report services now have provider-backed compute
evidence, transcript-safety regression coverage, a rollback plan, and explicit
operator approval to proceed with the runtime phase. A compute-only default
lets the main system treat decision and report as formal L4 agents while still
keeping the higher-risk `/invoke` path and all lower-layer external defaults
out of scope.

Consequence: default fixed-DAG runs may call production-source L4
`/v1/agent/compute` services without enabling the R8-12 demo bridge. Workflow
provenance records this as `external_compute_default_*`, not as public
`external_invoked=true`. `Context.disable_external_compute_default` and
`DISABLE_EXTERNAL_COMPUTE_DEFAULT=1` remain the rollback/test controls for
restoring deterministic L4 behavior.

Non-consequence: R8-13Q does not call `/v1/agent/invoke`, does not modify
`.env`, does not enable any L1/L2/L3 external default, does not turn compute
evidence into invoke evidence, does not claim incomplete upstream agents are
production-complete, and does not expose raw provider output, credentials, raw
graph messages, traceback text, endpoints, or chain-of-thought in public
transcripts.

## ADR-064: P2S Inventory Recursively Covers Registered Source And Support Roots

Status: accepted for SYNC-OPS planner phases.

Decision: P2S planning must recurse through every registered source and support
subroot while preserving the logical service-root relative path. If an Agent
omits `source_subroots`, the logical root is scanned recursively. Inventory
must prune excluded runtime/data/cache/model/log directories before descent and
must not fall back to top-level-only scanning.

Reason: the real P2S baseline contained nested packages, tests, configs, and
runbooks that the initial planner missed. A nonrecursive inventory can produce
a hash-valid but incomplete stage plan.

Consequence: registry rows now distinguish logical root, source subroots,
support subroots, transaction root, and stage prefix. Shared subroots are
modeled as shared transactions instead of duplicate file actions.

Non-consequence: recursive inventory is still source-policy bounded. It does
not copy `.env`, credentials, logs, cache, virtualenvs, models, datasets,
runtime output, or large assets by default.

## ADR-065: Historical Baseline And Current Prod Files Need Explicit Parity Dispositions

Status: accepted for SYNC-OPS P2S automation entry.

Decision: a P2S plan is not eligible for future machine approval unless every
historical baseline manifest row and every current production inventory row has
a terminal disposition. `unresolved` must be zero in both parity ledgers.

Reason: counts alone cannot distinguish legitimate prod deletions, sandbox
metadata, sanitized derivatives, shared subtree compression, runtime-noise
exclusion, or missed source files.

Consequence: SYNC-OPS-1R2 emits `previous_baseline_to_new_plan_parity_v1` and
`current_prod_to_new_plan_coverage_v1` ledgers. These ledgers are review and
validation evidence, not write authority.

Non-consequence: historical file count is not a mechanical copy target. The
planner may record removed, stale, excluded, blocked, shared, or preserved
files when current facts justify that disposition.

## ADR-066: Valid P2S Plans Need Temp Reconstruction Before Machine Approval

Status: accepted for SYNC-OPS P2S automation entry.

Decision: a valid P2S plan must carry an expected stage projection digest and
must be reconstructable in a repo-external `/tmp` tree before any future
approval request is considered actionable.

Reason: schema-valid action lists can still miss nested files, duplicate
destinations, preserve the wrong derivative, or materialize a tree that does
not match the planned digest.

Consequence: the planner can perform a temp-only reconstruction, compare
expected and actual projection digests, run a secret scan, and record bounded
py_compile diagnostics. The real sandbox is not written in SYNC-OPS-1R2.

Non-consequence: temp reconstruction is not P2S stage/activate. It does not
create the versioned sandbox baseline, write the pointer, create backups,
acquire locks, or approve a plan.

## ADR-067: Write Execution Requires Plan Approval And Environment Snapshot

Status: accepted for SYNC-OPS writer phases.

Decision: P2S write execution requires an immutable plan, a file-based machine
approval bound to the exact plan SHA, and an environment snapshot SHA that
matches current non-sensitive execution facts.

Reason: a plan can become stale after approval if prod source, active pointer,
baseline tree, stage path, registry, policy, or catalog hashes drift.

Consequence: stage, activate, and rollback commands refuse to run without
`--plan`, `--approval`, `--execute`, exact hashes, and matching environment
snapshot. Chat approval is never machine approval.

Non-consequence: SYNC-OPS-2A does not create a real approval for the current
server plan.

## ADR-068: P2S Activates Independent Candidates Without Hard Links

Status: accepted for SYNC-OPS writer phases.

Decision: P2S keeps immutable versioned baselines and activates a separate
candidate tree. The active sandbox must not share mutable hard-linked files
with the versioned baseline.

Reason: the versioned baseline is audit evidence and future experiment base
state. Hard links would let later active-tree mutation alter the baseline.

Consequence: activation copies or reflinks safely when available, verifies the
candidate digest, checks hard-link count, archives old active, renames the
candidate into place, and preserves both stage and archive.

Non-consequence: SYNC-OPS-2A validates this only in temp fixtures.

## ADR-069: Runtime Compile Failures Block Unless Proven Legacy

Status: accepted for SYNC-OPS writer phases.

Decision: runtime, startup, contract-test, offline-test, and semantic
placeholder Python compile failures are hard blockers. Proven unreachable legacy
Python may be retained as diagnostic-only evidence with explicit limitations.

Reason: a syntax error in runtime closure means a baseline is not safe to
activate. A non-runtime legacy file should not block all safe source capture
once static reachability is proven.

Consequence: validation profiles classify Python files before stage validation.
The risk crash `skmodels.py` file is treated as an unreachable legacy reference
and reported as diagnostic-only.

Non-consequence: diagnostic-only does not mean the file is production healthy.

## ADR-070: Writer Runs Use Global And Transaction Locks Plus Journal

Status: accepted for SYNC-OPS writer phases.

Decision: every write run uses a global coordinator lock, per-transaction locks,
and an append-only recovery journal outside the target tree.

Reason: P2S and S2P must not concurrently mutate the same target root or switch
active sandbox state while another transaction is mid-flight.

Consequence: stale locks are inspected but not auto-deleted; wrong-owner
release is rejected; recovery reads journal events to classify resume, rollback,
or manual-intervention states.

Non-consequence: SYNC-OPS-2A acquires locks only in `/tmp` tests.

## ADR-071: Stage Activate And Rollback Approval Are Separate

Status: accepted for SYNC-OPS writer phases.

Decision: machine approval grants stage, activate, and rollback independently.
Delete, process action, and live validation remain separately denied by default.

Reason: materializing a stage, switching the active sandbox, and restoring an
archive carry different operational risk.

Consequence: a valid stage approval cannot silently activate; a valid activate
approval cannot silently roll back; rollback approval must be available before
real execution.

Non-consequence: SYNC-OPS-2A does not approve real stage, activate, or rollback.

## ADR-072: P2S Source Selection Is Role Based

Status: accepted for SYNC-OPS P2S execution entry.

Decision: small regular files are not automatically source-bearing. P2S
inventory classifies files by role before planning: source code,
schema/protocol, tests, documentation, runbooks, package metadata, explicit
runtime assets, generated artifacts, experiment results, data/model assets,
backup artifacts, local metadata, runtime noise, sensitive blocked, or unknown
blocked.

Reason: the 2A plan showed that extension-based inclusion admitted generated
results, local tool settings, backup trees, and opaque files as copy actions.

Consequence: source category is part of inventory and copy actions. The plan
validator rejects non-materializable categories in `copy_from_prod`.

Non-consequence: role classification does not prove business correctness or
owner source authority.

## ADR-073: Local Metadata Backups And Generated Results Are Excluded By Default

Status: accepted for SYNC-OPS P2S execution entry.

Decision: `.claude`, `.idea`, `.vscode`, hidden local/cache directories,
backup-pattern directories, `artifacts`, `results`, `reports`, `outputs`, and
`runs` are pruned or excluded by default.

Reason: these paths are local workflow state, deployment residue, experiment
outputs, reports, or runtime artifacts, not portable source baseline input.

Consequence: a future stage plan may be smaller than a historical raw manifest
while still complete, provided excluded files have explicit dispositions.

Non-consequence: explicitly evidenced runtime assets can still be listed in a
manifest and included.

## ADR-074: Runtime Static Assets Require Explicit Evidence

Status: accepted for SYNC-OPS P2S execution entry.

Decision: runtime static assets, test fixtures, and legacy references are
included only when registered in an explicit runtime asset manifest with
agent id, relative path, role, evidence, size, SHA, and secret-scan policy.

Reason: generated-result directories can contain small JSON or CSV files that
look harmless but are not source authority.

Consequence: `config/ops/agent_runtime_asset_manifest.json` is the allowlist
for such exceptions. The current manifest contains the risk-composite
fixed-DAG L3 contract fixtures.

Non-consequence: the manifest cannot whitelist models, production datasets,
raw logs, credentials, or user data.

## ADR-075: Not Scanned Is Never Executable

Status: accepted for SYNC-OPS P2S execution entry.

Decision: a `copy_from_prod` action must never have
`sensitive_classification=not_scanned`. Unknown or opaque files are classified
and excluded or blocked before planning.

Reason: a plan with `not_scanned` copy actions cannot prove that no secret or
runtime noise is being copied.

Consequence: no-extension files are content-sniffed and secret-scanned. Safe
text can be classified as documentation; empty directory markers and opaque
files are excluded with explicit categories.

Non-consequence: this does not output file contents or secret findings.

## ADR-076: Real Write Approval Needs Full-Scale Actual-Plan Rehearsal

Status: accepted for SYNC-OPS P2S execution entry.

Decision: a reduced synthetic writer fixture is not enough for real P2S
approval. The current actual plan must stage, verify, activate, and roll back
successfully in a repo-external temp root before requesting machine approval.

Reason: full-scale rehearsal validates source selection, digest projection,
secret scan, compile profile, no-hardlink activation, rollback, and recovery
against the same action set that would be approved.

Consequence: SYNC-OPS-2A-R1 adds a temp-only `p2s rehearse` path that remaps
stage, active, pointer, archive, approval, locks, and artifact store to `/tmp`.

Non-consequence: temp rehearsal is not real execution and does not create a
real approval, lock, backup, stage, activation, endpoint smoke, or process
action.
