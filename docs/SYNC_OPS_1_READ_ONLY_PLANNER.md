# SYNC-OPS-1 Read-Only Bidirectional Agent Sync Planner

SYNC-OPS-1 implements the first read-only slice of the external Agent sync
control plane frozen in SYNC-OPS-0. It can inspect inventories, validate
manifests, compute B/S/P/D diffs, and generate immutable P2S, S2P, and
publish-and-rebase cycle plans. It cannot apply, stage, activate, lock, back up,
restart, smoke, or roll back anything.

## Frozen Decisions

- Artifact store root: `/sdb/dlut/ops-artifacts/agent-sync`.
- This phase records that root only; it does not create or write it.
- Approval mode: file-based JSON approval bound to an exact plan SHA256.
- Chat text such as `ok`, `继续`, or `apply` is not machine approval.
- Lock strategy: global cycle coordinator lock plus per-Agent transaction lock.
- This phase defines lock contracts only and never acquires a lock.
- Shared processes are represented by `registry.service_units` and process
  group keys for future restart de-duplication.
- Owner authority metadata is recorded in the main-system ops registry as
  candidate roots, status, and evidence. It does not replace owner repo
  acceptance.
- Partial-success publish-and-rebase must explicitly set
  `publish_and_rebase_approved=true` and list included, blocked, and rolled
  back Agents.
- Delete operations are disabled by default.
- Sanitized sandbox derivatives are non-publishable by default.
- MVP artifacts are retained; no automatic deletion is implemented.
- Future release bundles should be per-Agent portable bundles containing plan,
  result, patch, tests, rollback, and hashes.

## Static Registry And Runtime Inventory

`config/ops/agent_service_registry.json` is the source-controlled sync registry.
It contains stable identity, path, contract, owner, and sync policy metadata for
the 26 formal external Agents. It deliberately excludes PID, listener state,
process start time, elapsed time, raw command lines, health responses, compute
responses, and environment values.

`RuntimeInventorySnapshot` is generated on demand by the CLI. It may record
root existence, tree digests, included/excluded counts, file classifications,
and optional bounded process diagnostics in later phases. Planner validity does
not depend on transient PID or listener state.

The registry validator checks:

- exactly 26 formal external ids, excluding `route_planner`;
- exact catalog id equality;
- layer, dimension, and routes alignment;
- `sentiment_company_radar` routes only to `market_composite`;
- allowed root namespaces;
- shared service-unit metadata;
- transaction roots and process group keys;
- external id, port, and output contract metadata.

Owner authority unresolved, semantic placeholders, sanitized derivatives, shared
support roots, and stale historical artifacts are review warnings. Duplicate
formal ids, catalog mismatches, sentiment-to-risk routing, unsafe root escape,
and duplicate target actions without a declared shared service unit are fatal.

## B/S/P/D Model

The planner compares four sources:

- `B`: immutable versioned production-derived sandbox baseline;
- `S`: sandbox experiment workspace forked from `B`;
- `P`: current production runtime root;
- `D`: owner-dev candidate or authority root.

The diff key is:

```text
agent_id + unit_kind + normalized POSIX relative_path
```

Absolute paths are never used as identity. Tree digests use sorted normalized
relative path, file type, file SHA256, executable bit, and safe symlink target.
They do not use mtime, uid/gid, inode, or absolute root.

The active fixed sandbox baseline at
`/sdb/dlut/sandbox/r8-13a/services/prod` is immutable for sync purposes. It is
not a valid experiment workspace. An S2P plan whose workspace is the active
baseline returns `blocked_active_baseline_not_experiment`.

## Sensitive And Sanitized Sources

The inventory scanner excludes `.env`, runtime noise, logs, caches, virtualenvs,
model/data assets, special files, unsafe symlinks, path traversal, setuid/setgid
files, and files above the default large-asset threshold. Secret scanning records
only classification and safe line ranges, never matched text, entropy strings,
credential hashes, or environment values.

P2S-CLOSE-R1 introduced sandbox-only sanitized derivatives for
`value_research_synthesis` and `macro_index_valuation`. SYNC-OPS-1 preserves
that state in the registry and blocks direct S2P publish of such files unless a
future explicit prod-safe config-refactor change unit and approval record
exists.

## Plan Types

P2S plans describe a future production-to-sandbox baseline refresh. They include
source inventory, include/exclude decisions, sensitive blockers, large asset
references, old sandbox archive preconditions, staged digest expectations,
validation commands, switch preconditions, rollback skeleton, and approval
requirements. They do not create staging directories or switch pointers.

S2P plans require an experiment manifest. They include B/S/P/D inventory refs,
change units, per-file deltas, target-before hashes, add/replace/delete/omit/
sanitize/noop actions, blockers, backup plan skeleton, offline test plan,
process preflight requirements, live validation requirements, rollback skeleton,
and approval scope. They never modify production.

Cycle plans wrap an immutable S2P plan and defer P2S rebase. The P2S plan is
generated only after all started S2P transactions reach a settled real
production state. Rollback failure blocks rebase.

## Canonical Hash

Plans use canonical JSON:

```python
json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
```

The top-level `canonical_sha256` field is excluded from its own hash. Paths use
POSIX `/`, strings are normalized to NFC, mapping keys must be strings, and list
order is semantically meaningful. Target drift after planning invalidates a
future approval; callers must not update hashes under an old approval.

## CLI

Two read-only entry points are available:

```bash
.venv/bin/python -m react_agent.ops.agent_syncctl <command>
.venv/bin/python scripts/ops/agent_syncctl.py <command>
```

Implemented commands:

- `agent-sync inventory`
- `agent-sync baseline show`
- `agent-sync experiment init`
- `agent-sync experiment validate`
- `agent-sync p2s plan`
- `agent-sync s2p plan`
- `agent-sync cycle plan`
- `agent-sync plan show`
- `agent-sync plan validate`
- `agent-sync plan diff`
- `agent-sync status`
- `agent-sync schema validate`
- `agent-sync lock show`

Unsupported write commands return exit code `2` with
`command_not_available_in_sync_ops_1`:

- `p2s stage`, `p2s activate`, `p2s rollback`
- `s2p apply`, `s2p smoke`, `s2p rollback`
- `cycle publish-and-rebase`
- `lock force-release`

CLI output defaults to a human summary. `--json-output <path>` writes JSON to an
explicit path. `--stdout-json` writes machine JSON to stdout. The planner does
not write current directories by default.

## Exit Codes

- `0`: success
- `2`: invalid arguments, schema failure, or unsupported command
- `3`: plan blocked
- `5`: target drift
- `7`: validation failure
- `11`: partial/read-only plan with blockers

Other write/apply/smoke/rollback codes are reserved for later phases.

## Quality Boundary

SYNC-OPS-1 uses real JSON Schema Draft 2020-12 validation through
`jsonschema.Draft202012Validator`, followed by semantic validators. If the
validator is unavailable, the CLI exits with `schema_validator_unavailable` and
does not mark a plan valid.

Mainline remains provider-free, external-HTTP-free, process-action-free, and
environment-value-free. Tests use repo-external temporary roots for B/S/P/D
integration coverage.

## SYNC-OPS-2 Entry Conditions

SYNC-OPS-2 may start only after:

- planner registry, policy, schema, hash, inventory, diff, and plan tests pass;
- operator confirms the durable artifact-store root can be created;
- write-phase lock and approval records are reviewed;
- P2S automation has explicit permission to archive, stage, activate, and
  rollback sandbox paths;
- no write path is allowed without a hash-bound approval artifact.

## Non-Claims

This phase does not modify production, sandbox, owner-dev repositories, baseline
pointers, external Agent services, runtime bindings, live flags, databases,
models, data assets, service processes, or endpoints. It does not acquire locks,
create backups, apply patches, run smoke tests, or claim owner-dev durability.

