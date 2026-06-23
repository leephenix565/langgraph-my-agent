# SYNC-OPS-1R2 Recursive Source Coverage Repair

SYNC-OPS-1R2 repairs the read-only P2S planner after comparing the repaired
plan with the real P2S baseline manifest. It remains a planner-only phase: no
production, sandbox, owner-dev, approval, lock, backup, stage, activate,
rollback, endpoint, or process action is performed.

## Coverage Defect

SYNC-OPS-1R fixed unsafe file-action semantics, but its current P2S rehearsal
still under-covered source trees. The historical P2S baseline manifest had
1625 copied entries, while the repaired plan initially materialized only the
top-level subset for several services. The count itself is not a target:
current production may add or remove files. The defect is that every previous
baseline file and every current safe production source file needs an explicit
terminal disposition.

The repair makes inventory recursive for registered source and support roots.
Traversal prunes excluded directories before descent, does not follow external
symlinks, preserves POSIX relative paths, records executable bits, and keeps
large/model/data/cache/log/runtime output out of source materialization.

## Roots

The static registry now distinguishes:

- `prod.root`: logical service root;
- `prod.source_subroots`: recursive source roots whose relative paths are
  preserved under the logical root;
- `prod.support_subroots`: auxiliary roots for shared or non-entrypoint
  material;
- `sync.transaction_root`: transaction and conflict boundary;
- `sandbox.stage_prefix`: target prefix in a future versioned baseline.

If `source_subroots` is absent, the planner scans the logical root
recursively. It must not fall back to a top-level-only inventory.

## Parity Ledgers

The planner adds two read-only ledgers:

- `previous_baseline_to_new_plan_parity_v1` gives every historical P2S
  manifest row exactly one disposition.
- `current_prod_to_new_plan_coverage_v1` gives every current production
  inventory row exactly one disposition.

The allowed dispositions include current prod materialization, preserved
sanitized derivative, preserved baseline metadata, omitted sensitive legacy
file, backup/runtime/data/model exclusion, removed current-prod file,
stale sandbox-only file, shared transaction materialization, blocked sensitive
source, and unresolved. `unresolved` must be zero before P2S automation can
request machine approval.

## Stage Projection

P2S plans now carry an `expected_stage_projection_digest`. The digest is based
on planned stage-relative paths, operation type, expected file hash, executable
bit, file type, and safe symlink target. It does not include absolute stage
paths, mtimes, uid/gid, PIDs, listeners, or other transient runtime facts.

A temp-only materializer can reconstruct the planned safe tree under `/tmp`,
compare the actual temp digest with the expected projection digest, run a
secret scan, and run bounded py_compile diagnostics. This proves the plan is
complete without writing the real sandbox.

## Repaired Cases

The three previously misclassified no-source agents now have recursive source
coverage:

- `financial_data_service`
- `entity_relation_extractor`
- `sentiment_company_radar`

Nested packages under services such as `risk_crash`,
`market_stock_technical`, `market_capital_flow_chip`, `macro_analysis`, and
`macro_commodity_pricing` are included or explicitly excluded by policy.
`market_fund_manager_behavior` remains a shared transaction member of
`market_composite`; its file rows are resolved through the shared materialized
subtree rather than duplicate actions.

## Approval

The SYNC-OPS-1R approval request is superseded because it was based on
incomplete source coverage. A new approval request may be emitted only when:

- the new plan validates;
- historical parity unresolved count is zero;
- current production coverage unresolved count is zero;
- coverage ratio is 1.0;
- temp reconstruction digest matches;
- duplicate destination count is zero;
- secret scan passes.

The request is still not an approval record. SYNC-OPS-2A implements the
hash-bound machine approval artifact and temp-root writer contract, but the
1R2 request itself remains superseded by the 2A writer-contract plan.

## SYNC-OPS-2 Entry Conditions

SYNC-OPS-2B may execute P2S automation only after the 2A writer state is
accepted and after an operator supplies a real approval artifact for a fresh
2A plan with matching environment snapshot SHA. The real artifact store,
locks, stage creation, activation, and rollback are still not executed in
SYNC-OPS-1R2.

## Non-Claims

This phase does not modify production, sandbox, owner-dev repositories,
baseline pointers, external Agent services, runtime bindings, live flags,
databases, models, data assets, service processes, endpoints, or the configured
artifact store. It does not create approvals, locks, backups, stages, or
rollback state.
