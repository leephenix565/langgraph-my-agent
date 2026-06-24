# SYNC-OPS-5A First Nonzero Cycle Qualification

SYNC-OPS-5A qualifies the first real non-zero publish-and-rebase cycle without
executing it. It closes remaining mapping and strict-cycle semantics that 4X
left exposed, then freezes the next machine-approval boundary only when the
current baseline is complete.

## Risk Financial Fraud Mapping

`risk_financial_fraud` cannot be treated as a successful empty inventory. It is
a normal, non-shared, non-placeholder Agent. Its formal id and registry row are
valid, but the current live prod root and the current active/versioned baseline
do not contain the source-bearing tree needed for a first non-zero experiment.

The S2P validator now rejects any non-shared, non-placeholder Agent with
`file_count=0` and no explicit `registered_empty_tree` disposition. This turns
the prior empty digest/noop into a bounded blocker:
`blocked_baseline_source_mapping_missing`.

## Baseline Repair Boundary

When `risk_financial_fraud` is missing from the current P/S/B roots, 5A must not
freeze a first real non-zero cycle. Instead it generates a P2S baseline repair
requirement and an awaiting-machine-approval repair request. The repair must
restore only that Agent's approved source-bearing tree and must not execute in
5A.

## Multi-Transaction Qualification

5A expands the `/tmp` cycle rehearsal from a single demo transaction to:

- at least two independent transactions;
- one owner transaction for `market_composite`;
- one shared member `market_fund_manager_behavior` with
  `independent_apply=false`;
- duplicate target count `0`;
- fake process/live gates;
- P2S stage/activate simulation;
- strict compensation when a later transaction fails.

Strict compensation means that when transaction A has settled and transaction B
fails, B rolls back its partial changes and A is then compensated in reverse
order. P2S does not run after this failure.

## Candidate Selection

5A may select only an existing user-owned sandbox change unit. Synthetic canary
changes, sanitized derivatives, data/model/dependency/deployment changes,
owner-dev-only patches, already-published changes, deletes, and business-core
algorithm changes are not eligible.

If the baseline repair blocker is present, candidate selection is still
recorded as readiness evidence, but no real experiment workspace or non-zero
cycle approval request is generated.

## 5B Entry

R1X update: the 5A baseline repair request is superseded. It was a
baseline-only repair and could not restore the current empty prod root. The next
approval boundary is prod source recovery for `risk_financial_fraud`; only after
that recovery settles can P2S create a complete replacement baseline and the
first real non-zero cycle be regenerated.

SYNC-OPS-5B may proceed only after:

- `risk_financial_fraud` has non-empty compatible prod, active baseline,
  immutable baseline, and experiment descriptors;
- no baseline repair requirement remains;
- the selected candidate still applies cleanly;
- the final cycle plan and approval request are regenerated on the final tool
  version and final current environment.
