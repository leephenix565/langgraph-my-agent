# Historical Documentation

This directory stores phase records, closeouts, evidence ledgers, and handoff
records that are no longer current authority.

Current authority starts at:

1. `../../README.md`
2. `../../AGENTS.md`
3. `../INDEX.md`
4. `../CURRENT_STATUS.md`
5. `../FRONTEND_V2.md`
6. `../ARCHITECTURE_FIXED_DAG.md`
7. `../CONTRACTS.md`
8. `../QUALITY.md`

Historical documents are retained for audit, rollback, artifact, backup, and
owner handoff traceability. Do not treat a historical phase record as current
runtime authority unless a current document explicitly incorporates that claim.

Subdirectories:

- `backfill/` - backfill and prod-to-sandbox refresh records.
- `cs1/` - CS1 convergence and durability records.
- `misc/` - readiness, roadmap, handoff, and sample payload records.
- `r8/` - R8 phase evidence and backfill handoff records.
- `releases/` - post-backfill release records.
- `sync-ops/` - bidirectional sync workflow phase records and closeouts.

`MANIFEST.json` maps every moved historical document from its original path to
its retained historical path and records content hashes plus critical reference
classes.
