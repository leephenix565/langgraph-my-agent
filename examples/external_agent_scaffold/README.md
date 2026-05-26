# External Agent Developer Package

This directory is the complete external-agent developer package. It contains
the protocol guide, protocol reference, AI coding handoff, runnable minimal
FastAPI scaffold, sample requests, and contract tests needed to build an
external HTTP agent for `langgraph-my-agent`.

Recommended reading order:

1. [README.md](README.md)
2. [EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md](EXTERNAL_AGENT_DEVELOPER_ONBOARDING_GUIDE.md)
3. [EXTERNAL_AGENT_INTEGRATION_STANDARD.md](EXTERNAL_AGENT_INTEGRATION_STANDARD.md)
4. [AI_CODING_HANDOFF.md](AI_CODING_HANDOFF.md)

This package is an example and handoff surface only. It is not registered in
`AGENT_TOOLS`, it does not modify `config/agents`, and it is not part of the
default graph runtime.

## What It Provides

- `GET /health`
- `POST /v1/agent/invoke`
- `external_agent_health_v0`
- `external_agent_request_v0`
- `external_agent_response_v0`
- typed errors
- deterministic `ok`, `needs_clarification`, and `error` paths
- no real LLM calls
- no external network dependency
- no secrets

## Start The Service

From the repo root:

```powershell
python -m uvicorn service:app --app-dir examples/external_agent_scaffold --host 127.0.0.1 --port 8100
```

## Smoke Test `/health`

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8100/health"
```

Equivalent curl:

```bash
curl http://127.0.0.1:8100/health
```

## Smoke Test `/v1/agent/invoke`

PowerShell:

```powershell
$body = Get-Content -Raw examples/external_agent_scaffold/sample_requests/invoke.request.json
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8100/v1/agent/invoke" `
  -ContentType "application/json" `
  -Body $body
```

curl:

```bash
curl -X POST http://127.0.0.1:8100/v1/agent/invoke \
  -H "Content-Type: application/json" \
  --data @examples/external_agent_scaffold/sample_requests/invoke.request.json
```

## Run Tests

```powershell
python -m pytest examples/external_agent_scaffold/tests -q
```

These are scaffold contract tests. They are not live graph, public API, or Web
E2E tests.

## How To Hand This To The Main System Maintainer

Give the maintainer:

- this service directory
- the external service id, `example_external_agent`
- the service URL, for example `http://127.0.0.1:8100/v1/agent/invoke`
- sample request and response JSON files
- health output
- test results
- `.env.example`
- a note that this service is a scaffold and does not make investment,
  compliance, valuation, or risk claims

The main system maintainer must still write a repo-side wrapper, choose the
main-system `agent_id`, map it to this external `agent_id`, and register that
wrapper into `AGENT_TOOLS[agent_id]` before default tool backfill. This scaffold
does not automatically connect to the graph.

For maintainer-side wrapper guidance, use
[../../docs/AGENT_REPLACEMENT_GUIDE.md](../../docs/AGENT_REPLACEMENT_GUIDE.md)
only as an internal replacement guide. Its `/invoke`, `/healthz`, and direct
`AgentOutput` examples are not the third-party external-agent standard.

## Safety Rules

- Do not add real API keys to `.env.example`.
- Do not return traceback text.
- Do not return raw provider responses.
- Do not expose chain-of-thought.
- Do not claim that this scaffold is runtime-connected until a main-system
  wrapper is implemented and validated.
- Do not call scaffold tests or wrapper mock tests live graph/Web E2E evidence.
