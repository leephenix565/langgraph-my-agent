# Quality

This document defines the safe validation boundary for the fixed-DAG reset
branch after Phase R6-B.

## Default Reset Mainline

R6-B rebuilds `scripts/quality/run_quality.py --mode mainline` as the default
fixed-DAG reset quality gate. The mainline runs:

1. `static`
2. `unit`
3. `public-api`
4. `graph-smoke`
5. `frontend`

It does not run fusion-gate, provider live smoke, external
`/v1/agent/invoke`, demo stack commands, Router-SFT, RARP/route-prior, or
browser screenshot capture.

## Quality Runner Modes

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode unit
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode public-api
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode graph-smoke
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode frontend
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
```

`static` is intentionally scoped to active reset source, reset tests, quality
scripts, and maintained docs. It is not a full-tree legacy/offline lint gate.

`frontend` runs:

```powershell
npm --prefix apps/web exec -- tsc --noEmit --project apps/web/tsconfig.json
npm --prefix apps/web run test
npm --prefix apps/web run build -- --outDir <repo-external-temp-dir>
```

The runner creates a temporary repo-external frontend build directory and
cleans it up after the build. It must not write `apps/web/dist`.

## Manual, Live, And Archived Gates

These checks are not default reset mainline gates:

- `fusion-gate`: archived/manual deterministic regression lineage only.
- provider live smoke: optional live/manual or scheduled workflow only.
- external `/v1/agent/invoke`: manual/live readiness work only.
- demo stack start/stop: manual demo/deployment acceptance only.
- Router-SFT and RARP/route-prior: archived lineage only.
- browser screenshot visual capture: manual frontend visual acceptance only.

## Validation Meaning

Passing the R6-B reset mainline means the maintained static surface passes,
unit tests pass, public adapter integration tests pass, the runtime graph smoke
test passes, and the frontend typecheck/smoke/repo-external build gate passes.

It does not mean:

- provider readiness
- external service readiness
- live market-data correctness
- real business-agent correctness
- fusion acceptance restored
- visual screenshot acceptance
- production deployment readiness
- full-tree lint enforcement

The fixed-DAG runtime remains the deterministic provider-free reset skeleton
until later phases implement and verify real business agents and live external
service readiness.

## R7-B External Handoff Docs

R7-B external developer handoff work is docs-only. Its validation uses:

```powershell
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode mainline
git diff --check
```

These commands can confirm that the maintained reset quality surface still
passes after docs updates. They do not call providers, do not call external
`/v1/agent/invoke`, do not start the demo stack, do not run fusion-gate, and do
not prove that any external service is live verified or safe to enable.
