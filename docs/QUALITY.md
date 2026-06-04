# Quality

This document defines safe validation for the reset branch.

## Safe R1-A Commands

```powershell
git status --short --branch
git diff --name-status
git diff --check
conda run --no-capture-output -n cline_env python -m ruff check src/react_agent tests scripts/quality
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_public_api.py
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/test_graph.py
conda run --no-capture-output -n cline_env python scripts/quality/run_quality.py --mode static
```

## Not Safe For R1-A

Do not run during R1-A unless the user explicitly asks:

- provider live smoke
- external `/v1/agent/invoke`
- demo stack start or stop
- artifact-writing mainline gates
- artifact-writing fusion gates
- frontend production build if it writes repo artifacts

## Current Quality Runner Boundary

`scripts/quality/run_quality.py --mode static` checks maintained reset docs and selected static code surfaces. Old Router-SFT docs are no longer quality targets.

The previous mainline and fusion-gate modes still exist in code but are not reset acceptance evidence. They must be rebuilt in later phases before being used as Fixed DAG gate claims.

## Validation Meaning

Passing safe commands means the reset cleanup did not break the checked static/unit/public/graph surfaces. It does not mean:

- provider readiness
- external service readiness
- Fixed DAG runtime completion
- frontend v2 completion
- production deployment readiness
