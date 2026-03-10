# Regression Scripts (Phase 3.2)

These scripts are tooling-only and do not change runtime business logic.

## 1) Run the 10-turn Phase 2.5 regression

Script: `scripts/phase25_regress_10turn.py`

Behavior:
- Same-process, same `thread_id`, multi-turn invoke
- Turn 1-3: `REACT_AGENT_STABLE_CONSUME=0`
- Turn 4-10: `REACT_AGENT_STABLE_CONSUME=1`
- Sets env defaults for reproducible regression:
  - `REACT_AGENT_CHECKPOINTER=memory`
  - `REACT_AGENT_RESULTS_POOLS=1`
  - `REACT_AGENT_THREAD_SUMMARY=1`
  - `REACT_AGENT_MESSAGES_WINDOW=1`
  - `REACT_AGENT_MESSAGES_WINDOW_SIZE=<window_size>`
  - `LOCAL_TRACE=1`
  - `DISABLE_SEARCH=1`
  - `TAVILY_API_KEY=dummy-key`
  - `LOG_DIR=<log_dir>`

Windows (PowerShell):

```powershell
python scripts/phase25_regress_10turn.py `
  --thread_id phase25-regress-10turn `
  --log_dir "$env:TEMP\\phase25_regress_10turn\\logs" `
  --turns 10 `
  --consume_switch_turn 4 `
  --window_size 20 `
  --use_real_model auto
```

Unix:

```bash
python scripts/phase25_regress_10turn.py \
  --thread_id phase25-regress-10turn \
  --log_dir "${TMPDIR:-/tmp}/phase25_regress_10turn/logs" \
  --turns 10 \
  --consume_switch_turn 4 \
  --window_size 20 \
  --use_real_model auto
```

Output:
- Per-turn console lines with:
  - `turn`, `consume_enabled`, `is_last_step`, `stable_len`, `thread_summary_len`, `messages_len`
- JSON summary:
  - `<log_dir>/per_turn_summary.json`

## 2) Analyze LOCAL_TRACE logs

Script: `scripts/analyze_trace.py`

Reads all `*.jsonl` under `LOG_DIR` (multi-file) and prints JSON + short table:
- event counts
- `router_ctx`/`manager_ctx` context stats (`ctx_messages_len`, `full_messages_len`, min/median/max)
- window violation count (`ctx_messages_len > window_size` when `full_messages_len > window_size`)
- `stable_consume` summary (`by_node` stats + sample events)

Windows (PowerShell):

```powershell
python scripts/analyze_trace.py `
  --log_dir "$env:TEMP\\phase25_regress_10turn\\logs" `
  --window_size 20 `
  --out_json "$env:TEMP\\phase25_regress_10turn\\summary.json"
```

Unix:

```bash
python scripts/analyze_trace.py \
  --log_dir "${TMPDIR:-/tmp}/phase25_regress_10turn/logs" \
  --window_size 20 \
  --out_json "${TMPDIR:-/tmp}/phase25_regress_10turn/summary.json"
```

## Cost-control notes

- Keep `turns=10` for baseline regression.
- Keep `DISABLE_SEARCH=1` to avoid external search noise.
- Use `--use_real_model never` to force local dummy mode when external model is unavailable.

## Rollback / impact

- These scripts are additive tooling only.
- Removing `scripts/phase25_regress_10turn.py` and `scripts/analyze_trace.py` fully reverts this phase.
