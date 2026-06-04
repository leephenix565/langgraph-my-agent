# Changelog

Historical changelog entries before this reset branch are preserved by tag `pre-fixed-dag-reset-20260604-1457`.

## 2026-06-04 - Phase R1-A hard slimming reset baseline

### Removed

- Removed old Agent Catalog v2 documentation and replacement runbooks.
- Removed old mainline audit, A01 contract/SFT, route-prior/RARP, Router-SFT, external integration, archive, and handoff docs.
- Removed archive tests for route-prior, router eval, and A01 SFT.
- Removed route-prior helper source and its offline regression bundle.
- Removed Router-SFT data, A01 SFT data, Router-SFT tools, old router regression scripts, and SFT train/eval requirements.
- Removed old external-agent scaffold package and generated zip.

### Added

- Added reset documentation set:
  - `docs/ARCHITECTURE_FIXED_DAG.md`
  - `docs/CONTRACTS.md`
  - `docs/FRONTEND_V2.md`
  - `docs/QUALITY.md`
  - `docs/DECISIONS.md`
- Added reset-focused docs test coverage.

### Changed

- Rewrote `README.md`, `AGENTS.md`, `docs/INDEX.md`, and `docs/SYSTEM_MAP.md` for the reset branch.
- Updated static quality documentation targets so they no longer reference deleted docs.

### Not Done

- No runtime graph rewrite.
- No prompt/parser/state/public workflow deletion.
- No Fair Fusion or baseline sidecar deletion.
- No frontend v2 rewrite.
- No provider or external live verification.
- No push.
