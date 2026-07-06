# Repository Consolidation Closeout

This document is the final closeout record for the Repository Authority &
Active-Core Consolidation theme on the `frontend-ui-refinements` branch.

## Scope

This theme covered:

- documentation authority consolidation;
- active-core package boundary extraction;
- Context and State compatibility metadata;
- proven dead-code retirement audit.

This theme did not cover:

- external agent service implementation;
- production or sandbox runtime deployment;
- runtime binding changes;
- provider or live endpoint readiness;
- business algorithm changes;
- report-quality product work.

## Timeline

- M0: read-only repository authority audit and behavior freeze.
- M1A: quality baseline closure and documentation consolidation plan.
- M1: documentation authority consolidation implementation.
- M2A: active-core extraction plan and import-boundary freeze.
- M2B: Fixed-DAG contract foundations extracted behind the old facade.
- M2C: Fixed-DAG executor foundations extracted behind the old facade.
- M2D: external bridge and runtime registry boundaries split behind old facades.
- M2E: executor runner boundary completed behind the old facade.
- M3A: Context/State compatibility isolation plan.
- M3B: Context/State compatibility metadata helper added without shape change.
- M4A: proven dead-code retirement audit found no P4 deletion candidates.
- FINAL: current documentation records the theme closeout.

## Final Repository State

- Branch: `frontend-ui-refinements`.
- Pre-FINAL closeout HEAD: `64754de8d52977b4b62c50116bf8d623aac861fb`.
- Final closeout commit: the commit containing this document,
  `docs(repo): close repository consolidation theme`.
- Current authority docs start from `README.md`, `AGENTS.md`,
  `docs/INDEX.md`, and `docs/CURRENT_STATUS.md`.
- Historical phase records remain under `docs/history/` and are indexed by
  `docs/history/MANIFEST.json`.
- Fixed-DAG package boundaries now exist under:
  - `src/react_agent/fixed_dag/`;
  - `src/react_agent/fixed_dag/execution/`;
  - `src/react_agent/fixed_dag/external/`;
  - `src/react_agent/fixed_dag/runtime/`.
- Context/State compatibility metadata lives in
  `src/react_agent/compat/context_state.py`.
- Compatibility facades remain retained:
  - `react_agent.fixed_dag_contracts`;
  - `react_agent.fixed_dag_executor`;
  - `react_agent.fixed_dag_external_compute_bridge`;
  - `react_agent.fixed_dag_runtime_registry`.
- M4A found no P4 deletion candidates.

## Key Technical Outcomes

- Current authority docs are separated from historical evidence.
- `react_agent.fixed_dag_contracts` remains the contract compatibility facade.
- `react_agent.fixed_dag_executor` remains the executor compatibility facade.
- `react_agent.fixed_dag_external_compute_bridge` remains the bridge
  compatibility facade.
- `react_agent.fixed_dag_runtime_registry` remains the runtime registry
  compatibility facade.
- `src/react_agent/fixed_dag/` owns foundational contract constants, types,
  labels, and safety helpers.
- `src/react_agent/fixed_dag/execution/` owns execution constants, topology,
  validation, step-result helpers, and the runner.
- `src/react_agent/fixed_dag/external/` owns external compute bridge internals.
- `src/react_agent/fixed_dag/runtime/` owns runtime binding internals.
- `src/react_agent/compat/context_state.py` makes active/compat/legacy/manual
  Context and State field groups machine-checkable.

## Dead-Code Decision

M4A found:

- P0/P1/P2/P3/P4 counts: `10 / 17 / 0 / 0 / 0`;
- P4 count: `0`;
- deletion candidate count: `0`;
- facade delete-now count: `0`;
- Context/State deletion candidate count: `0`.

Because P4 count is zero, M4B deletion implementation is skipped. P0 and P1
observations are not deletable. Compatibility facades remain retained. Future
deletion requires a new P4 evidence audit, exact rollback, behavior freeze
comparison, and passing static/mainline quality.

## Behavior Invariants

The consolidation closeout does not change:

- fixed-DAG catalog;
- runtime bindings;
- public schema;
- graph topology;
- workflow snapshot;
- sync CLI;
- Context/State runtime shape;
- external compute demo/default behavior.

M4A and FINAL do not perform endpoint calls, process actions, provider calls,
production writes, sandbox writes, owner-dev writes, or artifact-store writes.

## Current Maintenance Guidance

- New internal code should import from the new `react_agent.fixed_dag.*`
  packages where appropriate.
- Old facades remain supported compatibility surfaces.
- Do not remove facades without a dedicated deprecation and removal plan.
- Do not delete P0 or P1 candidates.
- Keep Context/State compatibility fields until explicit P4 retirement.
- Treat docs history as evidence, not current runtime/config authority.

## Next Engineering Themes

Possible future themes, not started by this closeout:

- report-quality product work;
- frontend workflow inspector polish;
- real agent data readiness;
- owner-dev durability;
- non-L4 runtime activation;
- service owner source closure.

## Non-Claims

This closeout does not claim:

- runtime behavior change;
- production deployment;
- runtime binding change;
- live endpoint validation;
- provider validation;
- code deletion;
- compatibility deletion;
- public contract change.
