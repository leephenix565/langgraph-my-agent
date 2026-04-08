# langgraph-public-adapter

## Use When

- Designing, implementing, or reviewing the public adapter / BFF between LangGraph runtime and `apps/web`
- Defining safe response contracts for transcript turns, workflow snapshots, continuity modes, and final-answer provenance

## Boundaries

- Never expose `state["messages"]` as the public transcript.
- Never expose raw router outputs, raw manager assignments, raw agent JSON, or chain-of-thought.
- Preserve the separation between mainline bundle, emitted bundle, and fusion sidecars.
- Replay continuity must be disclosed as weaker than persistent graph continuity.
- Do not describe sync-only F3 behavior as streaming or step-level live tracing.
- Prefer extending existing public contracts and `/api/health` over inventing a separate raw debug API.

## Expected Outputs

- A safe public contract for thread list/detail/send-message APIs
- Clear mapping from runtime state surfaces such as `emitted_bundle`, `final_answer_source`, and workflow progress fields
- Explicit continuity-mode behavior (`persistent` vs `replay`)
- Structured readiness and sanitized failure semantics for health and message APIs
- Documentation of what remains internal-only
