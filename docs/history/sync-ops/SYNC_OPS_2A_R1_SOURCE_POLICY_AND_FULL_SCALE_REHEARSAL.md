# SYNC-OPS-2A-R1 Source Policy And Full-Scale Rehearsal

SYNC-OPS-2A-R1 closes the P2S source-selection gap found after the 2A writer
contract. It keeps all real prod, sandbox, owner-dev, approval, lock, backup,
stage, activation, endpoint, and process state untouched.

## Source Selection

P2S selection is role-based. Small regular files are not automatically
source-bearing. Every file receives exactly one category:

- materialized by default: source code, schema/protocol, contract/offline
  tests, documentation, startup runbooks, and package metadata;
- materialized only by explicit manifest: runtime static assets, test
  fixtures, and legacy references;
- excluded by default: generated artifacts, experiment results, data assets,
  model assets, backup artifacts, editor/local metadata, runtime noise,
  sensitive blocked files, and unknown blocked files.

`not_scanned` is never executable. A `copy_from_prod` action must carry a safe
source category and a completed sensitive classification.

## Default Exclusions

The inventory prunes hidden/local/editor and generated directories before
descent, including `.claude`, `.idea`, `.vscode`, `.history`, `.cache`,
`artifacts`, `results`, `reports`, `outputs`, `runs`, logs, temp/cache paths,
model/data paths, and backup patterns such as `.opt_bak_*`,
`.snapshot_bak_*`, `_backup_*`, and `*_predeploy_*`.

Generated reports, experiment outputs, and data/model files may be retained as
audit evidence only through explicit disposition. They are not copied into a
new sandbox baseline by default.

## Runtime Asset Manifest

`config/ops/agent_runtime_asset_manifest.json` is the explicit allowlist for
small runtime static assets or test fixtures that live under otherwise
excluded roles. It records agent id, relative path, role, evidence, size, and
SHA. The current manifest includes only the fixed-DAG L3 risk-composite
contract fixtures with explicit offline-test evidence.

## Unknown Files

No-extension and unusual files are sniffed and secret-scanned before
classification. Current special cases are classified as:

- `financial_data_service/pg-ops-agent/2`: safe extensionless documentation;
- `risk_composite/指令`: safe extensionless documentation;
- `market_stock_technical/multitask_dl/artifacts/.gitkeep`: empty generated
  directory marker, excluded.

## Full-Scale Rehearsal

The current real P2S plan is rehearsed at full scale in `/tmp`, not as a
reduced 26-file fixture. The rehearsal remaps the real plan's stage, active,
archive, pointer, approval, lock, and artifact roots to a repo-external temp
tree, then runs:

1. stage;
2. verify;
3. active-candidate build;
4. activate;
5. rollback;
6. recovery inspection.

The real prod tree is read-only source input. The real sandbox, pointer,
artifact store, approval, locks, and processes are not modified.

## Superseded Entry Note

SYNC-OPS-2A-R2 supersedes the R1 plan/request for execution approval because
the executable plan contract and staged approval boundary are now explicit.
The R1 source policy remains active, but real execution starts with
SYNC-OPS-2B1 stage/verify approval rather than a combined
stage/activate/rollback approval.

SYNC-OPS-2B1 can request real stage execution approval only if a fresh R2 plan
has:

- `not_scanned copy=0`;
- `unknown_blocked=0`;
- `sensitive copy=0`;
- no hidden/local/backup/generated copy actions;
- full coverage ratio `1.0`;
- full-scale temp stage/verify/stage-only-activate-reject/activate/rollback
  pass;
- expected and actual projection digests equal;
- hardlink count `0`;
- a stage-only approval request with `status=awaiting_machine_approval`.

## Non-Claims

This phase does not create real approval, real lock, real backup, real stage,
real activation, endpoint smoke, process action, provider call, database
access, or production deployment evidence.
