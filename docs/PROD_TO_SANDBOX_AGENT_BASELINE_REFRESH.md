# Production To Sandbox Agent Baseline Refresh

Status: partial with explicit service blockers.

This record covers the P2S-BASELINE-X production-to-sandbox external agent
baseline refresh. It is a sandbox baseline capture, not backfill, owner-dev
durability, production deployment, runtime activation, endpoint smoke, or
service restart.

## Scope

The main-system development authority remains:

```text
/sdb/dlut/dev/langgraph-my-agent
```

External agent runtime snapshots were taken from production service roots under:

```text
/sdb/dlut/prod/*
```

The main-system sandbox was not refreshed from production. Because the existing
main-system sandbox is not equal to the current dev HEAD, a dev-HEAD based
versioned sandbox baseline was created separately:

```text
/sdb/dlut/sandbox/langgraph-my-agent-baselines/20260623T050419Z/langgraph-my-agent
```

## Results

Artifact root:

```text
/tmp/lma-prod-to-sandbox-agent-refresh-20260623T050419Z
```

Old external-agent sandbox backup:

```text
/sdb/dlut/sandbox/backups/p2s_pre_refresh_20260623T050419Z
```

New staged external-agent baseline:

```text
/sdb/dlut/sandbox/prod-baselines/20260623T050419Z/fixed-dag-services
```

The current external-agent sandbox path was not switched:

```text
/sdb/dlut/sandbox/r8-13a/services/prod
```

Reason: two production source files contain high-confidence credential-like
assignments and were blocked from sandbox copy:

- `value_research_synthesis`
- `macro_index_valuation`

No secret values are recorded in this repository or in the sanitized artifacts.

## Disposition

The 26 formal external agents were covered.

- `refreshed_with_sandbox_experiments_archived`: 15
- `refreshed_from_prod`: 2
- `already_equal_to_prod`: 5
- `semantic_placeholder_snapshot`: 2
- `blocked_secret_or_sensitive_file`: 2

The staged baseline passed source hash equality for unblocked agents and
compiled 815 staged Python files using repo-external pycache. No endpoint was
called and no process was started, stopped, restarted, signaled, or killed.

## Preservation

The previous sandbox source-bearing inventory and sandbox-only differences were
archived under the backup root. These patches are preservation evidence for
future experiment review only. They were not applied on top of the new
production-derived baseline.

## Owner Provenance

Owner-dev provenance was recorded as context only. It is not a condition for
prod-to-sandbox baseline capture and does not make production the owner source
of truth.

The current owner provenance summary is:

- owner source exact: 2
- prod ahead: 9
- divergent: 2
- authority unresolved: 13
- owner ahead: 0

## Non-Claims

- No production file was modified.
- No owner-dev repository was modified.
- No endpoint was called.
- No process action was taken.
- No `.env` value or `/proc/*/environ` was read.
- No secret, raw log, raw response, model weight, or production data bulk asset
  was copied.
- The staged sandbox baseline is not production readiness evidence.
- The staged snapshot does not make production the source authority for external
  agent owner repositories.

## Follow-Up

To complete a current-path switch, service owners must first remove or replace
credential-bearing inline source from the two blocked production roots with
safe configuration references. After that, rerun the same audited snapshot
process and switch only if validation passes.
