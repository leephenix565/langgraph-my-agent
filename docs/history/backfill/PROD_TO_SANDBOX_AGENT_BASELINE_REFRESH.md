# Production To Sandbox Agent Baseline Refresh

Status: complete with sanitized derivatives.

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

P2S-BASELINE-X initially did not switch the current external-agent sandbox path:

```text
/sdb/dlut/sandbox/r8-13a/services/prod
```

Reason: two production source files contain high-confidence credential-like
assignments and were blocked from exact sandbox copy:

- `value_research_synthesis`
- `macro_index_valuation`

No secret values are recorded in this repository or in the sanitized artifacts.

P2S-CLOSE-R1 resolved that blocker without modifying production. The fixed
sandbox path now points to the refreshed production-derived baseline:

```text
/sdb/dlut/sandbox/r8-13a/services/prod
```

The previous current sandbox tree was preserved at:

```text
/sdb/dlut/sandbox/r8-13a/services/prod-pre-p2s-20260623T060926Z
```

The versioned baseline remains available at:

```text
/sdb/dlut/sandbox/prod-baselines/20260623T050419Z/fixed-dag-services
```

The active pointer is:

```text
/sdb/dlut/sandbox/r8-13a/services/PROD_BASELINE_POINTER.json
```

## Disposition

The 26 formal external agents are covered.

- `refreshed_with_sandbox_experiments_archived`: 14
- `refreshed_from_prod`: 2
- `already_equal_to_prod`: 5
- `semantic_placeholder_snapshot`: 2
- `refreshed_with_sanitized_derivative`: 2
- `refreshed_with_unreachable_sensitive_file_omitted`: 1

The final baseline passed source hash equality for exact-copied files,
explicitly tracked sanitized derivatives for runtime-required sensitive source,
compiled staged Python files using repo-external pycache, and passed a
credential-oriented source scan. No endpoint was called and no process was
started, stopped, restarted, signaled, or killed.

## Sensitive Source Resolution

P2S-CLOSE-R1 classified:

- `value_research_synthesis` `main5.py` as
  `hardcoded_credential_required_runtime`.
- `macro_index_valuation` `config.py` as
  `hardcoded_credential_required_runtime`.

Both were copied into sandbox as sanitized derivatives that replace literal
credential material with explicit environment-variable lookups and empty
defaults. The production files were not modified, and the raw literal values
were not recorded.

One unreachable legacy test file under `financial_data_service` was safely
omitted from the sandbox baseline because it contained token-like literal test
material and was not part of the runtime closure.

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

Future sandbox experiments should use the refreshed current sandbox path as the
baseline. If an experiment changes an external agent, it must still go through
the normal sandbox-to-prod audit path before production adoption. The sanitized
derivatives are sandbox safety controls and do not make production the owner
source authority.
