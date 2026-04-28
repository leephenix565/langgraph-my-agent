# RARP Design: Reliability-Aware Route Prior

> Status: design document only. This document does not describe implemented runtime behavior unless a section explicitly cites existing RP-1A/RP-1B facts. Runtime behavior remains defined by `src/react_agent/*` and focused tests.

## 1. Summary

Reliability-Aware Route Prior, abbreviated RARP, is the planned evolution of the current RP-1A embedding-first route-prior shadow seam into a measurable, explainable, calibratable, and reversible reliability-aware routing prior layer.

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

### 4.1 RP-1A Runtime Seam

RP-1A already exists as an internal embedding-first semantic retrieval seam inside `router_node`, before the formal Router model invoke. It computes semantic similarity, shortlist, confidence band, low-confidence fallback, wildcard retention, and routing hints for ordinary agents.

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

Scope:

- offline only
- no runtime behavior change
- no Router prompt change
- no State/public change
- support `route_eval_label_v0`
- preserve legacy RP-1B schema compatibility
- add safe/effective recall and calibration-oriented metrics

### RP-2B: Profile Cards and Reliability Scorer

Scope:

- offline first
- optional profile cards
- missing-card fallback
- optional reliability table
- cold-start safe deterministic scoring
- no Router prompt change

### RP-2C: Runtime Shadow Trace and Post-Router Comparison

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

Fallback is `agent_id`. Existing code supports `_REGISTRY_OVERRIDES`; current override usage is primarily wildcard handling for `a15_research_synthesis`.

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
  "agent_id": "a11_rates_fx",
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
    "strongly_recommended": ["a03_macro_policy", "a11_rates_fx"],
    "candidate": ["a09_sector_bank"],
    "wildcard": ["a15_research_synthesis"],
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
    "a03_macro_policy",
    "a11_rates_fx",
    "a09_sector_bank"
  ],
  "critical_agents": [
    "a11_rates_fx"
  ],
  "nice_to_have_agents": [
    "a15_research_synthesis"
  ],
  "should_not_include_agents": [
    "a23_portfolio_opt"
  ],
  "expected_layers": {
    "L2": ["a03_macro_policy"],
    "L3": ["a11_rates_fx", "a09_sector_bank"]
  },
  "primary_agent": "a03_macro_policy",
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
  "prior_only_agents": ["a09_sector_bank"],
  "router_only_agents": ["a21_reg_compliance"],
  "omitted_strong_recommended": [],
  "selected_deprioritized": ["a23_portfolio_opt"],
  "router_miss_prior_hit": false,
  "prior_miss_router_hit": false,
  "both_miss": false,
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

## 17. RP-3 Router Advisory

RP-3 may give Router a compact, non-binding advisory block. It does not replace Router, alter the output schema, or narrow the parser allowed catalog.

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

## 18. Runtime Config

Planned RP-2/RP-3 config:

```text
ROUTE_PRIOR_RELIABILITY_ENABLED=0
ROUTE_PRIOR_ADVISORY_MODE=off
ROUTE_PRIOR_PROFILE_CARDS_DIR=config/route_profiles
ROUTE_PRIOR_RELIABILITY_TABLE=
ROUTE_PRIOR_MAX_PROMPT_STRONG=4
ROUTE_PRIOR_MAX_PROMPT_CANDIDATE=4
ROUTE_PRIOR_MAX_PROMPT_WILDCARD=2
ROUTE_PRIOR_TRACE_RELIABILITY=1
```

Default behavior:

```text
off:
  preserve current RP-1A behavior

shadow:
  compute reliability cards and comparison trace
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
tests/unit_tests/test_route_prior_eval_rp2.py
```

No runtime code.

### Slice 3: RP-2B Profile Card and Reliability Scorer

Likely files:

```text
src/react_agent/route_profile_registry.py
src/react_agent/route_reliability.py
tests/unit_tests/test_route_reliability_rp2.py
tests/unit_tests/test_route_profile_registry_rp2.py
```

No Router prompt change.

### Slice 4: RP-2C Runtime Shadow Comparison Scaffold

Likely files:

```text
src/react_agent/route_prior.py
src/react_agent/route_reliability.py
src/react_agent/graph.py
tests/unit_tests/test_route_prior_runtime_invariance_rp2.py
tests/unit_tests/test_route_prior_router_comparison_rp2.py
```

No `layer_plan` mutation.

### Slice 5: RP-3A Env-Gated Advisory Prompt

Later only.

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
router_miss_prior_hit
prior_miss_router_hit
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

Current graph logs include `route_prior_shadow`, `router_decision`, `run_start`, and other node events. `router_decision` currently records truncated question and raw Router output.

RARP trace allowed:

```text
route_reliability_shadow summary
top ids
score bands
reason codes
counts
hashes
short previews
```

RARP trace not allowed:

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

RP-2 rollback:

```text
ROUTE_PRIOR_RELIABILITY_ENABLED=0
```

RP-3 rollback:

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

## 30. First Expected Implementation Slice

The first implementation prompt should be limited to RP-2A and RP-2B:

```text
route_eval_label_v0 support
legacy RP-1B schema compatibility
expanded offline metrics
optional profile card loader/fallback
deterministic reliability scorer
no Router prompt change
no State/public changes
docs + changelog update
```

It should not include:

```text
RP-3 prompt advisory
RP-4 repair
runtime mutation
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
