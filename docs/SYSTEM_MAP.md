# SYSTEM_MAP (Single Source of Truth)

## Scope Boundary
- This document is the S0 operational map for runtime, benchmark, train, and eval entrypoints.
- For the current narrative snapshot and reusable project description, see `docs/PROJECT_OVERVIEW.md`.
- If `PROJECT_OVERVIEW` conflicts with runtime code or this document, prefer runtime code plus this document and `docs/RUNBOOK_ROUTER_SFT.md`.
- Optional capabilities such as `REACT_AGENT_CHECKPOINTER`, `REACT_AGENT_THREAD_SUMMARY`, `REACT_AGENT_MESSAGES_WINDOW`, `REACT_AGENT_RESULTS_POOLS`, and `REACT_AGENT_STABLE_CONSUME` are env-gated and must not be assumed on by default.

## Environment Baseline (Local/Codex)
- Python requirement: `>=3.11,<4.0` (from `pyproject.toml`).
- Official local execution env: conda `cline_env`.
- Do not use bare `python` for validation. It can resolve to system Python 3.7 and cause false failures.
- `TAVILY_API_KEY` is an import-time prerequisite because `src/react_agent/tools.py` instantiates the Tavily search tool at module import.
- Default local dev baseline keeps remote LangSmith tracing off. Treat `LANGSMITH_TRACING=true` as explicit opt-in, not as a baseline requirement.
- `LOCAL_TRACE=1` enables the repo-local JSONL logger in `src/react_agent/run_logger.py`; it is separate from remote LangSmith tracing.
- Studio / API schema export now relies on a schema-generatable `AgentOutput` type surface in `src/react_agent/agents.py`; runtime results remain plain dicts and keep current `parse_ok` / `contract` / extra-key compatibility.
- FF-1 adds a final-summary seam field `State.multi_agent_bundle` for mainline bundle capture. It is written only on the final summary path and remains isolated from `analyst_results` / `ephemeral_results` / agent `shared_context`.
- FF-2A adds an isolated `baseline_sidecar` shadow scaffold behind `Context.enable_fair_fusion` (default off). It writes only `State.baseline_status` and `State.baseline_bundle`, is not part of L1-L4, does not enter a01 contract, and does not write to results pools.
- FF-2A also adds baseline-specific context knobs:
  - `baseline_model`
  - `baseline_openai_base_url`
  - `baseline_openai_api_key`
  - `enable_fair_fusion`
  - `baseline_force_search`
- `baseline_force_search` in FF-2A is metadata/prompt intent only. Provider-native hard binding remains a later phase and must not be assumed complete in this scaffold.
- FF-2B hardens the `baseline_sidecar` only when the baseline provider is `google_genai/...`:
  - baseline calls the Gemini Developer API directly via `google-genai`, not the generic LangChain `model.ainvoke(...)` path
  - Gemini Developer API path uses `GOOGLE_API_KEY` with `vertexai=False`; it does not use `baseline_openai_base_url` / `baseline_openai_api_key`
  - grounding/search is requested through Gemini's Google Search tool binding, and `baseline_bundle.search_meta` now includes provider/search receipts such as `search_executed`, `grounding_metadata_present`, `web_search_queries`, and grounding counts
  - `baseline_force_search` remains only a request-intent flag for non-Gemini providers
- FF-2B.1 compatibility note for Gemini grounding:
  - Gemini grounding/search tool use is incompatible with `response_mime_type="application/json"`
  - the Gemini baseline path therefore uses prompt-constrained JSON plus local parsing of `response.text`
  - this is a request-construction compatibility fix only; it does not change mainline graph control flow or baseline state isolation
- FF-3A adds a Judge-ready fan-in seam without switching the final answer source:
  - `State.mainline_status`, `State.mainline_emit_payload`, and `State.final_answer_source` are isolated readiness/emit fields outside results pools
  - when `enable_fair_fusion=True`, final-layer mainline summary now stages `multi_agent_bundle` plus `mainline_status="ready"` before any final emit
  - `baseline_sidecar` no longer ends directly at `__end__`; it reaches a branch-safe `fusion_gate`
  - `fusion_gate` is not a judge and not a writer; it only checks readiness before handing off to the later compare/write/emit seam
  - the runtime now closes out through a source-neutral `final_emit` seam; `mainline_emit` remains only as a compatibility wrapper while `final_answer_source` still stays `"mainline"` in the current phase
  - `mainline_status="ready"` is intentionally distinct from `is_last_step=True`
- FF-3B adds a shadow-only fusion judge without switching the final answer source:
  - `State.judge_status` and `State.fusion_verdict` are isolated judge sidecars outside results pools
  - `fusion_gate` now routes compare-ready A/B inputs to `fusion_judge_shadow`, and no longer treats judge completion as a direct emit step
  - `fusion_judge_shadow` reads only `multi_agent_bundle`, `baseline_status`, and `baseline_bundle`; it does not read raw `analyst_results`, `ephemeral_results`, `layer_plan`, or raw `a25_output`
  - `fusion_verdict` is a shadow JSON verdict only; it does not change `messages` or `final_answer_source`
- FF-4A adds a shadow-only fusion writer plus a source-neutral emit seam without switching the final answer source:
  - `State.writer_status`, `State.writer_output`, and `State.final_emit_payload` are isolated writer/emit sidecars outside results pools
  - `fusion_verdict` is now writer-ready and includes `decision` (`mainline|baseline|fused`), `rewrite_plan`, and `accepted_cards`
  - `fusion_judge_shadow` now hands off to `fusion_writer_shadow`, which reads only `fusion_verdict`, `multi_agent_bundle`, `baseline_status`, and `baseline_bundle`
  - `fusion_writer_shadow` writes only shadow artifacts plus `final_emit_payload`; it does not write `messages` or change `final_answer_source`
  - `final_emit` is now the source-neutral closeout seam, but FF-4A still maps it to the staged mainline answer and keeps `final_answer_source="mainline"`
  - `memory_update` remains tied only to the final emitted `messages` and `is_last_step=True`
- FF-4B enables a guarded final source switch on top of the FF-4A seam:
  - `Context.enable_fair_fusion_source_switch` defaults to `False`; with the flag off, current visible behavior remains unchanged and still emits the mainline answer
  - `State.emitted_bundle` now records the actual bundle used by the final visible emit, separate from `State.multi_agent_bundle` which remains the canonical A-line mainline bundle
  - when the flag is enabled, `final_emit_payload` can materialize `mainline`, `baseline`, or `fused` payloads and `final_emit` / `_emit_final_answer` preserve closeout semantics while writing the selected `final_answer_source`
  - `stable_findings` continues to use mainline `filtered_results`, but its `question` and `final_answer` now come from the actual `emitted_bundle`
- FF-5B adds deterministic fusion regression / eval / gate tooling without changing graph business semantics:
  - new tooling lives under `ops/regression/fusion/`
  - the default harness is deterministic, network-free, and reuses existing FF-1 .. FF-4B state surfaces instead of calling live providers
  - fixed artifacts are `ops/regression/fusion/out/fusion_runs.jsonl`, `fusion_metrics.json`, and `fusion_gate.json`
  - `trace_noise` is tracked separately from `business_status`; LangSmith 403 and local trace issues do not count as default business failures
- Gemini baseline env baseline:
  - `GOOGLE_API_KEY=...`
  - `GOOGLE_GENAI_USE_VERTEXAI=false`
  - `BASELINE_MODEL=google_genai/gemini-3-pro-preview`
  - `ENABLE_FAIR_FUSION=true`
  - `BASELINE_FORCE_SEARCH=true`
- Windows pytest recommended command (execution-layer workaround):
```bash
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/
```
- Reason: this bypasses conda's captured-output re-print path (where `UnicodeEncodeError(gbk)` can occur in `conda\cli\main_run.py`).
- This does not change project/test logic; it only stabilizes local command execution on Windows terminals.
- Minimal smoke with placeholder key:
```bash
# PowerShell
$env:TAVILY_API_KEY="test-key"
conda run -n cline_env python -c "from react_agent import graph_app; print(graph_app is not None)"
```
- Local tracing distinction:
  - `LOCAL_TRACE=1`: writes JSONL under `log/<YYYYMMDD>/` via `run_logger.py`; no remote upload.
  - `LANGSMITH_TRACING=true`: remote LangSmith upload path; if explicitly enabled, 403 multipart ingest warnings are tracing-channel noise rather than graph control-flow failure.
- FF-5B gate classification note:
  - `langsmith_403`, `langsmith_ingest_warning`, `local_trace_malformed_jsonl`, and `local_trace_io_warning` belong to trace-noise classification, not default business-failure classification.
- Existing untracked local `.env` files may still carry `LANGSMITH_TRACING=true` from older baselines. That local file must be aligned manually if you want `langgraph dev` to stop emitting remote ingest warnings immediately.
- Interpreter checks:
```bash
conda run -n cline_env python --version
conda run -n cline_env python -c "import sys; print(sys.executable)"
```

## Phase 2 Snapshot Status (Structure-Stable)
- Current milestone is `structure-stable`, not `quality-stable`.
- This status refers to runtime structure, protocol closure, and focused test coverage; it does not imply that all environment, training, or documentation issues are closed.
- Deferred backlog: U4 (`tests/` structure + `conftest` + CI + Makefile linkage refactor).
- Known blockers (not resolved in this document update):
  - Windows terminal runs of `conda run -n cline_env python -m pytest ...` may hit `UnicodeEncodeError(gbk)` in conda output handling.
- Current main risk focus has shifted from structure refactor to test baseline and environment execution stability.

## Windows Pytest Fallback (Verification-Only)
- Baseline remains conda-based pytest; on Windows use `conda run --no-capture-output -n cline_env python -m pytest ...`.
- If Windows terminal execution fails with `UnicodeEncodeError(gbk)` from `conda run`, temporarily verify with direct interpreter invocation:
```bash
D:\AnacondaEnvs\cline_env\python.exe -m pytest tests/unit_tests/
```
- This fallback is for local verification only and does not replace the official environment baseline.

## Fusion Regression / Eval / Gate (FF-5B)
- Directory: `ops/regression/fusion/`
- Entrypoints:
```bash
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.run_fusion_regression
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.eval_fusion_outputs
conda run --no-capture-output -n cline_env python -m ops.regression.fusion.gate_fusion_outputs
```
- Scenario catalog is deterministic and currently covers:
  - flag matrix
  - source matrix
  - baseline terminal matrix
  - shadow consistency matrix
  - emitted provenance matrix
  - results-pool isolation matrix
- Fixed artifacts under `ops/regression/fusion/out/`:
  - `fusion_runs.jsonl`: per-case run records with flags, terminal statuses, source-selection fields, emitted-bundle/message summaries, stable-findings/thread-summary summaries, `business_status`, `trace_noise`, and notes
  - `fusion_metrics.json`: aggregated deterministic metrics
  - `fusion_gate.json`: gate verdict with thresholds, failing checks, warning checks, and metrics snapshot
- Default gate policy:
  - deterministic and network-free
  - live/provider smoke is optional and not part of the default gate
  - trace noise is reported separately and does not fail the gate by itself

## Benchmark Entry (Qwen Server, Raw + E2E)
- Harness entry: `tools/bench_doubao_seed2_speed.py`.
- Full-system routing requirement: keep `ROUTER_MODEL`, `ROUTER_OPENAI_BASE_URL`, `ROUTER_OPENAI_API_KEY` unset so Router/Manager/Agents use the same global OpenAI-compatible endpoint.
- E2E benchmark uses `graph.ainvoke(...)` timing and keeps `DISABLE_SEARCH=1` (default) to reduce search-noise variance.

Dry-run:
```bash
D:\AnacondaEnvs\cline_env\python.exe tools/bench_doubao_seed2_speed.py --models "qwen=Qwen3-30B-A3B-Instruct-2507-int8" --base-url "http://10.7.46.122:8000/v1" --runs 1 --dry-run
```

Real-run (3 samples, output artifacts):
```bash
D:\AnacondaEnvs\cline_env\python.exe tools/bench_doubao_seed2_speed.py --models "qwen=Qwen3-30B-A3B-Instruct-2507-int8" --base-url "http://10.7.46.122:8000/v1" --runs 3 --e2e-timeout 1200 --out-csv outputs/benchmarks/qwen30b_e2e_20260311.csv --out-md outputs/benchmarks/qwen30b_e2e_20260311.md
```

Node-level profiling (sidecar, no business-logic change):
```bash
D:\AnacondaEnvs\cline_env\python.exe tools/bench_doubao_seed2_speed.py --models "qwen=Qwen3-30B-A3B-Instruct-2507-int8" --base-url "http://10.7.46.122:8000/v1" --runs 3 --e2e-timeout 1200 --out-csv outputs/benchmarks/qwen30b_e2e_20260311.csv --out-md outputs/benchmarks/qwen30b_e2e_20260311.md --enable-profiling
```
- Profiling sidecar defaults:
  - trace logs: `outputs/benchmarks/qwen30b_e2e_20260311_trace/*.jsonl`
  - summary sidecar: `outputs/benchmarks/qwen30b_e2e_20260311_profile.json`
- Aggregation uses trace `node_latency` events to summarize router / manager_broadcast / agent / summary / finalize node elapsed times.

Result artifacts:
- `outputs/benchmarks/qwen30b_e2e_20260311.csv`
- `outputs/benchmarks/qwen30b_e2e_20260311.md`
- This benchmark update is execution evidence only; no runtime business logic change.


閺囧瓨鏌婇弮鍫曟？閿?026-03-10

妤傛ê鐪伴崣娆庣皑閸忋儱褰涢敍姝歞ocs/PROJECT_OVERVIEW.md`閿涘牐鐭剧痪鍨禈 + 閹稿洦鐖ｆ担鎾堕兇 + 娑撹桨缍?SLM 閺囨潙宸遍敍娑楃瑝閸栧懎鎯堥崨鎴掓姢娑撳孩鎼锋担婊呯矎閼哄偊绱?
a01 閸氬牆鎮撻崡蹇氼唴閸忋儱褰涢敍姝歞ocs/A01_CONTRACT_SCHEMA_V0.md`閿涘澃chema v0 + 鏉╂劘顢戦幀浣圭Х鐠愮顫夐崚娆欑礆

## 0) 閸楀繋缍旈懕姘卞妽閼煎啫娲块敍鍫ユ▉濞堝吀绔撮弫瀵告倞閿?- 鏉╂劘顢戞稉鑽ゅ殠閻╊喖缍嶆穱婵囧瘮娑撳秴褰夐敍姝歴rc/react_agent/`閵嗕梗config/agents/`閵嗕梗langgraph.json`閵嗕梗pyproject.toml`閵嗕梗react_agent/`閵嗕梗sitecustomize.py`閵?- 缁傝崵鍤庨弫鐗堝祦閺嬪嫬缂撻懘姘拱瀹告彃缍婇獮鎯板殾閿涙瓪ops/data_pipeline/`閵?- 闂堢偘瀵岀痪鍨坊閸欒尪顕╅弰搴濈瑢閸欏倽鈧啳绁禍褍鍑¤ぐ鎺戣嫙閼风绱癭docs/archive/` 娑?`assets/reference/`閵?- Codex 娑撹崵鍤庨崡蹇庣稊姒涙顓绘导妯哄帥閸忚櫕鏁炴潻鎰攽娑撹崵鍤庨惄顔肩秿娑?S0 閺傚洦銆傞敍娑樼秺濡楋絿娲拌ぐ鏇炲讲閹稿娓剁拠璇插絿閵?
## 1) 鏉╂劘顢戦幀浣稿弳閸欙絼绗岄張鈧亸蹇撴儙閸?
### LangGraph Studio / CLI
- 閸忋儱褰涢柊宥囩枂閿涙瓪langgraph.json` 閹稿洤鎮?`src/react_agent/graph.py:graph`閵?
```json
{
  "graphs": { "agent": "./src/react_agent/graph.py:graph" },
  "env": ".env"
}
```
- 娴犳挸绨遍崘鍛弓閹绘劒绶甸弰搴ｂ€橀惃?CLI 閸氼垰濮╅崨鎴掓姢閵嗗倷濞囬悽?LangGraph Studio/CLI 閺冭泛绨茬拠璇插絿娑撳﹨鍫?`langgraph.json`閵?

### Python 閺堚偓鐏忓繗绻嶇悰?
- 缁€杞扮伐閼存碍婀伴敍姝歞emo_layered_run.py`
```bash
conda run -n cline_env python demo_layered_run.py
```
- 閻╁瓨甯?import閿涘牊娓剁亸蹇曘仛娓氬绱?
```bash
conda run -n cline_env python -c "from react_agent import graph_app; from react_agent.context import Context; import asyncio; print(asyncio.run(graph_app.ainvoke({'messages':[('user','hi')]} , context=Context())))"
```

### Thread persistence閿涘湧ython / 閼奉亜缂?API閿涘苯褰查柅澶涚礆
- 姒涙顓婚崗鎶芥４閿涙碍婀拋鍓х枂 `REACT_AGENT_CHECKPOINTER`閿涘牊鍨ㄧ拋鍙ヨ礋 `none`閿涘妞傞敍瀛瓂thon/閼奉亜缂?API 娑撳骸缍嬮崜宥堫攽娑撹桨绔撮懛杈剧幢`graph`閿涘湯tudio/CLI 姒涙顓婚崗銉ュ經閿涘顫愮紒鍫滅箽閹镐焦妫ゆ稉姘鐏?checkpointer閵?
- 閸欘垶鈧绱戦崗绛圭礄闂団偓閸?import `react_agent.graph` / `graph_app` 娑斿澧犵拋鍓х枂閿涘绱?
  - `REACT_AGENT_CHECKPOINTER=memory`閿涙艾鎯庨悽銊ㄧ箻缁嬪鍞撮惌顓熸埂閹镐椒绠欓崠鏍电礄閸氬奔绔存潻娑氣柤閸愬懎顦垮▎?invoke + 閻╃鎮?`thread_id` 閸欘垰顦查悽?state閿?
  - `REACT_AGENT_CHECKPOINTER=sqlite`閿涙艾褰查柅澶涚幢閼汇儲婀€瑰顥婄€电懓绨叉笟婵婄娴兼俺鍤滈崝銊╂缁狙傝礋娑撳秴鎯庨悽顭掔礄楠炲墎绮伴崙?warning閿?
  - `REACT_AGENT_CHECKPOINT_DB=checkpoints.db`閿涙qlite 濡€崇础娑撳娈戦弫鐗堝祦鎼存捁鐭惧鍕剁礄閸欘垶鈧绱?
- Python / 閼奉亜缂?API 瀵ら缚顔呴柅姘崇箖 `react_agent.graph.get_graph_for_invoke(thread_id)` 闁瀚ㄩ崶鎯ь嚠鐠炩槄绱遍崣顏呮箒閳ユ粌绱戦崗鍐插嚒閸氼垳鏁?+ 閹绘劒绶?thread_id閳ユ繃妞傞幍宥勭窗鐠х増瀵旀稊鍛閸ヤ勘鈧?
- invoke 閺冨爼娓剁憰浣规▔瀵繋绱堕崗?`thread_id`閿涘牆鎯侀崚娆庣矝閹稿鏌婃导姘崇樈婢跺嫮鎮婇敍澶涚窗
```python
import react_agent.graph as graph_module

thread_id = "demo-thread-1"
app = graph_module.get_graph_for_invoke(thread_id)
await app.ainvoke(
    {"messages": [("user", "閹存垵褰ㄧ亸蹇旀")]},
    context=Context(),
    config={"configurable": {"thread_id": thread_id}},
)
```
- demo 妤犲矁鐦夐敍鍫濇倱娑撯偓 thread_id 娑撱倛鐤?+ 娑撳秳绱?thread_id 鐎靛湱鍙庨敍澶涚窗
```bash
# PowerShell
$env:REACT_AGENT_CHECKPOINTER="memory"
conda run -n cline_env python demo_layered_run.py
```
- 閸ョ偞绮撮弬鐟扮础閿涙艾鍨归梽銈堫嚉閻滎垰顣ㄩ崣姗€鍣洪幋鏍啎缂?`REACT_AGENT_CHECKPOINTER=none`閿涘苯鑻熼柌宥呮儙鏉╂稓鈻奸敍鍫滃▏ graph 闁插秵鏌?compile閿涘鈧?
### Thread summary閿涘湧hase 2.2閿涘苯褰查柅澶涚礆
- 姒涙顓婚崗鎶芥４閿涙碍婀拋鍓х枂 `REACT_AGENT_THREAD_SUMMARY`閿涘牊鍨ㄧ拋鍙ヨ礋 `0`/`false`閿涘妞傞敍灞肩瑝娴兼碍鏌婃晶?`thread_summary` 閺囧瓨鏌婇敍灞肩瘍娑撳秳绱扮紒?Router / Manager Summary 濞夈劌鍙嗘０婵嗩樆濞戝牊浼呴妴?- 瀵偓閸忕绱欏楦款唴閸︺劑鏆辨潻娑氣柤閸氼垰濮╅崜宥堫啎缂冾噯绱氶敍?  - `REACT_AGENT_THREAD_SUMMARY=1`閿涙艾鎯庨悽銊х波濡楀牆鎮楁稉鈧▎鈩冣偓褎娲块弬鎵畱 extractive 娴兼俺鐦藉锝嗩攳
  - `REACT_AGENT_THREAD_SUMMARY_MAX_CHARS=2000`閿涙碍甯堕崚?`thread_summary` 閺堚偓婢堆囨毐鎼达讣绱欐妯款吇 2000閿?- 閻㈢喐鏅ラ崜宥嗗絹閿涘牐娉曟径姘偧 invoke 婢跺秶鏁ら敍澶涚窗
  - 娴犲懎绱戦崥?`REACT_AGENT_THREAD_SUMMARY=1` 閺冩湹绱扮亸婵婄槸閺囧瓨鏌?濞夈劌鍙?  - 閼汇儱绗囬張娑楃瑓娑撯偓鏉烆喖褰茬拠璇插煂娑撳﹣绔存潪顔芥喅鐟曚緤绱濋棁鈧憰渚€鍘ら崥?Phase 2.1 閹镐椒绠欓崠鏍电窗`REACT_AGENT_CHECKPOINTER=memory|sqlite` + 閻╃鎮?`thread_id`
- 閺囧瓨鏌婇弮鑸垫簚閿涙矮绮庨崷銊︽付缂佸牆鐪?`manager_summary()` 缂佹挻顢嶇捄顖氱窞閿涘潉is_last_step=True`閿涘鎮楅敍宀€绮?`memory_update` 閼哄倻鍋ｉ弴瀛樻煀娑撯偓濞嗏槄绱遍棃鐐存付缂佸牆鐪版稉宥嗘纯閺傝埇鈧?- 濞夈劌鍙嗛懠鍐ㄦ纯閿涘牆绱戦崥顖欑瑬 `thread_summary` 闂堢偟鈹栭弮璁圭礆閿?  - Router閿涙瓪router_node()` 閸?Router system prompt 閸氬氦鎷烽崝鐘辩閺?system message閿涘澅hread summary閿?  - Manager Summary閿涙瓪manager_summary()` 閺堚偓缂佸牊鐪归幀?LLM 閻?system prompt 閸氬氦鎷烽崝鐘辩閺?system message閿涘澅hread summary閿?- 闂堢偞鏁為崗銉ㄥ瘱閸ヨ揪绱欓張顒冪枂绾剛瀹抽弶鐕傜礆閿?  - 娑撳秵鏁?`manager_broadcast()` 閻ㄥ嫭娣冲?`assignment_text`
  - 娑撳秵鏁?AgentInput閿涘湏gent 娑撳秶娲块幒銉﹀灗闂傚瓨甯撮惇瀣煂 `thread_summary`閿?- 閹芥顩﹂弸鍕偓鐘电摜閻ｃ儻绱欓弮鐘活杺婢?LLM 鐠嬪啰鏁ら敍澶涚窗
  - 娴犲懍濞囬悽銊︽▔瀵繑鏋冮張顒婄礄`state.current_question` / 閺堚偓鏉?HumanMessage + 閺堚偓鏉?AIMessage 閺傚洦婀伴敍澶涚礉閸ュ搫鐣惧Ο鈩冩緲閹峰吋甯撮獮鑸靛焻閺傤叏绱辨稉宥呬粵閻㈢喐鍨氬蹇旀暭閸愭瑣鈧?- demo 妤犲本鏁归敍鍫濈紦鐠侇喕绗?Phase 2.1 娑撯偓鐠у嘲绱戦敍澶涚窗
```bash
# PowerShell
$env:REACT_AGENT_CHECKPOINTER="memory"
$env:REACT_AGENT_THREAD_SUMMARY="1"
conda run -n cline_env python demo_layered_run.py
```
- 妫板嫭婀￠敍姘倱娑撯偓 `thread_id` 缁楊兛绨╂潪顔跨翻閸戣桨绱伴幍鎾冲祪闂堢偟鈹?`thread_summary_len`閿涘牆鑻熼崣顖滄箙閸掗绗傛稉鈧潪顕€妫舵０?閸ョ偟鐡熼惃?extractive 閻楀洦顔岄敍澶涚幢娑撳秳绱?`thread_id` 閻ㄥ嫬顕悡褏绮嶆稉宥呯安缁嬪啿鐣炬径宥囨暏娑撳﹣绔存潪顔芥喅鐟曚降鈧?- 閸ョ偞绮撮弬鐟扮础閿涙瓪unset REACT_AGENT_THREAD_SUMMARY`閿涘牊鍨ㄧ拋鍙ヨ礋 `0`閿涘鑻熼柌宥呮儙鏉╂稓鈻奸敍娑橆洤閸氬本妞傛稉宥夋付鐟曚焦瀵旀稊鍛閿涘奔瀹抽崣顖氬絿濞?`REACT_AGENT_CHECKPOINTER`閵?
### Messages window / trim閿涘湧hase 2.3閿涘苯褰查柅澶涚礉Router + Manager Summary 鏉堟挸鍙嗛梽鎰暰閿?- 姒涙顓婚崗鎶芥４閿涙碍婀拋鍓х枂 `REACT_AGENT_MESSAGES_WINDOW`閿涘牊鍨ㄧ拋鍙ヨ礋 `0`/`false`閿涘妞傞敍瀛痮uter 娑?Manager Summary 娴犲秳濞囬悽銊ュ弿闁?`state["messages"]` 娴ｆ粈璐?LLM 鏉堟挸鍙嗘稉濠佺瑓閺傚洢鈧?- 瀵偓閸忓厖绗岄崣鍌涙殶閿涘牆缂撶拋顔兼躬闂€鑳箻缁嬪鎯庨崝銊ュ鐠佸墽鐤嗛敍澶涚窗
  - `REACT_AGENT_MESSAGES_WINDOW=1`閿涙艾鎯庨悽銊︾Х閹垳鐛ラ崣锝忕礄娴犲懎濂栭崫?Router 娑?Manager Summary 閻?LLM 鏉堟挸鍙嗛敍?  - `REACT_AGENT_MESSAGES_WINDOW_SIZE=20`閿涙氨鐛ラ崣锝呫亣鐏忓骏绱欓崣鏍ㄦ付閸?N 閺?messages閿涙盯绮拋?20閿涘本娓剁亸蹇庣窗 clamp 閸?1閿?- 鏉堟挸鍙嗙紒鎾寸€敍鍫濈磻閸氼垳鐛ラ崣锝嗘閿涘奔绻氶幐渚€銆庢惔蹇庣瑝閸欐﹫绱氶敍?  - Router閿涙瓪system_prompt + (optional thread_summary system msg) + window_messages`
  - Manager Summary閿涙瓪system_prompt + (optional thread_summary system msg) + window_messages + user_msg`
- 閸忕厧顔愰幀褝绱欐稉?Phase 2.2閿涘绱?  - `thread_summary` 濞夈劌鍙嗘い鍝勭碍娣囨繃瀵旈崷?system prompt 娑斿鎮楅妴浜€indow messages 娑斿澧?  - `_get_latest_user_question` 娑?`thread_summary` 閺嬪嫰鈧姳绮涚拠璇插絿閸忋劑鍣?messages閿涘牅绗夐崣妤冪崶閸欙絽濂栭崫宥忕礆
  - Agent 鐠侯垰绶?/ 濞叉儳浼愰弬鍥ㄦ拱娑撳秴褰夐敍鍫滅瑝閺€?`manager_broadcast` / AgentInput / `default_agents.py`閿?- 閸欘垵顫囧ù瀣剁礄閹恒劏宕橀敍澶涚窗
  - `LOCAL_TRACE=1` 閺冭绱濋弻銉ф箙 `router_ctx` / `manager_ctx` 娴滃娆㈡稉顓犳畱 `ctx_messages_len`閵嗕梗full_messages_len`閵嗕梗window_size`閿涘瞼鈥樼拋銈囩崶閸欙絿鏁撻弫?- demo 妤犲本鏁归敍鍫濆讲娑?Phase 2.1/2.2 缂佸嫬鎮庨敍澶涚窗
```bash
# PowerShell
$env:REACT_AGENT_CHECKPOINTER="memory"
$env:REACT_AGENT_THREAD_SUMMARY="1"
$env:REACT_AGENT_MESSAGES_WINDOW="1"
$env:REACT_AGENT_MESSAGES_WINDOW_SIZE="20"
$env:LOCAL_TRACE="1"
conda run -n cline_env python demo_layered_run.py
```
- 妫板嫭婀￠敍姘倱 thread 閸︾儤娅欐稉瀣╃矝閼崇晫婀呴崚?`thread_summary`閿涙矖LOCAL_TRACE` 閺冦儱绻旈柌?`router_ctx/manager_ctx` 閻?`ctx_messages_len` 娑撳秷绉存潻鍥╃崶閸欙絼绗傞梽鎰剁礄閸欐绉烽幁顖涒偓缁樻殶闂勬劕鍩楅敍澶堚偓?- 閸ョ偞绮撮弬鐟扮础閿涙瓪unset REACT_AGENT_MESSAGES_WINDOW`閿涘牊鍨ㄧ拋鍙ヨ礋 `0`閿涘鑻熼柌宥呮儙鏉╂稓鈻奸敍娑橆洤娑撳秹娓剁憰?trace閿涘苯鍙ч梻?`LOCAL_TRACE`閵?
### Results pools閿涘湧hase 2.4-B閿涘苯褰查柅澶涚礉stable/ephemeral 閸欏本鐫滈敍?- 姒涙顓婚崗鎶芥４閿涙瓪REACT_AGENT_RESULTS_POOLS` 閺堫亣顔曠純顔藉灗鐠佸彞璐?`0` 閺冭绱濈化鑽ょ埠濞岃法鏁ら悳鐗堟箒 `analyst_results` 閸楁洘鐫滈柅鏄忕帆閿涘牆瀵橀幏顒佺槨鏉?Router reset閿涘鈧?- 瀵偓閸氼垱鏌熷蹇ョ窗
  - `REACT_AGENT_RESULTS_POOLS=1`
  - 閸欘垶鈧妾烘０婵撶窗`REACT_AGENT_STABLE_FINDINGS_MAX_ITEMS=50`閵嗕梗REACT_AGENT_EVIDENCE_MAX_ITEMS=20`閵嗕梗REACT_AGENT_EVIDENCE_MAX_CHARS=500`閵嗕梗REACT_AGENT_STABLE_TEXT_MAX_CHARS=2000`
- 閸氼垳鏁ら崥搴ゎ嚔娑斿绱?  - `ephemeral_results`閿涙俺绻嶇悰灞炬埂缂佹挻鐏夊Ч鐙呯礄楠炴儼顢戦崣顖氭値楠炶绱氶敍灞剧槨鏉烆喚鏁?Router 閸?`__reset__` 濞撳懐鈹栭敍姹歡ent 娴犲懎鍟撶拠銉︾潨
  - `stable_findings`閿涙俺娉曟潪顔荤箽閻ｆ瑱绱濇禒鍛躬 `manager_summary()` 閺堚偓缂佸牏绮ㄥ鍫濆瀻閺€顖濇嫹閸旂姴鍟撻崗銉礄娑撳秳绶风挧?`memory_update`閿?  - `analyst_results`閿涙艾鍚嬬€瑰綊鏆呴崓蹇撶摟濞堢绱欐潻鍥ㄦ诞閺堢喍绻氶悾娆欑礆閿涘矂浼╅崗宥囩壃閸у繑妫拠鑽ゅ仯/閺冄勭ゴ鐠?  - 閸欙絽绶為敍姘儙閻?`REACT_AGENT_RESULTS_POOLS=1` 閸氬函绱漙ephemeral_results` 閺勵垵绻嶇悰灞炬埂閻喐绨敍娌梐nalyst_results` 娴犲懍璐熼崗鐓庮啇闂€婊冨剼閿涘苯顦婚柈銊ф纯閹恒儱鍟?`analyst_results` 娑撳秳绻氱拠浣筋潶缁崵绮虹拠璇插絿
- 鐠囪褰囨稉搴㈡暈閸忋儴绔熼悾宀嬬窗
  - Manager 濞叉儳浼?濮瑰洦鈧绗岀捄顖滄暠閹恒劏绻樻导妯哄帥鐠囨槒绻嶇悰灞炬埂濮圭媴绱欓崥顖滄暏閺冩湹璐?`ephemeral_results`閿?  - AgentInput `shared_context` 娴犲秴褰у▔銊ュ弳鏉╂劘顢戦張鐔哥潨閿涘奔绗夊▔銊ュ弳 `stable_findings`
  - `stable_findings` 閸楁洘娼張鈧亸蹇曠波閺嬪嫸绱癭kind/question/final_answer/evidence/run_id`閿涙矖evidence` 閺夈儴鍤?agent 鏉堟挸鍤?`evidence/key_points` 閻ㄥ嫭鍩呴弬顓犲偍瀵?- 閸欘垵顫囧ù瀣剁礄閹恒劏宕橀敍澶涚窗
  - `LOCAL_TRACE=1` 閺冭泛褰查弻銉ф箙 `ephemeral_reset` 娑?`stable_findings_update` 娴滃娆㈤敍鍫濇儓 `stable_len`閵嗕梗evidence_count`閿?- 妤犲本鏁归崨鎴掓姢閿?```bash
conda run --no-capture-output -n cline_env python -m pytest -q tests/unit_tests/test_results_pools_phase24b.py
```
- 閸ョ偞绮撮弬鐟扮础閿涙瓪unset REACT_AGENT_RESULTS_POOLS`閿涘牊鍨ㄧ拋鍙ヨ礋 `0`閿涘鑻熼柌宥呮儙闂€鑳箻缁嬪鈧?
### Stable findings consume閿涘湧hase 2.5閿涘苯褰查柅澶涚礉娴?Router + Manager Summary閿?- 姒涙顓婚崗鎶芥４閿涙瓪REACT_AGENT_STABLE_CONSUME` 閺堫亣顔曠純顔藉灗鐠佸彞璐?`0` 閺冭绱濇稉宥勭窗濞夈劌鍙?stable summary閿涘矂绮拋銈嗗灇閺堫兛绗岀悰灞艰礋娑撳秴褰夐妴?- 瀵偓閸忓厖绗岄崣鍌涙殶閿?  - `REACT_AGENT_STABLE_CONSUME=1`
  - `REACT_AGENT_STABLE_SUMMARY_MAX_CHARS=1200`閿涘牓绮拋?1200閿?  - `REACT_AGENT_STABLE_SUMMARY_MAX_ITEMS=5`閿涘牓绮拋?5閿涘苯褰囬張鈧潻?N 閺?stable findings閿?- 濞夈劌鍙嗘い鍝勭碍閿涘牆绱戦崥顖涙閿涘绱?  - Router閿涙瓪system_prompt + stable_summary + thread_summary + window_messages`
  - Manager Summary閿涙瓪system_prompt + stable_summary + thread_summary + window_messages + user_msg`
- 缁撅附娼潏鍦櫕閿?  - 娴?Router 娑?Manager Summary 濞戝牐鍨?stable findings
  - 娑撳秵鏁?`manager_broadcast` 濞叉儳浼愰弬鍥ㄦ拱閿涘奔绗夐弨?AgentInput/shared_context閿涘奔绗夐弨?`default_agents.py`
- 閸欘垵顫囧ù瀣剁礄閹恒劏宕橀敍澶涚窗
  - `LOCAL_TRACE=1` 閺冭埖鐓￠惇?`stable_consume` 娴滃娆㈤敍鍧刵ode/enabled/stable_len/stable_summary_len`閿?- 妤犲本鏁归崨鎴掓姢閿?```bash
conda run --no-capture-output -n cline_env python -m pytest -q tests/unit_tests/test_stable_consume_phase25.py
```
- 閸ョ偞绮撮弬鐟扮础閿涙瓪unset REACT_AGENT_STABLE_CONSUME`閿涘牊鍨ㄧ拋鍙ヨ礋 `0`閿涘鑻熼柌宥呮儙闂€鑳箻缁嬪鈧?
### Testing/Dev setup閿涘牆宕熷ù瀣箚婢у喛绱?閹恒劏宕橀張顒€婀撮張鈧亸蹇撶暔鐟佸懘鎽肩捄顖ょ礄娑?CI 鐎靛綊缍堥敍澶涚窗
```bash
conda run -n cline_env python --version
conda run -n cline_env python -m pip install -e .
conda run -n cline_env python -m pip install pytest
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/test_manager_contract_dispatch.py
```
鐠囧瓨妲戦敍姝歳equirements-hf.txt` 娑?`requirements-train.txt` 娑撻缚顔勭紒鍐х瑩閻劋绶风挧鏍电礉娑撳秳绻氱拠浣筋洬閻╂牞绻嶇悰灞锯偓浣瑰灗閸楁洘绁撮幍鈧棁鈧崠鍛偓?

## 2) 鏉╂劘顢戦柧鎹愮熅閿涘牆鍙嗛崣?閳?graph 閳?router 閳?manager 閳?agent 閳?summary閿?
- graph 閺嬪嫬缂撻敍姝歴rc/react_agent/graph.py`閿涘湯tateGraph + add_node/add_edge閿?
- Router閿涙瓪router_node()` 閻㈢喐鍨?`layer_plan/layer_mode` 楠炶泛鍟撻崗銉уЦ閹?
- Manager閿涙瓪manager_broadcast()` 閺嶈宓?mode 濞叉儳褰傞敍姹bate/Tree 闂勫秶楠囨稉?Star
- 閸氬牆鎮撴す鍗炲З閿涙艾缍?`analyst_results["a01_cio_orchestrator"]["contract"]` 閸欘垳鏁ゆ稉鏃€鐗庢宀勨偓姘崇箖閿涘畭manager_broadcast()` 閹?agent_id 閸掑洨澧栧ú鎯у絺 steps閿涙稑銇戠拹銉ユ礀闁偓濡剝婢橀獮鎸庢尡
- Agent閿涙瓪_build_agent_node()` 鐏忎浇顥?AgentInput 楠炶泛鍟撻崗?`analyst_results`
- Summary閿涙瓪manager_summary()` 閹恒劏绻樼仦鍌滈獓閹存牜鏁撻幋鎰付缂佸牏鐡熸径?

## 3) 鐠侇厾绮岄幀浣烘埂鐎圭偞绁︾粙瀣剁礄Router SFT閿?
鐠囷妇绮忛幙宥勭稊娑撳氦鐦夐幑顔肩秺濡楋綀顕憴渚婄窗`docs/RUNBOOK_ROUTER_SFT.md`閵?

### 3.1 閻㈢喐鍨?RouterPlan 閺佺増宓?
閼存碍婀伴敍姝歰ps/data_pipeline/generate_router_plans.py`
```bash
python ops/data_pipeline/generate_router_plans.py \
  --questions data/questions/questions_pool_YYYYMMDD_<catalog_id>.jsonl \
  --catalog-id <catalog_id> \
  --out-ok data/router_sft/router_sft_<date>_<catalog_id>.jsonl \
  --out-fail data/router_sft/router_sft_fail_<date>_<catalog_id>.jsonl
```
鏉堟挸鍤€涙顔岄敍鍦 閺嶉攱婀伴弽绋跨妇鐎涙顔岄敍澶涚窗
`catalog_id, question_id, source, bucket, question, mode_hint, teacher, router_plan_raw, router_plan_parsed, parser_ok, violations, [auto_fix, fix_notes]`

### 3.2 鐎电厧鍤拋顓犵矊閺嶇厧绱?
閼存碍婀伴敍姝歰ps/data_pipeline/export_router_sft_dataset.py`
```bash
python ops/data_pipeline/export_router_sft_dataset.py \
  --in-ok data/router_sft/router_sft_<date>_<catalog_id>.jsonl \
  --catalog-prompt data/catalogs/catalog_<catalog_id>_prompt.json \
  --out-messages data/sft/router_sft_messages_<catalog_id>.train.jsonl
```
鏉堟挸鍤€涙顔岄敍鍧ssages 閺嶇厧绱￠敍澶涚窗
`id, messages[system+user], response, meta`
MANIFEST閿涘牆婀?`data/router_sft/`閿涘绱扮拋鏉跨秿閿涙瓪seed, val_ratio, in_ok_sha256, out_train_sha256, out_val_sha256`閵?

### 3.3 閺佺増宓侀崙鍡楊槵閿涘牐鍤滈崝銊﹀ⅵ閺?+ 鏉╁洦鎶ら敍?
閼存碍婀伴敍姝歵ools/prepare_router_sft.py`
```bash
python tools/prepare_router_sft.py \
  --in-train data/sft/router_sft_messages_<catalog_id>.train.jsonl \
  --in-val data/sft/router_sft_messages_<catalog_id>.val.jsonl \
  --out-dir data/sft/prepared \
  --filter-mode strict \
  --emit-val-messages-strict
```
鏉堟挸鍤敍姝歱repared_train.jsonl / prepared_val.jsonl`閿涘潰essages 鏉╄棄濮?assistant 閸ョ偛鎮庨敍瀹甧ta 閸愭瑥鍙?parse_ok/parse_error 缁涘绱氶妴?
strict 閸欙絽绶為敍姝歱arse_ok == True && used_default_plan == False`閵?

### 3.4 QLoRA SFT 鐠侇厾绮岄敍鍦en3-4B閿?
娓氭繆绂嗛敍鍫濆讲闁绱氶敍姝歱ip install -r requirements-train.txt`
閼存碍婀伴敍姝歵ools/train_router_sft_qlora.py`
Phase 3.1 姒涙顓婚崥顖滄暏閸氬牆鑻熸禍褏澧块敍姝?-merge-and-save-full-model`閵?
閸忕厧顔愮拠瀛樻閿涙ransformers 4.57 娴ｈ法鏁?`eval_strategy`閿涙矞ompletion-only 鐠侇厾绮岄敍鍧ompt 鐏炲繗鏂€閿涘鏁?Trainer 婢跺嫮鎮婇敍姹篖oRA=4bit base + LoRA adapters閿涘牆褰茬拋顓犵矊閿涘绱遍梹鍨閻?`tokenizer.model_max_length` / `max_seq_len` 閹貉冨煑閵嗗倽顔勭紒鍐ц厬鐠佸墽鐤?`remove_unused_columns=False`閵嗕骏val 姒涙顓绘担璺ㄦ暏娑?train 閻╃鎮撻惃?batch size 楠炴儼顔曠純?eval_accumulation_steps=1閿涘奔浜掗柆鍨帳闂€鍨碍閸?OOM閿涙稑顩ч棁鈧ぐ璇茬俺閸忔娊妫寸拋顓犵矊閺?eval閿涘苯褰叉导?`--max-eval-samples 0`閿涘牅绱扮亸?eval_strategy 鐠佸彞璐?`no` 娑撴柧绗夐弸鍕紦 eval_dataset閿涘鈧?
```bash
python tools/train_router_sft_qlora.py \
  --base-model-path /root/autodl-tmp/models/Qwen3-4B-Instruct-2507 \
  --train-jsonl data/sft/prepared/prepared_train.jsonl \
  --val-jsonl data/sft/prepared/prepared_val.jsonl \
  --output-dir /root/autodl-tmp/out/router_sft_qlora \
  --max-seq-len 8192 \
  --seed 42 \
  --per-device-train-batch-size 1 \
  --gradient-accumulation-steps 16 \
  --lr 2e-4 \
  --num-epochs 1 \
  --merge-and-save-full-model
```

#### 3.4.1 Completion-only 鐠侇厾绮岄敍鍧ompt 鐏炲繗鏂€閿?
- 鐠侇厾绮屾禒鍛嚠 assistant閿涘湩outerPlan JSON閿涘娲栭崥鍫ｎ吀缁?loss閿涙埠rompt token 閻?labels 鐠佸彞璐?`-100`閵?
- 閸樼喎娲滈敍姘朵缉閸忓秵瀚欓崥鍫㈤兇缂?閻劍鍩涢幓鎰仛閿涘矁浠涢悞?RouterPlan JSON 閸氬牐顫夋潏鎾冲毉閵?
- 鐎圭偟骞囨担宥囩枂閿涙瓪tools/train_router_sft_qlora.py`閿涘潏ompletion-only tokenize + labels masking + collator閿涘鈧?

#### 3.4.2 JSON canonicalization閿涘潷repare 闂冭埖顔岄敍?
- `tools/prepare_router_sft.py` 閸?append assistant 閸ョ偛鎮庨崜宥忕礉閹惰棄褰?response 娑擃厸鈧粓顩绘稉顏勭暚閺?JSON閳ユ繐绱濋獮?`json.dumps(..., separators=(",",":"))` 鐟欏嫯瀵栭崠鏍モ偓?
- 閻╊喚娈戦敍姘櫤鐏忔垼顔勭紒鍐╂埂鏉堟挸鍤ǎ宄板弳闂?JSON 閸撳秴鎮楃紓鈧敍灞惧絹閸?eval 閻?`valid_json_rate`閵?

#### 3.4.3 QLoRA 鐠侇厾绮岀憰浣哄仯
- 闁插繐瀵插Ο鈥崇€疯箛鍛淬€忛幐?LoRA adapters 閹靛秷鍏樼拋顓犵矊閿涙瓪prepare_model_for_kbit_training` + `get_peft_model`閵?
- target_modules 闁插洨鏁ら崝銊︹偓浣瑰閹诲骏绱檘/k/v/o + gate/up/down proj 閻ㄥ嫪姘﹂梿鍡礆閵?
- 鐠侇厾绮岀紒鎾存将閸欘垳鏁?`--merge-and-save-full-model` 鏉堟挸鍤?`output-dir/merged`閿涘牆褰查惄瀛樺复 HF 閸旂姾娴囬敍澶堚偓?

#### 3.4.4 鐠侇厾绮岄張?eval 缁嬪啿鐣鹃幀?
- `remove_unused_columns=False` 闁灝鍘?閳ユ罚o columns match forward signature閳ユ縿鈧?
- eval 姒涙顓绘担璺ㄦ暏娑?train 閻╃鎮撻惃?batch size閿涘苯鑻熺拋鍓х枂 `eval_accumulation_steps=1` 娴犮儵妾锋担搴ㄦ毐鎼村繐鍨?OOM 妞嬪酣娅撻妴?
- 婵″倿娓惰ぐ璇茬俺閸忔娊妫寸拋顓犵矊閺?eval閿涙瓪--max-eval-samples 0`閿涘潒val_strategy="no"閿涘奔绗夐弸鍕紦 eval_dataset閿涘鈧?

### 3.5 Post-train eval / gate閿涘湚F閿?
娴ｈ法鏁?merge 閸氬孩膩閸ㄥ鐭惧鍕灗 adapter 閸氬牆鑻熼崥搴ｆ畱濡€崇€风捄顖氱窞閿?
```bash
conda run -n cline_env python ops/regression/router/run_regression_eval.py \
  --val-messages data/sft/router_sft_messages_<catalog_id>.val.jsonl \
  --mode hf \
  --hf-model-path /root/autodl-tmp/out/router_sft_qlora/merged \
  --device cuda \
  --temperature 0 \
  --seed 42 \
  --max-items 2 \
  --gate-mode repro \
  --out-dir /root/autodl-tmp/out/regression_eval
```

### 3.6 娴溠呭⒖娑撳簼绗呮潪鏂ょ礄AutoDL閿?
缁€杞扮伐娴溠呭⒖鐠侯垰绶為敍鍫熸降閼?AutoDL 閺冦儱绻旈敍澶涚窗
- 鐠侇厾绮屾潏鎾冲毉閻╊喖缍嶉敍姝?root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903/`
- 閸氬牆鑻熷Ο鈥崇€烽惄顔肩秿閿涙瓪/root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903/merged`
  - 缁?3.3G閿涘苯瀵橀崥?`model.safetensors` + `config.json` + tokenizer 閺傚洣娆?
- 閹垫挸瀵樻禍褏澧块敍?
  - `..._merged.tgz`閿涘牏瀹?2.4G閿涘绱伴崥鍫濊嫙閸氬海娈戦崗銊╁櫤濡€崇€烽弶鍐櫢閿涘苯褰查惄瀛樺复 HF 閸旂姾娴囬幒銊ф倞
  - `..._full.tgz`閿涙艾鍙忛惄顔肩秿閸栧拑绱欓崥顐ヮ唲缂佸啯妫╄箛?闁倿鍘ら崳?閻樿埖鈧胶鐡戦敍?

閹垫挸瀵樻稉搴濈瑓鏉炵晫銇氭笟瀣剁窗
```bash
# 閹垫挸瀵?merged
cd /root/autodl-tmp/out
tar -czf router_sft_qwen3_4b_qlora_full_20260123_155903_merged.tgz \
  router_sft_qwen3_4b_qlora_full_20260123_155903/merged

# 閹垫挸瀵橀崗銊ф窗瑜?
tar -czf router_sft_qwen3_4b_qlora_full_20260123_155903_full.tgz \
  router_sft_qwen3_4b_qlora_full_20260123_155903

# 娑撳娴囬敍鍫仛娓氬绱皊cp閿?
scp root@<autodl-host>:/root/autodl-tmp/out/router_sft_qwen3_4b_qlora_full_20260123_155903_merged.tgz .
```

閺堫剙婀存宀冪槈閸旂姾娴囬敍?
```python
from transformers import AutoTokenizer, AutoModelForCausalLM
tok = AutoTokenizer.from_pretrained("path/to/merged", trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained("path/to/merged", trust_remote_code=True)
```

### 3.6 a01-SFT 閺佺増宓侀梻顓犲箚閿涘澅eacher 閸氬牆鎮撻悽鐔稿灇閿?
鐟欏嫯瀵栭敍姝歞ocs/A01_SFT_DATA_V0.md`
绾剝顫夐崚娆欑窗`selected_agents` 韫囧懘銆忛崠鍛儓 `a01_cio_orchestrator` 娑撴梻鐡戞禍?Router 闁鑵戦梿鍡楁値閿涙矖tasks[].steps` 闂€鍨韫囧懘銆忛崷?[2,6]閵?
```bash
python ops/train_eval/a01/generate_a01_teacher_contracts.py \
  --router-sft data/router_sft/router_sft_<date>_<catalog_id>.jsonl \
  --questions data/questions/questions_pool_<date>_<catalog_id>.jsonl \
  --out-train data/a01_sft/a01_sft_messages_<date>_<catalog_id>.train.jsonl \
  --out-val data/a01_sft/a01_sft_messages_<date>_<catalog_id>.val.jsonl \
  --out-stats data/a01_sft/a01_sft_teacher_stats_<date>_<catalog_id>.json
```
DeepSeek teacher 姒涙顓?base_url 娑?`https://api.deepseek.com`閿涘當ndpoint 閸ュ搫鐣炬稉?`/chat/completions`閿涘牐绶崗?`https://api.deepseek.com/v1` 娑旂喍绱拌ぐ鎺嶇閸栨牕鍩岀拠銉ㄧ熅瀵板嫸绱氶妴?
`teacher_error` 娴犲懐绮虹拋?teacher 鐠嬪啰鏁ゅ鍌氱埗閿涘湚TTP/timeout/娴肩姾绶柨娆掝嚖閿涘绱濇稉宥呭瘶閸氼偄鎮楃紒顓犳畱 JSON/閸氬牆鎮撻弽锟犵崣婢惰精瑙﹂妴?
缂佺喕顓告禍褏澧块崠鍛儓鐠愩劑鍣虹憴鍌涚ゴ閹稿洦鐖ｉ敍鍧揺neric_steps_ratio_v1 / very_generic_steps_ratio_v1 / duplicate_steps_contract_count / avg_steps_per_task閿涘绱濋獮鎯八夐崗鍛邦唶瑜版洜楠囬崚鍡楃閿涘潛eneric_ratio_p50/p90/p95閵嗕箍ery_generic_ratio_p50/p90/p95閵嗕够teps_per_task_p50/p90/p95閵嗕龚uplicate_steps_contract_rate閿涘绱遍崥灞炬鏉堟挸鍤憴鍌涚ゴ鐎涙顔岄崚鍡曠秴閺佸府绱檈lapsed_ms_*閵嗕工ssistant_chars_*閵嗕菇sage_total_tokens_*閿涘绱濇稉鏃€鐦￠弶陇顔囪ぐ?meta.quality / meta.teacher 娑擃厾鏆€閻ユ洏鈧?
FINAL 閸愯崵绮ㄧ捄顖氱窞閿涙瓪data/a01_sft/final/a01_sft_messages_FINAL.{train,val}.jsonl` 娑?`data/a01_sft/final/a01_sft_teacher_stats_FINAL.json`閵?
娴溿倖甯撮崠鍜冪窗`docs/archive/handoff/HANDOFF_A01_SFT_FINAL.md`閵?
### 3.6.1 Phase 4.1 a01-SFT 鐠侇厾绮岄梻顓犲箚閿涘澃moke train 閳?eval 閳?gate閿?
娓氭繆绂嗙€瑰顥婇敍鍫ｎ唲缂?鐠囧嫭绁撮悳顖氼暔閿涘绱?
```bash
pip install -e .
pip install -r requirements-train.txt
pip install -r requirements-hf.txt
```
base-model-path 瀵ら缚顔呴幐鍥ф倻閸ュ搫鐣鹃惄顔肩秿閹?HF cache閿涘牅绌舵禍搴☆槻閻滈绗岄弮銉ョ箶鏉╁€熼嚋閿涘鈧精utoDL 閸︾儤娅欓崣顖濐啎缂?`HF_HOME`/`TRANSFORMERS_CACHE`閿涘苯鑻熺亸?`runs/` 閹稿洤鎮滈幐浣风畽閸栨牜娲忛敍鍫ｈ拫闁炬拝绱氶妴?
鐠侇厾绮岄敍鍧坥mpletion-only QLoRA閿涙稑褰х拠?FINAL閿涘奔绗夌憰鍡欐磰 data/a01_sft/final閿涘绱?
```bash
python ops/train_eval/a01/train_a01_sft_qlora.py \
  --base-model-path <base_model_or_adapter> \
  --train-jsonl data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl \
  --val-jsonl data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl \
  --output-dir runs/a01_sft/20260128_smoke \
  --max-steps 50 \
  --max-train-samples 200
```
鐠囧嫭绁撮敍鍧搑eedy閿涘本淇惔?0閿涘绱?
```bash
python ops/train_eval/a01/eval_a01_sft.py \
  --model-path runs/a01_sft/20260128_smoke \
  --val-jsonl data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl \
  --out-dir runs/a01_sft/20260128_smoke
```
eval_report 鐠囦焦宓佺€涙顔岄敍姝穉lid_json_rate / contract_ok_rate / schema_keys_match_rate + model_sha256 / model_dir_size / git_commit閵?
闂傘劎顩﹂敍鍫熸焽鐟封偓 metrics + run_manifest閿涘绱?
```bash
python ops/train_eval/a01/gate_a01_sft.py \
  --eval-report runs/a01_sft/20260128_smoke/eval_report.json
```
run_manifest 鐠囦焦宓佺€涙顔岄敍姝t_commit / data_sha256 / seed / package_versions / train_args閵?
閺堝秴濮熼崳銊ㄤ粓閸斻劏鐦夐幑顕嗙礄preflight閿涘绱?
```bash
python ops/train_eval/a01/server_preflight.py --out-dir runs/a01_sft/20260128_smoke
```

#### AutoDL 4090 (24GB) smoke runbook閿涘牆褰叉径宥呭煑閿?
鐠囦焦宓侀弬鍥︽閿涙瓪preflight.txt` / `run_manifest.json` / `eval_report.json`閿涘牆娼庨崷銊ユ倱娑撯偓 `runs/...` 閻╊喖缍嶉敍澶堚偓?
```bash
# 0) 閻╊喖缍嶆稉搴ｇ处鐎?
export HF_HOME=/root/autodl-tmp/hf
export TRANSFORMERS_CACHE=/root/autodl-tmp/hf
mkdir -p /root/autodl-tmp/models
mkdir -p /root/autodl-tmp/runs
ln -sfn /root/autodl-tmp/runs runs

# 1) 娓氭繆绂?
pip install -e .
pip install -r requirements-train.txt
pip install -r requirements-hf.txt

# 2) 閹峰褰?base model閿涘牏銇氭笟瀣剁礆
python -c "from transformers import AutoTokenizer, AutoModelForCausalLM; AutoTokenizer.from_pretrained('<hf_model_id>', cache_dir='/root/autodl-tmp/models'); AutoModelForCausalLM.from_pretrained('<hf_model_id>', cache_dir='/root/autodl-tmp/models')"

# 3) preflight
RUN_ID=$(date -u +%Y%m%d_%H%M%S)
OUT_DIR=/root/autodl-tmp/runs/a01_sft/${RUN_ID}_smoke
python ops/train_eval/a01/server_preflight.py --out-dir "$OUT_DIR"

# 4) smoke train
python ops/train_eval/a01/train_a01_sft_qlora.py \
  --base-model-path /root/autodl-tmp/models/<hf_model_id_or_path> \
  --train-jsonl data/a01_sft/final/a01_sft_messages_FINAL.train.jsonl \
  --val-jsonl data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl \
  --output-dir "$OUT_DIR" \
  --max-steps 50 \
  --max-train-samples 200 \
  --max-eval-samples 50

# 5) eval + gate
python ops/train_eval/a01/eval_a01_sft.py \
  --model-path "$OUT_DIR" \
  --val-jsonl data/a01_sft/final/a01_sft_messages_FINAL.val.jsonl \
  --out-dir "$OUT_DIR"
python ops/train_eval/a01/gate_a01_sft.py \
  --eval-report "$OUT_DIR/eval_report.json"
```
姒涙顓?`--max-new-tokens=4096`閿涘牓浼╅崗宥嗗焻閺傤厼顕遍懛?gate 閸嬪洤銇戠拹銉礆閿涙硞moke 婵″倿娓堕弴鏉戞彥閸欘垱澧滈崝銊╂閸?2048閿涘奔绲鹃棁鈧▔銊﹀壈閸欘垵鍏橀幋顏呮焽 JSON閵?
瑜版帗銆傜痪锕€鐣鹃敍姝歳uns/a01_sft/<run_id>_smoke/` 娣囨繄鏆€ `preflight.txt` + `run_manifest.json` + `eval_report.json`閿涙稐绗夌憰鍡欐磰 `data/a01_sft/final/*`閵?
閺堚偓鐏忓繑甯撻梾婊冩嚒娴犮倧绱?
```bash
nvidia-smi
df -h | head -n 5
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.version.cuda)"
git rev-parse HEAD
ls -la "$OUT_DIR"
```

### 3.7 AutoDL 娴滃鐤勭拠浣瑰祦閿涘牊妫╄箛妤佹喅鐠佸府绱?
- strict 鏉╁洦鎶ら敍姝祌ain 735/735 kept閿涙硣al 15/15 kept閿涙矞anon_success=100%閿涘牊娼甸懛?prepare 閺冦儱绻旈敍?
- completion-only閿涙rompt labels = -100閿涘牓浼╅崗宥嗗珯閸?prompt閿?
- QLoRA 娣囶喖顦查敍姝祌ainable params 閳?33,030,144閿?.8145%閿?
- HF preds canonical JSON 閸氬氦鐦庡ù瀣剁窗`valid_json_rate=1.0`閵嗕梗used_default_plan_rate=0.0`
- gate_mode=repro閿涙矮琚卞▎?run `hard_match=True`閵嗕梗meta_match=True`
- N=15 閹稿洦鐖ｇ悰銉ュ帠閿涙瓱xact_match=0/15閿涙驳ode_acc閿涙瓈1/L3/L4=1.0閿涘2閳?.8667閿涙碑accard閿涙瓈2閳?.4357閿涘3閳?.5367閿涘2+L3閳?.4862

### 3.8 Phase 3.1.2 / 3.1.3 瑜版挸澧犻悩鑸碘偓?
- 3.1.2閿涘牊鏆熼幑顔煎櫙婢跺洣绗屾潻鍥ㄦ姢閿涘绱扮€瑰本鍨氶敍鍧皌rict+canonical JSON + stats閿?
- 3.1.3閿涘牐顔勭紒鍐х瑢 post-train eval閿涘绱扮€瑰本鍨氶張鈧亸蹇涙４閻滎垽绱檆ompletion-only + QLoRA merge + HF eval/gate閿?
- 娑撳绔村銉窗閹绘劕宕?exact_match / Jaccard 閹稿洦鐖ｉ敍灞惧⒖婢?N 娑撳酣鏆辨惔蹇撳灙缁嬪啿鐣鹃幀褔鐛欑拠渚婄礄TODO閿?

## 4) 鐠囧嫭绁?/ 閹电绐囬敍鍧畊n_graph_batch 缂傚搫銇戦惃鍕禌娴狅絾绁︾粙瀣剁礆

娴犳挸绨辨稉?*娑撳秴鐡ㄩ崷?* `run_graph_batch` 閼存碍婀伴妴鍌氱杽闂勫懏娴涙禒锝嗙ウ缁嬪顩ф稉瀣剁窗

### 4.1 閻㈢喐鍨?preds.jsonl閿涘潷rovider 濡€崇€烽敍?
閼存碍婀伴敍姝歰ps/regression/router/generate_router_preds.py`
```bash
conda run -n cline_env python ops/regression/router/generate_router_preds.py \
  --in data/sft/router_sft_messages_...val.jsonl \
  --out tmp/preds.jsonl \
  --model deepseek/deepseek-chat
```
濮ｅ繑娼拋鏉跨秿娴兼岸妾敮?`meta`閿涙瓪provider/model, prompt_format, source_val_path/source_val_sha256, run_ts`閵?

### 4.2 閻㈢喐鍨?preds.jsonl閿涘牊婀伴崷?HF 濡€崇€烽敍?
閼存碍婀伴敍姝歰ps/regression/router/generate_router_preds_hf.py`
娓氭繆绂嗛敍鍫濆讲闁绱氶敍姝歱ip install -r requirements-hf.txt`
```bash
conda run -n cline_env python ops/regression/router/generate_router_preds_hf.py \
  --in data/sft/router_sft_messages_...val.jsonl \
  --out tmp/preds.jsonl \
  --model-path <hf_model_path_or_name> \
  --max-items 2 --device cpu
```
濮ｅ繑娼拋鏉跨秿娴兼岸妾敮?`meta`閿涙瓪hf_model_id, prompt_format, source_val_path/source_val_sha256, run_ts, seed, do_sample, temperature`閵?
HF preds 娴兼艾鐨?`raw_text` 鐟欏嫯瀵栭崠鏍﹁礋妫ｆ牔閲?JSON 鐎电钖勯惃?compact 瑜般垹绱￠敍鍫ｅ閺?JSON 閸掓瑤绻氶悾娆忓斧閺傚洦婀伴敍澶堚偓?

### 4.3 鐠囧嫭绁?
閼存碍婀伴敍姝歰ps/regression/router/eval_router_outputs.py`
```bash
conda run -n cline_env python ops/regression/router/eval_router_outputs.py --in tmp/preds.jsonl --out tmp/metrics.json
```
metrics.json 鐎涙顔岄敍鍫ｅΝ闁绱氶敍?
`valid_json_rate, used_default_plan_rate, l2_trunc_rate, avg_filtered_agents, mode_dist, l2_len_dist, l3_len_dist, meta`
閸欘垶鈧绱癭--val-messages <val.jsonl>` 娴犮儴藟姒?`val_messages_*` 閸忓啩淇婇幁顖樷偓?

### 4.4 閸欘垰娲栬ぐ鎺曠槑濞村绱檓eta 鐎靛綊缍堥敍?
- 鐠囧嫭绁撮崜宥呭帥閺嶇顕?`metrics.json.meta`閿涙瓪git_commit`, `preds_path/preds_sha256`, `catalog_*`, `val_messages_*`閵?
- `preds.jsonl` 濮ｅ繗顢戦崠鍛儓 `meta`閿涘牊膩閸?閹绘劗銇氶弽鐓庣础/val 濠ф劒淇婇幁?閺冨爼妫块幋绛圭礆閿涘瞼鏁ゆ禍搴ゆ嫹濠ь垳鏁撻幋鎰蒋娴犺翰鈧?
- 鐎佃鐦?baseline/鐠侇厾绮岄崥搴ｇ波閺嬫粍妞傞敍灞界安閸忓牏鈥樼拋?`meta` 娑撯偓閼疯揪绱濋崘宥嗙槷鏉堝啰绮虹拋鈩冨瘹閺嶅洢鈧?

## 5) 閸忔娊鏁悳顖氼暔閸欐﹢鍣洪敍鍫ｎ嚢閸欐牔缍呯純顕嗙礆
- `Context`閿涘潉src/react_agent/context.py`閿涘绱癭MODEL`, `SYSTEM_PROMPT`, `RUN_ID` 缁涘鈧俺绻冪€涙顔岄崥宥呫亣閸愭瑨顕伴崣?env閵?
- Router 濡€崇€烽崣顖滃缁斿鍘ょ純顕嗙窗`ROUTER_MODEL`閿涘潷rovider/model閿涘本婀拋鍓х枂閸掓瑥娲栭拃钘夊煂 `MODEL`閿涘鈧?
- Router 閸欘垶鈧绗撻悽?OpenAI endpoint閿涙瓪ROUTER_OPENAI_BASE_URL` / `ROUTER_OPENAI_API_KEY`閿涘牊婀拋鍓х枂閸掓瑤濞囬悽銊ュ弿鐏炩偓 OpenAI_BASE_URL/OPENAI_API_KEY閿涙稖瀚?Router 娑撴挾鏁?endpoint 鐠嬪啰鏁ゆ径杈Е閿涘奔绱伴懛顏勫З閸ョ偠鎯ら崚鏉垮弿鐏炩偓閸愬秷鐦稉鈧▎鈽呯礆閵?
- OpenAI 閸忕厧顔?provider閿涘牆顩?Cerebras閿涘绱癭OPENAI_BASE_URL=https://api.cerebras.ai/v1`閿涘苯鑻熺拋鍓х枂 `MODEL=gpt-oss-120b`閿涘牊鍨ㄩ崗铚傜秼濡€崇€烽崥宥忕礆閵嗕精PI key 娴兼ê鍘涙担璺ㄦ暏 `OPENAI_API_KEY`閿涙稐绡冮崣顖欏▏閻?`CEREBRAS_API_KEY` 娴ｆ粈璐熼崙顓熷祦閺夈儲绨敍鍫滅瑢 .env 鐎靛綊缍堥敍澶堚偓?

缁€杞扮伐閿涘湩outer 閸楁洜瀚挧鐗堟拱閸?vLLM閿涘苯鍙炬担?agents 鐠ф澘鍙忕仦鈧?provider閿涘绱?
```bash
OPENAI_BASE_URL=https://api.cerebras.ai/v1
OPENAI_API_KEY=token-abc123
ROUTER_OPENAI_BASE_URL=http://127.0.0.1:18000/v1
ROUTER_OPENAI_API_KEY=token-abc123
ROUTER_MODEL=openai/router
MODEL=deepseek/deepseek-chat
```
- `run_logger`閿涘潉src/react_agent/run_logger.py`閿涘绱癭LOCAL_TRACE`, `LOG_DIR`, `TRACE_MAX_CHARS`閵嗕繖LOCAL_TRACE=1` 閹靛秳绱伴崘?JSONL閿涙盯绮拋銈堢翻閸戝搫鍩?`log/YYYYMMDD/`閿涘苯褰查悽?`LOG_DIR` 鐟曞棛娲婄捄顖氱窞閿涙矖TRACE_MAX_CHARS` 閹貉冨煑鐎涙顔岄幋顏呮焽闂€鍨閿涘牓绮拋?4000閿涘绱濋獮鏈电窗閼奉亜濮╅崜鏃堟珟閺佸繑鍔呴柨顕嗙礄token/secret/password閿涘鈧?
- `graph`閿涘潉src/react_agent/graph.py`閿涘绱癭ENABLE_BUILTIN_AGENTS`, `INCLUDE_DISABLED_AGENTS`閵?
- `tools`閿涘潉src/react_agent/tools.py`閿涘绱癭TAVILY_API_KEY`閿涘湵avilySearchResults閿涘鈧?

## 6) 閸ョ偛缍?妤犲矁鐦夐崨鎴掓姢
```bash
conda run --no-capture-output -n cline_env python -m pytest tests/unit_tests/
conda run --no-capture-output -n cline_env python -m pytest tests/integration_tests/
```

## 7) Phase 3 閸ョ偛缍婃灞炬暪閿涘牐鐦庡ù瀣，缁備緤绱?

鐎电懓鎮撴稉鈧?val_messages 鏉╃偠绐囨稉銈嗩偧 preds->eval閿涘苯鑻熺€佃鐦?`metrics.json.meta` 閻ㄥ嫬鍙ч柨顔肩摟濞堝吀绔撮懛瀛樷偓褋鈧?

```bash
conda run -n cline_env python ops/regression/router/run_regression_eval.py \
  --val-messages data/sft/router_sft_messages_...val.jsonl \
  --mode provider \
  --model deepseek/deepseek-chat \
  --out-dir tmp/regression_eval
```

閸掋倕鐣剧憴鍕灟閿?
- `--gate-mode repro`閿涘牓绮拋銈忕礆閿涙氨鏁ゆ禍搴㈡拱閸?HF閵嗕辜emperature=0閿涘矁顩﹀Ч鍌氱暚閸忋劌顦查悳甯幢濮ｆ棁绶?`preds_content_sha256`閿涘牏菙鐎规艾鍞寸€圭懓鎼辩敮宀嬬礆楠炲墎婀?`meta_match` 娑?`diff_keys`閵?
- `--gate-mode condition`閿涙氨鏁ゆ禍?provider 閹存牕鍘戠拋鎼佹閺堝搫婧€閺咁垽绱濊箛鐣屾殣 `preds_sha256`閿涙稓婀?`hard_match` 娑?`soft_mismatch_keys`閵?

HF 閸欘垰顦查悳鐗堝腹閼芥劕鎳℃禒銈忕礄CPU閿涘绱?
```bash
conda run -n cline_env python ops/regression/router/run_regression_eval.py \
  --val-messages data/sft/router_sft_messages_...val.jsonl \
  --mode hf \
  --hf-model-path <hf_model_path_or_name> \
  --device cpu \
  --temperature 0 \
  --seed 42 \
  --gate-mode repro \
  --out-dir tmp/regression_eval
```

## 8) 缂冩垹绮舵稉搴℃倱濮濄儻绱橝utoDL 鎼存梹鈧儲鏌熷鍫礆
閻滄媽钖勯敍鍦搖toDL 閺冦儱绻旈敍澶涚窗`github.com:443` 鐢瓕绉撮弮璁圭幢`api.github.com` 閸欘垵顔栭梻顔衡偓?

### 8.1 GitHub Contents API閿涘牆宕熼弬鍥︽鐟曞棛娲婇敍?
闁倸鎮庤箛顐︹偓鐔锋倱濮?`tools/*.py` / `docs/*.md`閿?
```bash
# 娓氬绱版稉瀣祰 docs/SYSTEM_MAP.md
curl -L \
  "https://api.github.com/repos/leephenix565/langgraph-my-agent/contents/docs/SYSTEM_MAP.md?ref=data/router-sft-v1" \
  | python - <<'PY'
import sys, json, base64
obj = json.load(sys.stdin)
print(base64.b64decode(obj["content"]).decode("utf-8"), end="")
PY
```

### 8.2 GitHub tarball閿涘牊鏆ｉ崚鍡樻暜韫囶偆鍙庨敍?
```bash
curl -L -o repo.tgz \
  "https://api.github.com/repos/leephenix565/langgraph-my-agent/tarball/data/router-sft-v1"
mkdir -p /tmp/repo_sync
tar -xzf repo.tgz -C /tmp/repo_sync --strip-components=1

# 閸欘亣顩惄鏍﹀敩閻?閺傚洦銆傞敍宀勪缉閸忓秵钖勯弻鎾规珓閹风喓骞嗘晶鍐х瑢閺佺増宓?
rsync -av --delete \
  --exclude ".git" --exclude ".venv" --exclude "data" \
  /tmp/repo_sync/ /root/autodl-tmp/work/my-agent/
```


