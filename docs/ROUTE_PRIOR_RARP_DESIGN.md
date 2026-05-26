# RARP Design: Reliability-Aware Route Prior

> Status: design/archive reference only. As of AC-1B-1, offline RP/RARP/SFT/manual-gold/teacher-proxy evidence is archived and non-mainline. As of AC-1B-2A, `react_agent.graph` no longer imports or executes the old RP-1A/RP-2C route-prior runtime seam. This document does not define current Agent Catalog v2 acceptance evidence.

## 1. Summary

Reliability-Aware Route Prior, abbreviated RARP, was the planned evolution of the historical RP-1A embedding-first route-prior shadow seam into a measurable, explainable, calibratable, and reversible reliability-aware routing prior layer. Current graph runtime no longer runs that seam; any future `router_prior_v2` must be rebuilt from stable Agent Catalog v2 metadata, new profile cards, and new manual labels.

RARP is not a replacement Router. It does not make embedding scores directly decide final agent selection. The target architecture is:

```text
Embedding route prior
  -> reliability-aware route cards
  -> Formal Router remains owner of layer_plan/layer_mode
  -> post-router deterministic comparison
  -> offline eval / metrics / artifact feedback loop
```

The first implementation phase is RP-2 Reliability-Aware Shadow Routing. RP-2 must not change Router prompt behavior by default, parser behavior, committed `layer_plan/layer_mode`, State schema, manager dispatch, public API, public workflow, or `/api/health`.

## 2. Existing Project Context

The current repository is a LangGraph layered multi-agent runtime with a Python public adapter and a single-assistant React frontend.

Current runtime entry:

```text
langgraph.json -> src/react_agent/graph.py:graph
```

Current public product path:

```text
apps/web
  -> /api/*
  -> src/react_agent/public_api.py
  -> src/react_agent/public_runtime.py
  -> src/react_agent.graph.get_graph_for_invoke(...)
```

Current graph mainline:

```text
__start__ -> router
router -> manager_broadcast
router -> baseline_sidecar
agent nodes -> manager_summary
manager_summary/finalize_summary
  -> fusion_gate
  -> fusion_judge_shadow
  -> fusion_writer_shadow
  -> final_emit
  -> memory_update or __end__
```

`mainline_emit` still exists as a compatibility wrapper, but current routing targets `final_emit`.

The current phase posture is `Phase F3 + QS-2`: hardening and quality closure, not public product expansion. `docs/SYSTEM_MAP.md` remains the S0 operational source, `docs/CHANGELOG.md` remains the S0 phase/change record, and `scripts/quality/run_quality.py` remains the repo-level quality command truth.

## 3. Motivation

The current Router is a prompt-based LLM Router. It outputs a four-layer plan:

```json
{
  "layers": [
    {"layer": "L1", "mode": "Chain", "selected": ["..."]},
    {"layer": "L2", "mode": "Star", "selected": ["..."]},
    {"layer": "L3", "mode": "Star", "selected": ["..."]},
    {"layer": "L4", "mode": "Chain", "selected": ["..."]}
  ],
  "reason": "why you chose the subset per layer and mode"
}
```

The current Router prompt sees a layer-to-agent-id catalog, not rich metadata, profile cards, or historical reliability. That creates several reliability risks:

- Router domain judgment depends mostly on prompt wording and agent ids.
- Router has no historical reliability signal for similar tasks.
- Router does not expose a calibrated uncertainty signal.
- A missed critical agent is hard to recover downstream.
- Replacing Router selection with embedding top-k would introduce high-confidence false negatives.

RARP therefore adds an internal second opinion around Router:

```text
Before Router:
  generate semantic and reliability prior

After Router:
  compare Router selections with high-confidence prior signals

Offline:
  measure when prior, Router, or fail-open behavior is reliable
```

## 4. Existing Foundations

### 4.1 Historical RP-1A Runtime Seam

RP-1A previously existed as an internal embedding-first semantic retrieval seam inside `router_node`, before the formal Router model invoke. AC-1B-2A removed this runtime wiring from `react_agent.graph`. The source remains as archived/offline helper code only.

RP-1A is shadow-only:

- no Router prompt change
- no parser change
- no committed State expansion
- no public workflow/API/health expansion
- fail-open when disabled or broken
- trace-only through local observability

Core current behavior:

```text
build_route_profile_registry(metadata_by_id)
retrieve_semantic_matches(question, profiles)
rank matches
classify confidence band
low-confidence fallback to full ordinary pool
select ranked shortlist
apply wildcard guardrail
return route_scores / awake_agents / routing_hint / ordinary_pool / wildcard_agents
```

Current RP-1A shortlist parameters:

```text
NORMAL_BASE_SHORTLIST = 6
NORMAL_SHORTLIST_CAP = 8
WIDE_BASE_SHORTLIST = 8
WIDE_SHORTLIST_CAP = 10
WILDCARD_KEEP_MIN = 1
WILDCARD_KEEP_MAX = 2
SHORTLIST_TIE_EPSILON = 0.02
LOW_CONFIDENCE_MARGIN = 0.03
WIDE_SCORE_BAND = 0.05
```

### 4.2 RP-1B Offline Eval Harness

RP-1B already exists under:

```text
ops/regression/route_prior/
```

It evaluates RP-1A shadow outputs against labeled JSONL and reports:

- top-k match
- expected-agent recall at top 5
- shortlist recall
- low-confidence fallback rate
- formal Router overlap observation
- wildcard retention
- false-negative examples

It is optional and non-blocking. DeepSeek teacher-proxy labels are explicitly proxy-only, not human/manual gold, and keep `quality_conclusion_allowed=false`.

## 5. Design Principles

### 5.1 Router Remains Formal Owner

Formal Router continues to own:

```text
layer_plan
layer_mode
current_layer
```

Those committed routing outputs continue to come from `router_parse.parse_router_layers_with_stats(...)`. RP-2 only creates offline scoring, shadow route cards, trace/eval artifacts, and post-router comparison.

RP-2 does not mutate:

```text
layer_plan
State schema
manager dispatch
public workflow
```

### 5.2 Embedding Does Not Perform Irreversible Deletion

Embedding retrieval may rank, compress, and classify candidates, but it must not remove valid agents from the formal Router catalog.

The formal Router catalog and ordinary route-prior pool are different universes:

- formal Router catalog: enabled L1-L4 ids, including `a01_cio_orchestrator` and `a25_report_center`, excluding disabled `a02_task_router`
- ordinary route-prior pool: enabled L2/L3 ordinary agents, excluding `a01_cio_orchestrator`, `a02_task_router`, and `a25_report_center`

RARP may score ordinary L2/L3 agents. It must not replace the formal Router catalog.

### 5.3 Public Surface Does Not Expand

RARP data must not enter:

```text
PublicTurn
WorkflowModel
AgentCatalogResponse
HealthResponse
StreamEvent
public store
frontend workflow panel
frontend agents page
```

The public transcript remains `user/assistant` only. `state["messages"]` remains an internal bus. `turn.text` remains the public/store/replay canonical truth.

### 5.4 No Second LLM Router Call

RARP first versions must keep runtime hot path to:

```text
embedding retrieval
+ deterministic scoring
+ existing Router
```

No LLM reranker, second Router, or judge call is part of RP-2 or RP-3A.

### 5.5 Teacher-Proxy Is Not Gold Truth

DeepSeek teacher-generated labels can support proxy diagnostics only. Manual/gold labels are required for quality conclusions and promotion gates.

## 6. Phase Roadmap

### RARP-0: Design Audit

Status: complete.

Completed audit areas:

```text
RP-1B eval schema / metrics / artifact / CLI
Router prompt / parser / committed State / public boundary
route profile registry / ordinary pool / public catalog / teacher-proxy catalog
tests / docs / trace-artifact / quality gate
```

### RP-2A: Eval Schema and Metrics Expansion

Implementation status:

- implemented as offline eval/tooling only
- code-backed in `ops/regression/route_prior/run_route_prior_eval.py` and `ops/regression/route_prior/eval_route_prior_outputs.py`
- archived offline coverage in `tests/archive/route_prior/test_route_prior_eval_rp2.py`
- no runtime graph, Router prompt/parser, State, manager dispatch, public API, public workflow, `/api/health`, frontend, or mainline quality-gate change

Scope:

- offline only
- no runtime behavior change
- no Router prompt change
- no State/public change
- support `route_eval_label_v0`
- preserve legacy RP-1B schema compatibility
- add safe/effective recall and calibration-oriented metrics

### RP-2B: Profile Cards and Reliability Scorer

Implementation status:

- implemented as offline-first tooling/helpers
- code-backed in `src/react_agent/route_profile_registry.py`, `src/react_agent/route_reliability.py`, and optional `run_route_prior_eval --enable-rarp-scoring`
- archived helper coverage in `tests/archive/route_prior/test_route_profile_registry_rp2.py` and `tests/archive/route_prior/test_route_reliability_rp2.py`; current default unit coverage uses the no-route-prior runtime contract test
- no runtime graph, Router prompt/parser, State, manager dispatch, public API, public workflow, `/api/agents`, `/api/health`, frontend, or mainline quality-gate change
- no RP-3 advisory or RP-4 repair

Scope:

- offline first
- optional profile cards
- missing-card fallback
- optional reliability table
- cold-start safe deterministic scoring
- no Router prompt change

### RP-2C: Historical Runtime Shadow Trace and Post-Router Comparison

Implementation status:

- historically implemented as env-gated runtime trace/comparison only
- AC-1B-2A removed the `src/react_agent/graph.py` runtime import/call sites
- archived helper coverage lives under `tests/archive/route_prior/`
- the current graph runtime does not read `ROUTE_PRIOR_RELIABILITY_ENABLED`
- no Router prompt/parser, committed routing output, State, manager dispatch, public API, public workflow, `/api/agents`, `/api/health`, frontend, advisory, repair, or mainline quality-gate behavior remains from this seam

Scope:

- env-gated
- trace/eval only
- no `layer_plan` mutation
- no State mutation
- no public surface expansion

### RP-3A: Score-Informed Router Advisory

Scope:

- disabled by default
- compact non-binding prompt block
- Router output schema unchanged
- parser allowed catalog unchanged
- no post-parse repair

### RP-4: Guarded Deterministic Repair

Future only. Not part of RP-2 or RP-3A.

## 7. Agent Universes

| Catalog | Purpose | Scope | Public | RARP may narrow it |
| --- | --- | --- | --- | --- |
| Formal Router catalog | Router legal selection universe | enabled L1-L4 ids | no | no |
| Ordinary route-prior pool | semantic/reliability scoring | enabled L2/L3 ordinary ids | no | scoring only |
| Public `/api/agents` catalog | frontend read-only explanation | metadata by layer | yes | no |

### 7.1 Formal Router Catalog

Source:

```text
graph_bootstrap.build_agent_catalog(layer_order)
  -> agents_by_layer(layer)
```

Facts:

- includes L1/L2/L3/L4
- includes enabled agents only
- includes `a01_cio_orchestrator`
- includes `a25_report_center`
- excludes disabled `a02_task_router`
- gives Router ids only, not rich profile text

### 7.2 Ordinary Route-Prior Pool

Source:

```text
route_profile_registry.build_route_profile_registry(metadata_by_id)
```

Rules:

```python
ORDINARY_LAYERS = ("L2", "L3")
ORDINARY_EXCLUDED = {
    "a01_cio_orchestrator",
    "a02_task_router",
    "a25_report_center",
}
```

Ordinary agent test:

```text
meta.default_enabled == True
layer in L2/L3
agent_id not in ORDINARY_EXCLUDED
```

### 7.3 Public `/api/agents` Catalog

Source:

```text
public_api._build_agent_catalog_response()
```

Public fields:

```text
id
name
description
capabilities
layer
team
roleType
defaultEnabled
```

Not public fields:

```text
profile_text
wildcard
cost_tiebreak
route_score
ordinary flag
advisory
reliability score
```

## 8. Route Profile Cards

Current `RouteProfile.profile_text` is derived from:

```text
description
capabilities
input_type
team
```

Fallback is `agent_id`. Existing code supports `_REGISTRY_OVERRIDES`; current override usage is primarily wildcard handling for `a15_entity_relation_extraction`.

RP-2 may introduce optional internal profile cards:

```text
config/route_profiles/<agent_id>.json
```

Example schema:

```json
{
  "schema_version": "route_profile_card_v0",
  "agent_id": "a21_reg_compliance",
  "positive_examples": [
    "评估监管政策变化对行业准入、披露义务或处罚风险的影响"
  ],
  "negative_examples": [
    "纯技术面交易信号不优先路由到该 agent"
  ],
  "when_to_use": [
    "问题涉及监管、合规、披露、处罚、牌照、政策约束"
  ],
  "when_not_to_use": [
    "问题只涉及价格趋势、技术指标或组合权重优化"
  ],
  "evidence_expectations": [
    "监管公告",
    "政策原文",
    "交易所披露规则",
    "处罚案例"
  ],
  "common_misroutes": [
    "把所有风险问题都误路由给合规 agent"
  ],
  "routing_keywords": [
    "监管",
    "合规",
    "披露",
    "处罚"
  ],
  "risk_tags": ["regulatory", "compliance"],
  "profile_version": "2026-04-rp2"
}
```

Profile cards are internal routing material. They are not public metadata, not `AgentMetadata` replacements, not `AGENT_TOOLS` replacements, and not agent execution implementations.

Behavior boundaries:

```text
missing card:
  fallback to metadata-derived profile_text

invalid card:
  offline artifact records invalid count
  runtime shadow fail-open

card agent_id not ordinary:
  ignore and record

internal negative_examples/common_misroutes:
  never expose through /api/agents
```

## 9. Reliability Table

Reliability table purpose:

```text
represent whether an agent has historically been reliable for a task class,
how stable that reliability is,
and whether sample size is sufficient.
```

Example schema:

```json
{
  "schema_version": "route_reliability_table_v0",
  "generated_at": "2026-04-28T00:00:00Z",
  "catalog_version": "agent-catalog-hash",
  "label_sets": [
    {
      "path": "ops/regression/route_prior/fixtures/rp2_manual_gold_100.jsonl",
      "label_source": "manual_gold",
      "count": 100
    }
  ],
  "global": {
    "a21_reg_compliance": {
      "trials": 42,
      "successes": 35,
      "false_positives": 8,
      "historical_reliability": 0.79,
      "uncertainty": 0.14
    }
  },
  "by_task_type": {
    "regulatory_compliance": {
      "a21_reg_compliance": {
        "trials": 18,
        "successes": 16,
        "historical_reliability": 0.85,
        "uncertainty": 0.21
      }
    }
  }
}
```

Cold-start defaults:

```text
historical_reliability = 0.50
historical_uncertainty = 1.00
```

Bayesian smoothing:

```text
reliability = (success + alpha) / (trials + alpha + beta)
uncertainty = 1 / sqrt(trials + alpha + beta)
alpha = 2
beta = 2
```

Label-source policy:

```text
manual_gold:
  can support quality conclusion

deepseek_teacher_v1:
  proxy diagnostic only

draft_for_human_review:
  not final quality evidence
```

## 10. Reliability Scoring

Inputs:

```text
question
RP-1A route_scores
ordinary_pool
wildcard_agents
profile_cards
reliability_table
agent metadata
optional task_type
```

Outputs:

```text
route reliability cards
confidence band
groups:
  strongly_recommended
  candidate
  wildcard
  deprioritized
post-router comparison input
eval artifacts
```

RP-2 v0 combined score:

```text
combined_route_score =
  0.45 * semantic_relevance
+ 0.20 * profile_match
+ 0.20 * historical_reliability
+ 0.05 * query_type_prior
+ 0.05 * wildcard_bonus
- 0.10 * historical_uncertainty
- 0.05 * cost_penalty
```

First-version simplification:

```text
profile_match = semantic_relevance
query_type_prior = 0.50
wildcard_bonus = 0.00
```

Cost penalty:

```text
low     -> 0.0
normal  -> 0.5
medium  -> 0.5
high    -> 1.0
unknown -> 0.5
```

Score band:

```text
high:
  combined >= 0.75

medium:
  0.55 <= combined < 0.75

low:
  combined < 0.55
```

Priority group:

```text
strong:
  combined >= 0.75
  historical_uncertainty <= 0.35
  not low_confidence_fallback

candidate:
  combined >= 0.55

deprioritized:
  combined >= 0.35

hidden:
  combined < 0.35
```

Wildcard should continue to rely on guardrail retention rather than a large score boost.

## 11. Confidence Bands

RARP confidence band is a per-turn route-prior confidence, not a single-agent score.

Low:

```text
embedding disabled
backend error
empty ordinary pool
top1-top2 margin < 0.03
top1 combined score < 0.55
top agents historical uncertainty too high
```

Behavior:

```text
fail-open to full ordinary pool
safe_recall counts coverage
effective_recall does not count this as precise route success
```

Wide:

```text
top1-top5 scores close
multiple candidate clusters close
many medium candidates
```

Behavior:

```text
larger shortlist
preserve wildcard
```

Normal:

```text
top cluster reasonably clear
compact shortlist
normal route cards
```

High:

```text
top1 combined >= 0.75
top1-top2 margin >= 0.10
top strong candidates uncertainty <= 0.35
```

Behavior:

```text
strong route cards
eligible for future advisory
not eligible for RP-4 repair until manual-gold gates prove benefit
```

## 12. Route Reliability Shadow Schema

Internal route card:

```json
{
  "agent_id": "a11_index_technical_analysis",
  "priority": "strong",
  "score_band": "high",
  "combined_route_score": 0.78,
  "semantic_relevance": 0.84,
  "profile_match": 0.84,
  "historical_reliability": 0.72,
  "historical_uncertainty": 0.18,
  "cost_penalty": 0.5,
  "wildcard_flag": false,
  "reason_codes": [
    "semantic:high",
    "history:stable",
    "priority:strong"
  ],
  "selection_hint": "recommended"
}
```

Full shadow object:

```json
{
  "schema_version": "route_reliability_shadow_v0",
  "algorithm": "rarp_v0",
  "shadow_only": true,
  "confidence_band": "normal",
  "low_confidence_fallback": false,
  "ordinary_pool_size": 22,
  "cards": [],
  "groups": {
    "strongly_recommended": ["a03_macro_industry_research", "a11_index_technical_analysis"],
    "candidate": ["a09_company_sentiment_radar"],
    "wildcard": ["a15_entity_relation_extraction"],
    "deprioritized": ["a23_portfolio_opt"]
  }
}
```

No-leak rule:

Allowed:

```text
agent_id
score band
numeric score
reason code
short routing tag
```

Not allowed by default:

```text
raw embeddings
full profile_text
raw prompt
API key
hidden state
```

## 13. Eval Label Schema

Legacy RP-1B records use:

```text
id
question
expected_agents
tags
label_source
formal_router_selected
notes
```

RP-2 must preserve compatibility.

New RP-2 schema:

```json
{
  "schema_version": "route_eval_label_v0",
  "id": "rp2-manual-0001",
  "question": "如果美联储转鸽，对美国银行股、美元指数和黄金分别有什么影响？",
  "language": "zh",
  "task_type": "macro_rates_fx_sector",
  "difficulty": "multi_domain",
  "risk_level": "medium",
  "label_source": "manual_gold",
  "quality_conclusion_allowed": true,
  "review_status": "reviewed",
  "must_include_agents": [
    "a03_macro_industry_research",
    "a11_index_technical_analysis",
    "a09_company_sentiment_radar"
  ],
  "critical_agents": [
    "a11_index_technical_analysis"
  ],
  "nice_to_have_agents": [
    "a15_entity_relation_extraction"
  ],
  "should_not_include_agents": [
    "a23_portfolio_opt"
  ],
  "expected_layers": {
    "L2": ["a03_macro_industry_research"],
    "L3": ["a11_index_technical_analysis", "a09_company_sentiment_radar"]
  },
  "primary_agent": "a03_macro_industry_research",
  "notes": "重点是宏观政策与利率/汇率/银行板块传导，不是组合优化。"
}
```

Validation rules:

```text
critical_agents subset of must_include_agents
must_include_agents intersection should_not_include_agents is empty
manual_gold can set quality_conclusion_allowed=true
deepseek_teacher_v1 must set quality_conclusion_allowed=false
draft_for_human_review cannot support final quality conclusion
legacy expected_agents maps to must_include_agents
ordinary-eval labels default to ordinary agent ids only
special roles such as a01 and a25 are not ordinary route-prior eval labels
```

## 14. Metrics

RP-2A writes `route_prior_metrics_v2` while keeping the legacy RP-1B metric fields compatible. The added metrics remain offline diagnostics and do not promote route-prior eval into the mainline quality gate.

Coverage metrics:

```text
expected_agent_recall@1
expected_agent_recall@3
expected_agent_recall@5
shortlist_recall
critical_agent_miss_rate
nice_to_have_recall
```

Safe vs effective recall:

```text
safe_recall:
  low-confidence full ordinary pool fallback counts as coverage

effective_recall:
  full ordinary pool fallback does not count as precise route success
```

Precision and noise metrics:

```text
precision_at_shortlist
f1_at_shortlist
jaccard_at_shortlist
negative_selection_rate
unnecessary_agent_rate
avg_shortlist_size
```

Cost metrics:

```text
avg_cost
normalized_avg_cost
recall_per_cost
cost_at_recall90
```

Cost mapping:

```text
low     = 1
normal  = 2
medium  = 2
high    = 3
unknown = 2
```

Calibration metrics:

```text
high_confidence_wrong_rate
ECE
Brier
```

Router comparison metrics:

```text
formal_router_overlap
router_miss_prior_hit
prior_miss_router_hit
both_miss
omitted_strong_recommended
selected_deprioritized
```

Safety metrics:

```text
special_agent_leakage
unknown_agent_id_count
wildcard_retention_rate
fallback_reason_distribution
raw_embedding_leak_count
profile_text_leak_count
```

## 15. Run Artifact Schema

RP-2 run record target:

```json
{
  "schema_version": "route_prior_run_v2",
  "id": "rp2-manual-0001",
  "question_hash": "sha256:...",
  "question_preview": "如果美联储突然转鸽...",
  "question": "optional-local-debug-only",
  "label_source": "manual_gold",
  "quality_conclusion_allowed": true,
  "labels": {
    "must_include_agents": [],
    "critical_agents": [],
    "nice_to_have_agents": [],
    "should_not_include_agents": []
  },
  "route_prior": {
    "algorithm": "rarp_v0",
    "enabled": true,
    "retrieval_reason": "ok",
    "confidence_band": "normal",
    "low_confidence_fallback": false,
    "ordinary_pool_size": 22,
    "shortlist": [],
    "ranked_agents": [],
    "reliability_cards": []
  },
  "formal_router": {
    "source": "label_provided | prediction_artifact | live_optional | unavailable",
    "parse_ok": null,
    "used_default_plan": null,
    "ordinary_selected_agents": []
  },
  "case_metrics": {
    "recall_at_5": 0.8,
    "safe_shortlist_recall": 1.0,
    "effective_shortlist_recall": 0.75,
    "critical_miss": false,
    "negative_selection_rate": 0.0,
    "shortlist_cost": 8.0
  }
}
```

Artifact privacy policy:

Default:

```text
question_hash
question_preview
```

Optional local/debug:

```text
full raw question
```

Never:

```text
raw embeddings
full profile_text by default
API keys
hidden prompts
```

## 16. Post-Router Comparison

Function contract:

```python
compare_route_prior_to_router(
    reliability_shadow: dict,
    layer_plan: dict[str, list[str]],
) -> dict
```

Output schema:

```json
{
  "schema_version": "route_prior_router_comparison_v0",
  "prior_confidence_band": "normal",
  "router_overlap": 0.67,
  "prior_only_agents": ["a09_company_sentiment_radar"],
  "router_only_agents": ["a21_reg_compliance"],
  "omitted_strong_recommended": [],
  "selected_deprioritized": ["a23_portfolio_opt"],
  "disagreement_band": "medium",
  "reason_codes": [
    "overlap:medium",
    "selected_deprioritized:1"
  ]
}
```

RP-2 behavior:

```text
trace/eval only
no layer_plan mutation
no State mutation
no manager dispatch mutation
no public workflow mutation
```

The runtime RP-2C comparison helper is label-free. Label-dependent miss metrics remain part of offline eval artifacts rather than runtime trace.

## 17. Future RP-3 Router Advisory

This section describes future runtime Router advisory design only. Current RP-3A work in this repository is offline/ops experimentation and evidence; it does not implement runtime advisory, `ROUTE_PRIOR_ADVISORY_MODE`, Router prompt mutation, parser changes, State changes, public surface changes, or quality-gate promotion.

RP-3 may later give Router a compact, non-binding advisory block. It does not replace Router, alter the output schema, or narrow the parser allowed catalog.

Env:

```text
ROUTE_PRIOR_ADVISORY_MODE=off | shadow | prompt
default = off
```

Natural insertion point:

```text
router_node
  after route prior computation
  before model invoke
```

Prompt size limits:

```text
max_strong = 4
max_candidate = 4
max_wildcard = 2
deprioritized = ids/count only
```

Non-negotiable parser boundary:

```text
do not change parse_router_layers_with_stats(raw_text, agent_catalog)
do not make parser depend on route prior
Router output schema remains current JSON schema
```

### 17.1 RP-3A-0D Router Advisory Experiment Design

Status: design checkpoint only. RP-3 Router advisory is not implemented.

Current readiness facts from the RP-3R/RP-3A-0 audit at the time of RP-3A-0D:

```text
readiness = partial
manual/manual_gold records = 0
quality_conclusion_allowed=true records = 0
high_confidence_wrong_rate / ECE / Brier = no effective sample evidence
prompt A/B dry-run harness = not implemented
token/latency artifact = not available
ROUTE_PRIOR_ADVISORY_MODE = design fact only, not runtime code fact
```

RP-3G-Gold-Import later lands `ops/regression/route_prior/fixtures/rp3_manual_gold_20.jsonl`
as a 20-case GPT Pro assisted, project-owner accepted `manual_gold` smoke fixture.
That updates smoke-data availability only. It does not provide the 100-case initial
gate, the 300-case promotion gate, prompt A/B parse-fallback evidence, token/latency
evidence, or a code-backed `ROUTE_PRIOR_ADVISORY_MODE`.

This means RP-3A prompt advisory must not be implemented directly from the
current tree. RP-3A-1 lands the first offline, network-free prompt A/B dry-run
harness for parser-stability and selected-agent-delta evidence, but it still
does not implement runtime prompt injection.

Offline prompt A/B harness design:

```text
implemented RP-3A-1 command:
  python -m ops.regression.route_prior.run_router_advisory_ab \
    --dataset ops/regression/route_prior/fixtures/rp3_manual_gold_20.jsonl \
    --out-dir ops/regression/route_prior/out \
    --max-items 20 \
    --mode network-free

input:
  route_eval_label_v0 JSONL, preferably manual_gold
  legacy RP-1B expected_agents records may be normalized for compatibility
  optional route_reliability_shadow_v0 records from RP-2B/RP-2C artifacts
  optional Router prediction artifact JSONL:
    preferred schema_version = router_advisory_prediction_v0
    baseline/advisory side objects carry raw output plus side metadata
    legacy baseline_raw / advisory_raw keys remain supported

baseline:
  current ROUTER_SYSTEM_PROMPT rendered with the current formal Router catalog
  no advisory block

advisory:
  same Router prompt plus a compact non-binding advisory block
  advisory content must use compact safe fields only:
    confidence_band
    low_confidence_fallback
    strongly_recommended / candidate / wildcard / deprioritized ids
    score bands
    reason codes
  advisory content must not include:
    raw embeddings
    full profile_text
    full profile card text
    hidden prompts or secrets

parser:
  both A and B outputs must be parsed through
  parse_router_layers_with_stats(raw_text, agent_catalog)
  parser allowed catalog and output schema stay unchanged

RP-3A-2B prediction artifact schema hardening:
  implemented in the same offline harness
  supports legacy baseline_raw / advisory_raw JSONL predictions
  supports enriched baseline/advisory side objects with model/token/latency metadata
  does not call live models
  does not implement runtime Router advisory
  does not create promotion evidence by itself
```

Run artifact schema sketch:

```json
{
  "schema_version": "router_advisory_ab_run_v0",
  "mode": "network-free",
  "case_id": "...",
  "question_hash": "sha256:...",
  "question_preview": "...",
  "label_source": "manual_gold",
  "quality_conclusion_allowed": true,
  "baseline_prompt_chars": 0,
  "advisory_prompt_chars": 0,
  "prediction_schema_version": "router_advisory_prediction_v0",
  "baseline": {
    "raw": "...",
    "model_name": null,
    "model_spec": null,
    "prompt_chars": null,
    "token_count": null,
    "latency_ms": null,
    "prompt_hash": null,
    "catalog_hash": null,
    "parse_latency_ms": null,
    "parse_stats": {},
    "layer_plan": {},
    "layer_mode": {},
    "selected_agents": []
  },
  "advisory": {
    "raw": "...",
    "model_name": null,
    "model_spec": null,
    "prompt_chars": null,
    "token_count": null,
    "latency_ms": null,
    "prompt_hash": null,
    "catalog_hash": null,
    "parse_latency_ms": null,
    "parse_stats": {},
    "layer_plan": {},
    "layer_mode": {},
    "selected_agents": []
  },
  "comparison": {
    "parse_ok_delta": 0,
    "used_default_plan_delta": 0,
    "filtered_agents_delta": 0,
    "l2_truncated_delta": 0,
    "selected_jaccard": 0.0,
    "must_include_recall_delta": 0.0,
    "critical_agent_miss_delta": 0,
    "negative_selection_delta": 0,
    "prompt_char_delta": 0,
    "token_count_delta": null,
    "latency_ms_delta": null
  }
}
```

Enriched prediction JSONL schema accepted by RP-3A-2B:

```json
{
  "schema_version": "router_advisory_prediction_v0",
  "id": "case-id",
  "baseline": {
    "raw": "{\"layers\": []}",
    "model_name": "router-baseline-model",
    "model_spec": "provider/model",
    "prompt_chars": 1234,
    "token_count": 345,
    "latency_ms": 812.5,
    "prompt_hash": "sha256:...",
    "catalog_hash": "sha256:...",
    "parse_latency_ms": 2.1
  },
  "advisory": {
    "raw": "{\"layers\": []}",
    "model_name": "router-advisory-model",
    "model_spec": "provider/model",
    "prompt_chars": 1510,
    "token_count": 401,
    "latency_ms": 934.2,
    "prompt_hash": "sha256:...",
    "catalog_hash": "sha256:...",
    "parse_latency_ms": 2.4
  }
}
```

The harness persists only the side metadata above. It does not persist full
prompt bodies, raw embeddings, profile text, profile card text, secrets, or
provider credentials. Missing optional metadata is represented as `null`.
Summary artifacts aggregate average prompt/token/latency deltas and latency
p50/p90/p95 only when supplied prediction metadata is complete enough to do so.

Summary artifact schema additions from RP-3A-2B:

```json
{
  "avg_prompt_char_delta": 0.0,
  "avg_token_count_delta": null,
  "avg_latency_ms_delta": null,
  "latency_ms_delta_p50": null,
  "latency_ms_delta_p90": null,
  "latency_ms_delta_p95": null,
  "prediction_records_with_complete_prompt_char_metadata": 0,
  "prediction_records_with_complete_token_metadata": 0,
  "prediction_records_with_complete_latency_metadata": 0,
  "routing_quality_promotion_evidence": false
}
```

Prompt A/B comparison metrics:

```text
parse_ok_rate
used_default_plan_rate
filtered_agents_avg
l2_truncated_rate
selected_agents_delta_count
selected_jaccard_avg
shortlist_overlap_avg
must_include_recall
critical_agent_miss_rate
critical_agent_miss_delta
negative_selection_rate
avg_selected_agents
prompt_char_delta_avg/p95
prompt_token_delta_avg/p95
latency_ms_p50/p90/p95 when live model mode is used
```

Network-free mode:

```text
no provider calls
validate prompt rendering, artifact schema, parser replay, and static budget fields
may use stored Router prediction artifacts or deterministic fake outputs
RP-3A-2B enriched prediction replay improves metadata completeness observability only
cannot support model-behavior quality conclusions
RP-3A-1 deterministic stubs are label-derived parser smoke only, not routing quality evidence
```

RP-3A-3 optional-live prediction artifact generator:

```text
implemented command:
  python -m ops.regression.route_prior.generate_router_advisory_predictions \
    --dataset ops/regression/route_prior/fixtures/rp3_manual_gold_20.jsonl \
    --out ops/regression/route_prior/out/router_advisory_predictions.jsonl \
    --summary-out ops/regression/route_prior/out/router_advisory_predictions_summary.json \
    --max-items 20 \
    --mode dry-run

dry-run mode:
  default
  network-free
  writes schema-valid router_advisory_prediction_v0 JSONL
  uses deterministic label-derived Router JSON
  advisory_source = label_stub
  supports A/B replay wiring and artifact validation only

live mode:
  explicit opt-in via --mode live
  uses the configured Router model through the same provider/model utility pattern
  writes enriched baseline/advisory raw outputs and side metadata when provider calls succeed
  if required env is missing, writes status=skipped summary and exits 0
  if provider errors occur, writes status=error summary

RP-3A-5 advisory sources:
  advisory_source = label_stub | provided_artifact | rarp_shadow
  label_stub:
    label-derived smoke path only
  provided_artifact / rarp_shadow:
    read a local RP-2 route-prior / route-reliability JSONL artifact via --advisory-artifact
    key records by case id
    extract route_reliability_shadow_v0 cards/groups when present
    group advisory agent ids by formal Router layer
    record artifact path/hash, confidence band, fallback state, agent ids, reason codes,
      retrieval enabled/reason, case-found state, and missing reason
    mark missing/disabled/empty-card cases as provided_artifact_missing or rarp_shadow_missing
    set advisory_applied = false for no-advisory cases
    set advisory_noop_reason = noop_no_advisory for no-advisory cases
    do not render an advisory block for no-advisory cases
    never silently fall back to label-derived advisory
```

Prediction generator summary schema:

```json
{
  "schema_version": "router_advisory_predictions_summary_v0",
  "status": "ready | skipped | error",
  "mode": "dry-run | live",
  "case_count": 0,
  "generated_count": 0,
  "skipped_count": 0,
  "model_spec": "provider/model",
  "missing_env_reason": null,
  "error_message": null,
  "latency_ms_p50": null,
  "latency_ms_p90": null,
  "latency_ms_p95": null,
  "token_metadata_complete_count": 0,
  "advisory_source_counts": {"label_stub": 0},
  "advisory_applied_count": 0,
  "advisory_noop_count": 0,
  "advisory_missing_count": 0,
  "routing_quality_promotion_evidence": false
}
```

RP-3A-3 does not persist full prompt bodies, raw embeddings, profile text,
profile card text, secrets, or provider credentials. It does not modify runtime
Router prompt construction, parser behavior, State, public API, workflow,
frontend, manager dispatch, agent execution, or the quality gate. Dry-run and
optional-live prediction artifacts are still evidence inputs only; they are not
production promotion evidence by themselves.

RP-3A-4D label-stub layer-constraint hardening:

```text
implemented in the offline A/B harness and optional prediction generator only
addresses observed live-smoke regression:
  case_id = rp3-manual-gold-0004
  critical agent = a19_market_risk
  expected layer = L3
  baseline selected a19_market_risk in L3
  label_stub advisory live output placed a19_market_risk in L2
  parser correctly filtered the wrong-layer L2 selection

label_stub advisory now includes:
  must_include_agents_by_layer
  critical_agents_by_layer
  nice_to_have_agents_by_layer

layer grouping source order:
  1. label expected_layers
  2. formal Router catalog fallback

layer constraint:
  Only select each advisory agent in the layer where it is listed.
  Do not move L3 agents into L2 or L2 agents into L3.
  If uncertain, omit rather than selecting the agent in the wrong layer.
  Return only the existing Router JSON schema.
```

RP-3A-4D does not modify `ROUTER_SYSTEM_PROMPT`, parser behavior, graph runtime
routing, State schema, public contracts, workflow snapshots, `/api/agents`,
`/api/health`, frontend behavior, manager dispatch, agent execution, or quality
gates. It does not implement runtime advisory and does not make a 5-case
label-stub smoke result promotion evidence.

RP-3A-5 provided-artifact / RARP-shadow advisory-source experiment:

```text
implemented in the optional prediction generator only
adds:
  --advisory-source provided_artifact
  --advisory-source rarp_shadow
  --advisory-artifact <route_prior_runs.jsonl>

source material:
  RP-2 route-prior / route-reliability artifacts
  route_reliability_shadow_v0 cards and groups when present
  formal Router catalog for layer grouping

not source material:
  manual_gold must_include_agents
  manual_gold critical_agents
  manual_gold nice_to_have_agents

prediction metadata:
  advisory_source
  advisory_artifact_path
  advisory_artifact_hash
  advisory_applied
  advisory_status
  advisory_noop_reason
  advisory_case_found
  advisory_confidence_band
  advisory_low_confidence_fallback
  advisory_agent_ids
  advisory_reason_codes
  advisory_retrieval_enabled
  advisory_retrieval_reason
  advisory_missing_reason

missing / disabled / fallback behavior:
  missing artifact path:
    source = provided_artifact_missing | rarp_shadow_missing
    missing_reason = artifact_not_configured
  artifact exists but case missing:
    missing_reason = case_not_found
  case exists but reliability shadow missing:
    missing_reason = route_reliability_missing
  reliability cards empty:
    missing_reason = reliability_cards_empty
  retrieval disabled or low confidence:
    preserve retrieval enabled/reason and confidence/fallback metadata

RP-3A-5B noop fallback behavior:
  missing artifact path, missing case, missing reliability shadow, empty cards,
  disabled retrieval, and low-confidence fallback are no-advisory cases
  no-advisory cases:
    advisory_applied = false
    advisory_noop_reason = noop_no_advisory
    do not render a non-empty advisory prompt block
    do not make a second live advisory-side model call
    may copy baseline raw output and metadata to the advisory side for schema compatibility
  A/B replay:
    marks comparison mode as noop_no_advisory
    reports zero prompt/token/latency deltas for noop cases
    does not count noop side differences as advisory-induced critical regressions
  summary:
    advisory_applied_count
    advisory_noop_count
    advisory_missing_count
```

RP-3A-5 does not modify `ROUTER_SYSTEM_PROMPT`, parser behavior, graph runtime
routing, State schema, public contracts, workflow snapshots, `/api/agents`,
`/api/health`, frontend behavior, manager dispatch, agent execution, or quality
gates. It does not implement runtime Router advisory. `provided_artifact` /
`rarp_shadow` artifacts are experiment inputs only and are not promotion
evidence by themselves.

RP-3A-5B specifically addresses the disabled/fallback RP-2 artifact case where
all records had no reliability cards. That path is not RARP-card evidence. It is
treated as a noop/no-advisory experiment state so empty advisory text cannot
perturb a Router live smoke.

RP-3A-5E provided-artifact renderer hardening:

```text
trigger:
  real Qwen-backed RP-1A retrieval produced non-empty route-reliability cards
  provided_artifact DeepSeek live A/B on manual_gold_20 had no parse/default regressions
  but produced critical_miss_regressions=3

triage finding:
  the missed critical agents were present in route-prior ranking/cards
  renderer selected only wildcard a15_entity_relation_extraction when strong/candidate groups were empty
  parser filtering, wrong-layer placement, and label/comparison bugs were not the cause

renderer behavior:
  never treat wildcard-only advisory ids as clean applied provided_artifact signal
  when strong/candidate groups are empty:
    prefer top-ranked non-wildcard route-prior cards as weak non-binding candidates
    group weak fallback candidates by formal Router layer
    keep wildcard ids as secondary context only
  when no non-wildcard card exists:
    advisory_applied = false
    advisory_status = noop_wildcard_only
    no second live advisory call

artifact metadata:
  advisory_selection_reason = weak_non_wildcard_fallback | noop_wildcard_only | priority_groups
  advisory_secondary_agent_ids
  advisory_status may be provided_artifact_weak_non_wildcard_fallback
```

RP-3A-5E remains an offline experiment-harness hardening. It does not implement
runtime Router advisory, does not modify `ROUTER_SYSTEM_PROMPT`, parser behavior,
graph runtime routing, State schema, public contracts/workflow/API/health/frontend
surfaces, manager dispatch, agent execution, or quality gates. The manual_gold_20
rerun is smoke evidence only, not promotion evidence.

RP-3A-5F live stability and routing case report evidence:

```text
route-prior artifact:
  case_count: 20
  enabled_count: 20
  disabled_count: 0
  retrieval_reason_counts: {"ok": 20}
  cards_non_empty_count: 20
  confidence_band_counts: {"normal": 14, "low": 6}
  low_confidence_fallback_count: 6
  RARP top5 all-critical coverage: 13/20
  RARP top10 all-critical coverage: 18/20

three DeepSeek live provided_artifact reruns:
  run_count: 3
  total case replays: 60
  advisory source mix per run: provided_artifact=14, provided_artifact_low_confidence=6
  advisory_applied_count per run: 14
  advisory_noop_count per run: 6
  parse_ok_regressions_total: 0
  default_plan_regressions_total: 0
  critical_miss_regressions_total: 1
  avg_selected_jaccard_mean: 0.7508
  avg_token_count_delta_mean: 381.78
  avg_latency_ms_delta_mean: 436.38 ms

remaining risk:
  rp3-manual-gold-0017 had one stochastic critical miss in run 1.
  Baseline selected a19_market_risk and a20_fundamental_risk.
  Advisory selected a20_fundamental_risk but missed a19_market_risk.
  Runs 2 and 3 did not repeat that critical miss.

case-report artifacts:
  ops/regression/route_prior/out/rp3_routing_case_report.md
  ops/regression/route_prior/out/rp3_routing_case_table.json
```

RP-3A-5F confirms the offline provided-artifact experiment path can consume real
Qwen-backed RARP reliability cards and remain parse/default stable in a 3 x
20-case live smoke. It does not prove production routing quality, does not clear
runtime advisory promotion, and still leaves manual_gold_100 expansion plus
targeted monitoring of `rp3-manual-gold-0017` as the next evidence work.

RP-3A-5C-Embed-Audit local embedding service note:

```text
project-external endpoint:
  health: http://127.0.0.1:8001/healthz
  embeddings: http://127.0.0.1:8001/v1/embeddings
  model: Qwen/Qwen3-Embedding-0.6B
  embedding dimension: 1024
  serving implementation: FastAPI + SentenceTransformers wrapper outside repo

Historical RP-1A local env:
  ROUTE_PRIOR_EMBEDDINGS_ENABLED=1
  ROUTE_PRIOR_EMBEDDINGS_MODEL=Qwen/Qwen3-Embedding-0.6B
  ROUTE_PRIOR_OPENAI_BASE_URL=http://127.0.0.1:8001/v1
  ROUTE_PRIOR_OPENAI_API_KEY=local-test

latest checked service state:
  health ok on http://127.0.0.1:8001/healthz
  model reported by health: Qwen/Qwen3-Embedding-0.6B
  project-external local process; re-check health before each live experiment
  repo code unchanged

endpoint smoke:
  status=200
  count=2
  dims=[1024, 1024]

latest RP-3A-5F route-prior artifact:
  enabled_count=20
  disabled_count=0
  cards_non_empty_count=20

boundary:
  local service only
  no Router prompt/parser change
  no State/public/API/health/frontend expansion
  no runtime advisory
  fail-open if unavailable
```

Optional live mode:

```text
explicit opt-in only
writes ignored artifacts under ops/regression/route_prior/out/
records model, timestamp, prompt size, parse stats, and latency
remains optional and non-blocking until a future promotion decision
```

Manual-gold data requirements:

```text
smoke: 20 manual_gold cases
  validates harness wiring, artifact shape, and no-leak constraints only

initial gate: 100 manual_gold cases
  minimum evidence before RP-3A prompt-mode implementation can be accepted

promotion gate: 300 manual_gold cases
  stronger evidence before broader default availability or any repair work
```

Seed template path:

```text
ops/regression/route_prior/fixtures/rp3_manual_gold_seed_template.jsonl
```

The seed template is not manual gold evidence by itself. Its records remain
`draft_for_human_review` with `quality_conclusion_allowed=false` until a human
reviewer verifies the labels and explicitly changes them to `manual_gold` with
`quality_conclusion_allowed=true`.

Accepted smoke fixture path:

```text
ops/regression/route_prior/fixtures/rp3_manual_gold_20.jsonl
```

As of RP-3G-Gold-Import this file contains 20 reviewed `manual_gold` records
generated with GPT Pro expert assistance and accepted by the project owner. It
is a smoke dataset for prompt A/B dry-run wiring and schema validation only; it
is not the 100-case initial gate, the 300-case promotion gate, or routing-quality
promotion evidence by itself.

Required label fields:

```text
schema_version = route_eval_label_v0
question
label_source = manual_gold
quality_conclusion_allowed = true
must_include_agents
critical_agents
nice_to_have_agents
should_not_include_agents
task_type
difficulty
risk_level
```

Teacher-proxy and draft labels remain separate diagnostics only:

```text
deepseek_teacher_v1 -> quality_conclusion_allowed=false
draft_for_human_review -> quality_conclusion_allowed=false
```

Threshold draft for RP-3A implementation readiness:

```text
high_confidence_wrong_rate <= 5% with sufficient high-confidence sample count
critical_agent_miss_rate_advisory <= critical_agent_miss_rate_baseline
must_include_recall_advisory >= baseline, or within an explicit non-inferiority margin
parse_fallback_rate_advisory <= parse_fallback_rate_baseline
used_default_plan_rate_advisory <= baseline
filtered_agents_avg_advisory <= baseline + 0.2
l2_truncated_rate_advisory <= baseline
avg_selected_agents_advisory <= baseline + 1.0
negative_selection_rate_advisory <= baseline
prompt_token_delta_avg <= 1200
prompt_char_delta_p95 within the agreed prompt budget
live additional routing latency p50 <= 500 ms
live additional routing latency p90 <= 1500 ms
live additional routing latency p95 <= 2500 ms
```

Rollback policy for future RP-3A:

```text
ROUTE_PRIOR_ADVISORY_MODE=off | shadow | prompt
default = off
one-flag rollback = ROUTE_PRIOR_ADVISORY_MODE=off
```

As of RP-3A-0D this env is not implemented. It is a future code requirement,
not a current runtime fact.

Public boundary constraints:

```text
no State schema field for route_prior / reliability / advisory
no public contract field
no workflow.snapshot field
no /api/agents route-profile or reliability exposure
no /api/health readiness expansion
no frontend change
no manager dispatch change
no AGENT_TOOLS change
```

Readiness gate before RP-3A implementation:

```text
manual_gold smoke set exists
prompt A/B harness artifact schema is reviewed
network-free parser stability run passes
optional live run shows no parse fallback regression
token/latency budget evidence exists
no public boundary expansion is proven by tests
rollback env policy is implemented default-off before prompt mode is usable
```

## 18. Runtime Config

Historical private RP-2/RP-3 config, retained for archived lineage only:

```text
ROUTE_PRIOR_RELIABILITY_ENABLED=0
ROUTE_PRIOR_ADVISORY_MODE=off
ROUTE_PRIOR_PROFILE_CARDS_DIR=config/route_profiles
ROUTE_PRIOR_RELIABILITY_TABLE=
ROUTE_PRIOR_TRACE_TOP_CARDS=5
ROUTE_PRIOR_MAX_PROMPT_STRONG=4
ROUTE_PRIOR_MAX_PROMPT_CANDIDATE=4
ROUTE_PRIOR_MAX_PROMPT_WILDCARD=2
```

Historical behavior before AC-1B-2A:

```text
off:
  preserved RP-1A behavior

shadow:
  RP-2C computed reliability cards and comparison trace when ROUTE_PRIOR_RELIABILITY_ENABLED=1
  no Router prompt change

prompt:
  append compact advisory block
  still no post-parse repair
```

These envs must remain private runtime config and must not be added to `/api/health`.

## 19. State and Public Boundary

Current `State` does not include route prior, reliability, or advisory fields. RP-2 should not add State fields.

Allowed:

```text
LOCAL_TRACE event
offline eval artifact
temporary local variable inside router_node
```

Not allowed:

```text
State.route_prior
State.route_reliability
State.advisory
State.route_cards
public workflow projection of route cards
```

No RARP data should enter:

```text
PublicTurn
WorkflowModel
AgentCatalogResponse
HealthResponse
StreamEvent
public store
frontend workflow panel
frontend agents page
```

## 20. Implementation Slices

### Slice 1: Design Doc Only

Files:

```text
docs/ROUTE_PRIOR_RARP_DESIGN.md
docs/INDEX.md
docs/CHANGELOG.md
```

No runtime code.

### Slice 2: RP-2A Eval Schema and Metrics

Likely files:

```text
ops/regression/route_prior/run_route_prior_eval.py
ops/regression/route_prior/eval_route_prior_outputs.py
ops/regression/route_prior/fixtures/rp2_labeling_template.jsonl
tests/archive/route_prior/test_route_prior_eval_rp2.py
```

No runtime code.

### Slice 3: RP-2B Profile Card and Reliability Scorer

Implemented files:

```text
src/react_agent/route_profile_registry.py
src/react_agent/route_reliability.py
ops/regression/route_prior/run_route_prior_eval.py
tests/archive/route_prior/test_route_reliability_rp2.py
tests/archive/route_prior/test_route_profile_registry_rp2.py
```

RP-2B is offline-first and opt-in for run artifacts through `--enable-rarp-scoring`. It adds no Router prompt change, parser change, State/public change, `/api/agents` exposure, `/api/health` readiness field, or manager dispatch change.

### Slice 4: Historical RP-2C Runtime Shadow Comparison Scaffold

Historical files:

```text
src/react_agent/route_reliability.py
src/react_agent/graph.py (runtime wiring removed in AC-1B-2A)
tests/archive/route_prior/test_route_prior_runtime_invariance_rp2.py
tests/archive/route_prior/test_route_prior_router_comparison_rp2.py
```

RP-2C was env-gated by `ROUTE_PRIOR_RELIABILITY_ENABLED`, trace-only, and fail-open. AC-1B-2A removed the runtime wiring that emitted `route_reliability_shadow` and `route_prior_router_comparison` trace events. Current routing is owned by the formal Router provider output and `router_parse`.

### Slice 5: Future RP-3A Env-Gated Advisory Prompt

Later only. Not implemented in the current work package; current RP-3A remains offline/ops tooling and evidence only.

Likely files:

```text
src/react_agent/graph.py
src/react_agent/prompts.py
src/react_agent/route_reliability.py
tests/unit_tests/test_route_prior_advisory_rp3.py
```

### Slice 6: RP-4 Guarded Repair

Future only. Do not implement as part of RP-2 or RP-3A.

## 21. Test Matrix

Route profile tests:

```text
valid profile card loads
missing card fallback
invalid card fail-open
special agent card ignored
ordinary pool still excludes a01/a02/a25
public /api/agents does not expose profile card fields
```

Reliability scorer tests:

```text
cold-start defaults
historical reliability applied
uncertainty penalty applied
cost penalty applied
deterministic ordering
wildcard guardrail preserved
confidence bands
```

Eval metrics tests:

```text
route_eval_label_v0 parsing
legacy expected_agents compatibility
must/critical/nice/negative validation
safe_recall vs effective_recall
critical miss
negative selection
high-confidence wrong
ECE
Brier
cost metrics
label_source grouped metrics
teacher_proxy quality_conclusion_allowed=false
```

Router comparison tests:

```text
overlap
prior_only_agents
router_only_agents
omitted_strong_recommended
selected_deprioritized
no layer_plan mutation
```

Runtime invariance tests:

```text
default env keeps Router prompt unchanged
default env keeps committed layer_plan unchanged
reliability scorer error fail-open
no State field added
no public workflow field added
```

No-leak tests:

```text
no raw embeddings in artifact
no full profile_text in public artifact by default
public /api/agents no route profile fields
public workflow no route cards
/api/health no route-prior readiness expansion
```

RP-3 advisory tests only apply when implementing RP-3.

## 22. Quality Gate Policy

Blocking invariants can enter the normal unit gate:

```text
special_agent_leakage == 0
unknown predicted id handling deterministic
no raw embeddings emitted
profile card invalid does not crash runtime
default env preserves Router committed output
public /api/agents does not expose internal route fields
teacher-proxy quality_conclusion_allowed=false
```

Diagnostic metrics remain optional/non-blocking until enough manual gold exists:

```text
expected_agent_recall@5
shortlist_recall
critical_agent_miss_rate
high_confidence_wrong_rate
ECE
Brier
cost@recall
router_miss_prior_hit
prior_miss_router_hit
```

Current `run_quality.py --mode mainline` runs static checks, unit tests, public adapter integration, graph smoke, frontend build/test, and deterministic fusion gate. RP-1B route-prior eval remains optional and non-blocking.

Potential future route-prior commands:

```text
python -m ops.regression.route_prior.run_route_prior_eval ...
python -m ops.regression.route_prior.eval_route_prior_outputs ...
python -m ops.regression.route_prior.gate_route_prior_outputs ...
```

`gate_route_prior_outputs` should not block mainline in the first implementation.

## 23. Trace and Artifact Privacy

Current `RunLogger`:

```text
enabled only when LOCAL_TRACE=1
writes JSONL under LOG_DIR or log/YYYYMMDD
drops keys containing api_key/token/secret/password
truncates long strings by TRACE_MAX_CHARS
```

Before AC-1B-2A, graph logs included `route_prior_shadow`, `router_decision`, `run_start`, and other node events. Current graph runtime no longer emits the old route-prior/RARP trace events; `router_decision` and `run_start` remain part of normal Router tracing.

Historical RARP trace allowed:

```text
route_reliability_shadow summary
route_prior_router_comparison summary
top ids
score bands
reason codes
counts
hashes
short previews
```

Historical RARP trace not allowed:

```text
raw embeddings
full profile_text by default
full profile card text by default
secret env
API keys
raw hidden prompts
```

RP-2 artifacts should prefer:

```text
question_hash
question_preview
```

Full raw question is local/debug or legacy compatibility only.

## 24. Documentation Plan

Implementation slices that change behavior should update the appropriate authority docs:

```text
README.md
docs/SYSTEM_MAP.md
docs/PROJECT_OVERVIEW.md
docs/INDEX.md
docs/CHANGELOG.md
```

Each implementation slice should record scope boundaries:

```text
no formal Router ownership change
no Router prompt/parser change unless RP-3 explicitly
no State schema change
no public API/workflow/health change
no manager dispatch change
no agent execution change
teacher-proxy remains proxy-only
```

## 25. Custom Agents and Codex Workflow

Implementation prompts should explicitly decide whether to use project custom agents. If used, they should remain read-only investigators unless the parent task assigns a bounded write scope.

Available project-scoped agents:

```text
repo_explorer:
  read-only execution path and file ownership tracing

protocol_auditor:
  read-only Router schema/parser/State/public boundary auditing

test_impact_analyst:
  read-only affected test and validation path mapping

docs_impact_analyst:
  read-only docs/changelog impact mapping
```

Final code, tests, docs, and changelog updates remain a single-writer closeout.

## 26. Promotion Criteria

RP-2 to RP-3 requires:

```text
manual_gold label set >= 100 cases
critical_agent_miss_rate not worse than baseline
high_confidence_wrong_rate below agreed threshold
no special_agent_leakage
no public leak tests passing
default runtime invariance tests passing
parse fallback rate not worse in prompt A/B dry run
```

RP-3 to RP-4 requires stronger evidence:

```text
manual_gold label set >= 300 cases
router_miss_prior_hit cases reliably exceed prior_miss_router_hit harm
bounded repair reduces critical miss
avg shortlist size/cost within budget
no parser regression
no public surface expansion
rollback is one env flag
```

RP-4 is out of current scope.

## 27. Performance Budget

RARP must not add a second LLM call.

Expected hot-path overhead in prompt mode:

```text
query embedding:
  local or remote backend dependent

deterministic scoring:
  ms-level

route card render:
  ms-level

Router prompt token delta:
  compact block only, target 300-1200 tokens
```

Runtime target for RP-3 prompt mode:

```text
p50 additional routing latency <= 500 ms
p90 additional routing latency <= 1500 ms
p95 additional routing latency <= 2500 ms
```

RP-2 shadow/offline should not affect production hot path unless env-enabled.

## 28. Rollback

Historical RP-2 rollback before AC-1B-2A:

```text
ROUTE_PRIOR_RELIABILITY_ENABLED=0
```

Historical RP-3 rollback:

```text
ROUTE_PRIOR_ADVISORY_MODE=off
```

RP-4 rollback is future-only and must use a separate env flag if ever implemented.

## 29. Out of Scope Until Dedicated Prompts

Before a dedicated implementation prompt, do not:

```text
implement route_reliability.py
change Router prompt
change parser
add State fields
add public contract fields
expose route cards in /api/agents
expose route cards in workflow
change manager dispatch
change AGENT_TOOLS
implement guarded repair
promote route-prior eval into mainline gate
```

## 30. Implementation Slice Status

RP-2A is implemented as offline eval/tooling only:

```text
route_eval_label_v0 support
legacy RP-1B schema compatibility
expanded offline metrics
RP-2A focused tests
docs and changelog update
no Router prompt change
no State/public changes
```

RP-2B is implemented as offline-first profile-card/reliability tooling:

```text
optional profile card loader/fallback
deterministic reliability scorer
optional reliability table reader
optional run_route_prior_eval --enable-rarp-scoring artifact section
RP-2B focused tests
no Router prompt change
no State/public changes
docs + changelog update
```

Historical RP-2C implementation before AC-1B-2A:

```text
ROUTE_PRIOR_RELIABILITY_ENABLED default off
compact route_reliability_shadow trace
route_prior_router_comparison trace
comparison helper does not mutate layer_plan
scorer/comparison errors fail open
RP-2C focused tests
no Router prompt/parser change
no committed routing output change
no State/public changes
docs + changelog update
```

The next implementation prompt should be scoped separately if it targets RP-3 advisory. It should not include:

```text
RP-3 prompt advisory
RP-4 repair
runtime repair
```

## 31. Final Mental Model

RARP is not a new agent, not a new public product feature, and not a replacement Router.

It is a reliability layer around routing:

```text
RP-1A:
  semantic route-prior shadow

RP-2:
  reliability-aware shadow scoring + metrics

RP-3:
  non-binding Router advisory

RP-4:
  future bounded repair
```

The current multi-agent runtime already has a formal Router that owns the four-layer plan. RARP adds an internal, reliability-aware second opinion before and after that Router. It first observes, scores, and evaluates without changing behavior. Only after manual-gold evidence proves value does it become a non-binding Router advisory. This keeps the system auditable, reversible, and aligned with the existing public/product boundary.
