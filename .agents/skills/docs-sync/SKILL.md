# docs-sync

## Use When

- A change modifies frontend behavior, repo boundaries, runtime semantics, or collaboration rules
- New files add public-facing capabilities that need discovery in repo docs
- A mock-first surface becomes a live integration surface

## Boundaries

- Keep changelog scope boundaries explicit.
- Keep operational truth in `docs/SYSTEM_MAP.md`.
- Keep narrative summary in `docs/PROJECT_OVERVIEW.md`.
- Do not describe sync-only live integration as streaming.
- Do not describe replay continuity as equivalent to persistent graph continuity.
- Keep `/api/health` readiness semantics and sanitized error-contract language aligned with the actual adapter surface.

## Expected Outputs

- Updated authority docs and changelog
- Phase-position language that matches the actual repo state
- Clear distinction between mock shell, public adapter, and runtime truth
- Clear distinction between unavailable, degraded, and request-error states on the public surface
