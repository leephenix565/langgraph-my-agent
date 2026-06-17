#!/usr/bin/env python3
# ruff: noqa: D102,D103,T201,E402
"""Run an R8-13A end-to-end fixed DAG demo smoke.

By default this remains an offline smoke: fake external compute mappings,
task-aware LLM placeholders for unconnected L2 slots, and fake LLM report
synthesis. Set ``R8_13A_USE_REAL_EXTERNAL_COMPUTE=1`` to use the actual
default-off compute bridge and its explicit loopback allowlist. Set
``R8_13A_USE_REAL_REPORT_MODEL=1`` or ``R8_13A_USE_REAL_PLACEHOLDER_MODEL=1``
only when the configured provider path is intentionally available.

The runner never calls `/v1/agent/invoke`, never changes runtime bindings, and
never sets live flags.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import react_agent.fixed_dag_external_compute_bridge as bridge
import react_agent.fixed_dag_llm_placeholders as llm_placeholders
import react_agent.fixed_dag_report_synthesizer as report_synthesizer
import react_agent.graph as graph_module
from react_agent.context import Context
from react_agent.fixed_dag_external_adapter import (
    map_external_response_to_fixed_dag_object,
)

DEFAULT_QUESTION = "请从估值、市场、风险和宏观角度分析贵州茅台 600519.SH 当前是否值得关注。"
DEFAULT_AS_OF = "2026-06-05"
DEFAULT_ALLOWLIST = (
    "value_ml_valuation",
    "market_stock_technical",
    "risk_identification",
    "macro_analysis",
    "value_composite",
    "market_composite",
    "risk_composite",
    "macro_composite",
)
REAL_EXTERNAL_COMPUTE_ENV = "R8_13A_USE_REAL_EXTERNAL_COMPUTE"
REAL_REPORT_MODEL_ENV = "R8_13A_USE_REAL_REPORT_MODEL"
REAL_PLACEHOLDER_MODEL_ENV = "R8_13A_USE_REAL_PLACEHOLDER_MODEL"
ALLOWLIST_ENV = "R8_13A_E2E_ALLOWLIST"
FORBIDDEN_MARKERS = (
    "api_key",
    "secret",
    "password",
    "authorization",
    "cookie",
    "traceback",
    "chain-of-thought",
    "raw_response",
    "raw_provider_response",
    "raw_external_json",
    "/v1/agent/invoke",
)


class FakePlaceholderModel:
    """Deterministic JSON model used by unconnected L2 placeholder slots."""

    def invoke(self, prompt: str) -> SimpleNamespace:
        agent_id = _extract_prompt_field(prompt, "agent_id") or "unknown_agent"
        return SimpleNamespace(
            content=json.dumps(
                {
                    "analysis": (
                        f"{agent_id} 已收到 agent_task_v1，本次以内部 LLM 占位方式"
                        "给出结构化观察，等待真实外部 agent 接入。"
                    ),
                    "key_points": [
                        "已读取中文任务指令和 required_output_schema。",
                        "该结论不是生产外部 agent 证据。",
                    ],
                    "evidence": [
                        {
                            "fact": (
                                "R8-13A offline smoke 使用 task-aware placeholder "
                                "补齐未接入 L2 槽位。"
                            )
                        }
                    ],
                    "confidence": 0.28,
                },
                ensure_ascii=False,
            )
        )


class FakeReportModel:
    """Deterministic JSON model for final report synthesis in the smoke."""

    def invoke(self, prompt: str) -> SimpleNamespace:
        return SimpleNamespace(
            content=json.dumps(
                {
                    "title": "R8-13A 固定 DAG 端到端研判报告",
                    "answer": (
                        "研判流程报告：本轮已从用户问题进入 fixed DAG，router/orchestrator "
                        "为每个 agent 生成 agent_task_v1。allowlist 内的 agent 使用"
                        "外部 compute 映射结果，未接入 L2 agent 使用 task-aware LLM "
                        "placeholder。综合来看，估值维有正向样例信号，市场维偏中性，"
                        "风险门为 pass，宏观调节器给出 value/market 权重。该结果证明"
                        "输入问题到最终报告的主系统链路可跑通，但 offline smoke 不代表"
                        "真实业务结论。"
                    ),
                    "sections": [
                        {
                            "id": "agent_inputs",
                            "title": "单体与综合智能体输入",
                            "content": (
                                "报告已读取 L2 单体 agent、L3 综合 agent、风险门、宏观调节"
                                "和任务编排摘要。"
                            ),
                        },
                        {
                            "id": "final_view",
                            "title": "最终研判",
                            "content": "当前可进入演示关注池；真实展示前仍需替换 fake smoke 为真实 provider/compute。",
                        },
                    ],
                    "evidence_cards": [
                        {
                            "title": "端到端链路",
                            "note": "compiled graph -> agent_task_v1 -> L2/L3 evidence -> report_input_bundle_v1 -> report_result_v1",
                        }
                    ],
                    "limitations": [
                        "本 smoke 使用 fake external compute 和 fake LLM，不调用生产 endpoint。",
                        "未调用 invoke endpoint，未改 runtime bindings，未设置 live flags。",
                    ],
                },
                ensure_ascii=False,
            )
        )


def _extract_prompt_field(prompt: str, field: str) -> str:
    match = re.search(rf"^{re.escape(field)}:\s*(.+)$", prompt, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _env_enabled(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in {"1", "true", "on", "yes"}


def _allowlist_from_env(default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(ALLOWLIST_ENV) or os.getenv("EXTERNAL_COMPUTE_DEMO_ALLOWLIST") or ""
    if not raw.strip():
        return default
    items: list[str] = []
    for item in raw.split(","):
        agent_id = item.strip()
        if agent_id and agent_id not in items:
            items.append(agent_id)
    return tuple(items)


def _compute_envelope(agent_id: str, external_agent_id: str, tool_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "external_agent_compute_v0",
        "agent_id": agent_id,
        "external_agent_id": external_agent_id,
        "status": "ok",
        "tool_result": dict(tool_result),
    }


def _l2_conclusion(entry: bridge.ExternalComputeDemoEntry, as_of: str) -> dict[str, Any]:
    role = "gate_member" if entry.dimension == "risk" else "direction"
    result: dict[str, Any] = {
        "schema_version": "agent_conclusion_v1",
        "agent_id": entry.agent_id,
        "external_agent_id": entry.external_agent_id,
        "dimension": entry.dimension,
        "role": role,
        "confidence": 0.66,
        "status": "ok",
        "evidence": [
            {
                "id": f"offline-smoke-{entry.agent_id}",
                "fact": f"{entry.agent_id} fake external compute fixture mapped successfully.",
                "source": "r8_13a_offline_smoke",
                "as_of": as_of,
                "data_as_of": as_of,
            }
        ],
        "as_of": as_of,
        "data_as_of": as_of,
        "event_flags": [],
    }
    if role == "gate_member":
        result["risk_score"] = 0.18
    else:
        result["stance"] = {
            "value": "positive",
            "market": "neutral",
            "macro": "neutral",
        }.get(entry.dimension, "neutral")
    return result


def _data_bundle(entry: bridge.ExternalComputeDemoEntry, as_of: str) -> dict[str, Any]:
    return {
        "schema_version": "data_bundle_v1",
        "agent_id": entry.agent_id,
        "external_agent_id": entry.external_agent_id,
        "status": "ok",
        "target": "600519.SH",
        "as_of": as_of,
        "data_as_of": as_of,
        "snapshot_id": "r8-13h-offline-data-snapshot",
        "sources": [
            {"name": "daily_price", "source": "offline_fixture"},
            {"name": "financial_indicator", "source": "offline_fixture"},
        ],
        "feature_bundle": {
            "close": 1520.0,
            "pe_ttm": 28.4,
            "pb": 8.1,
        },
        "missing_fields": [],
    }


def _entity_relation_bundle(
    entry: bridge.ExternalComputeDemoEntry,
    as_of: str,
) -> dict[str, Any]:
    return {
        "schema_version": "entity_relation_bundle_v1",
        "agent_id": entry.agent_id,
        "external_agent_id": entry.external_agent_id,
        "status": "ok",
        "target": "600519.SH",
        "as_of": as_of,
        "data_as_of": as_of,
        "entities": [
            {"id": "stock:600519.SH", "name": "贵州茅台", "type": "company"},
            {"id": "industry:baijiu", "name": "白酒", "type": "industry"},
        ],
        "relations": [
            {
                "source": "stock:600519.SH",
                "target": "industry:baijiu",
                "type": "belongs_to",
            }
        ],
        "sources": [{"name": "offline_relation_fixture"}],
        "notes": ["R8-13H offline entity relation fixture."],
    }


def _dimension_conclusion(entry: bridge.ExternalComputeDemoEntry, as_of: str) -> dict[str, Any]:
    members = (
        [
            {"agent_id": "value_ml_valuation", "weight": 1.0, "stance": "positive", "confidence": 0.66},
        ]
        if entry.agent_id == "value_composite"
        else [
            {"agent_id": "market_stock_technical", "weight": 1.0, "stance": "neutral", "confidence": 0.61},
        ]
    )
    return {
        "schema_version": "dimension_conclusion_v1",
        "agent_id": entry.agent_id,
        "external_agent_id": entry.external_agent_id,
        "dimension": entry.dimension,
        "members": members,
        "stance": "positive" if entry.dimension == "value" else "neutral",
        "confidence": 0.7,
        "status": "ok",
        "contributing_agents": [str(item["agent_id"]) for item in members],
        "evidence": [
            {
                "id": f"offline-smoke-{entry.agent_id}",
                "fact": f"{entry.agent_id} fake L3 dimension conclusion mapped successfully.",
                "source": "r8_13a_offline_smoke",
                "as_of": as_of,
                "data_as_of": as_of,
            }
        ],
        "as_of": as_of,
        "data_as_of": as_of,
        "method": "offline_weighted_fixture",
    }


def _risk_conclusion(entry: bridge.ExternalComputeDemoEntry, as_of: str) -> dict[str, Any]:
    return {
        "schema_version": "risk_conclusion_v1",
        "agent_id": entry.agent_id,
        "external_agent_id": entry.external_agent_id,
        "dimension": "risk",
        "role": "gate",
        "gate": "pass",
        "risk_score": 0.21,
        "penalty": 0.0,
        "confidence": 0.73,
        "contributing_agents": ["risk_identification"],
        "triggered_flags": [],
        "red_lines": [],
        "evidence": [
            {
                "id": "offline-smoke-risk-composite",
                "fact": "risk_composite fake gate pass mapped successfully.",
                "source": "r8_13a_offline_smoke",
                "as_of": as_of,
                "data_as_of": as_of,
            }
        ],
        "as_of": as_of,
        "data_as_of": as_of,
        "status": "ok",
    }


def _macro_conclusion(entry: bridge.ExternalComputeDemoEntry, as_of: str) -> dict[str, Any]:
    return {
        "schema_version": "macro_conclusion_v1",
        "agent_id": entry.agent_id,
        "external_agent_id": entry.external_agent_id,
        "dimension": "macro",
        "role": "regulator",
        "regime": "neutral",
        "dimension_weights": {"value": 0.55, "market": 0.45},
        "risk_sensitivity": 0.65,
        "style_bias": ["quality"],
        "contributing_agents": ["macro_analysis"],
        "evidence": [
            {
                "id": "offline-smoke-macro-composite",
                "fact": "macro_composite fake regulator mapped successfully.",
                "source": "r8_13a_offline_smoke",
                "as_of": as_of,
                "data_as_of": as_of,
            }
        ],
        "as_of": as_of,
        "data_as_of": as_of,
        "status": "ok",
        "confidence": 0.69,
    }


def fake_invoke_external_compute(
    entry: bridge.ExternalComputeDemoEntry,
    *,
    question: str,
    as_of: str,
    request_id: str,
    timeout_seconds: float,
    agent_task: Mapping[str, Any] | None = None,
    upstream_outputs: Mapping[str, Any] | None = None,
    transport: bridge.Transport | None = None,
) -> dict[str, Any]:
    del question, request_id, timeout_seconds, upstream_outputs, transport
    if entry.expected_payload == "agent_conclusion_v1":
        tool_result = _l2_conclusion(entry, as_of)
    elif entry.expected_payload == "data_bundle_v1":
        tool_result = _data_bundle(entry, as_of)
    elif entry.expected_payload == "entity_relation_bundle_v1":
        tool_result = _entity_relation_bundle(entry, as_of)
    elif entry.expected_payload == "dimension_conclusion_v1":
        tool_result = _dimension_conclusion(entry, as_of)
    elif entry.expected_payload == "risk_conclusion_v1":
        tool_result = _risk_conclusion(entry, as_of)
    elif entry.expected_payload == "macro_conclusion_v1":
        tool_result = _macro_conclusion(entry, as_of)
    else:
        return {
            "agent_id": entry.agent_id,
            "status": "failed",
            "mapped": None,
            "failure_code": "unsupported_fixture_payload",
            "warning": "external_compute_demo_failed:unsupported_fixture_payload",
        }
    mapped = map_external_response_to_fixed_dag_object(
        _compute_envelope(entry.agent_id, entry.external_agent_id, tool_result)
    )
    return {
        "agent_id": entry.agent_id,
        "status": "pass",
        "mapped": mapped,
        "failure_code": "",
        "warning": "",
        "agent_task": dict(agent_task) if isinstance(agent_task, Mapping) else {},
    }


def _source(item: Mapping[str, Any]) -> str:
    provenance = item.get("provenance", {})
    return str(provenance.get("runtime_path") or provenance.get("source") or "unknown") if isinstance(provenance, Mapping) else "unknown"


def _summary_from_l2(agent_id: str, item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "status": item.get("status"),
        "dimension": item.get("dimension"),
        "stance": item.get("stance"),
        "confidence": item.get("confidence"),
        "risk_score": item.get("risk_score"),
        "source": _source(item),
        "analysis": item.get("analysis", ""),
    }


def _summary_from_l3(dimension: str, item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "agent_id": item.get("agent_id"),
        "status": item.get("status"),
        "stance": item.get("stance"),
        "confidence": item.get("confidence"),
        "gate": item.get("gate"),
        "risk_score": item.get("risk_score"),
        "regime": item.get("regime"),
        "dimension_weights": item.get("dimension_weights"),
        "source": _source(item),
    }


def _assert_no_forbidden_markers(payload: Mapping[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False).lower()
    leaked = [marker for marker in FORBIDDEN_MARKERS if marker in text]
    if leaked:
        raise RuntimeError(f"unsafe_marker_in_smoke_artifact:{','.join(leaked)}")


async def run_smoke(question: str, as_of: str, artifact_root: Path) -> dict[str, Any]:
    use_real_external_compute = _env_enabled(REAL_EXTERNAL_COMPUTE_ENV)
    use_real_report_model = _env_enabled(REAL_REPORT_MODEL_ENV)
    use_real_placeholder_model = _env_enabled(REAL_PLACEHOLDER_MODEL_ENV)
    allowlist = _allowlist_from_env(DEFAULT_ALLOWLIST)

    if not use_real_placeholder_model:
        llm_placeholders.load_chat_model = lambda _model: FakePlaceholderModel()
    if not use_real_report_model:
        report_synthesizer.load_chat_model = lambda _model: FakeReportModel()
    if not use_real_external_compute:
        bridge.invoke_external_compute = fake_invoke_external_compute  # type: ignore[assignment]

    result = await graph_module.graph.ainvoke(
        {"messages": [("user", question)]},
        context=Context(
            enable_external_compute_demo=True,
            external_compute_demo_allowlist=allowlist,
            enable_internal_llm_placeholders=True,
            enable_llm_report_synthesis=True,
            fixed_dag_as_of=as_of,
        ),
    )
    dag_execution = result.get("dag_execution", {})
    l2 = result.get("l2_conclusions") or dag_execution.get("l2_conclusions", {})
    l3 = result.get("dimension_results") or dag_execution.get("dimension_results", {})
    report = result.get("report_result") or dag_execution.get("report_result", {})
    report_input_bundle = (
        result.get("report_input_bundle")
        or dag_execution.get("report_input_bundle")
        or {}
    )
    agent_evidence_bundle = (
        report_input_bundle.get("agent_evidence_bundle", {})
        if isinstance(report_input_bundle, Mapping)
        else {}
    )
    workflow_snapshot = result.get("workflow_snapshot") or dag_execution.get("workflow_snapshot") or {}
    summary = {
        "phase": "R8-13A",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "question": question,
        "mode": {
            "external_compute": "real_bridge" if use_real_external_compute else "fake_fixture",
            "report_model": "configured_provider" if use_real_report_model else "fake_fixture",
            "placeholder_model": "configured_provider" if use_real_placeholder_model else "fake_fixture",
        },
        "non_claims": [
            "No invoke endpoint was called.",
            "No runtime binding was enabled.",
            "No live flags were set.",
            "No raw external/provider response is stored in the artifact.",
            (
                "Only explicitly allowlisted loopback /v1/agent/compute endpoints were eligible."
                if use_real_external_compute
                else "No production endpoint was called by the offline fixture mode."
            ),
            (
                "Configured provider may be called for report/placeholder synthesis if explicitly enabled."
                if use_real_report_model or use_real_placeholder_model
                else "No provider model was called by the offline fixture mode."
            ),
        ],
        "allowlist": list(allowlist),
        "provenance": dag_execution.get("provenance", {}),
        "l2_agent_outputs": {
            agent_id: _summary_from_l2(agent_id, item)
            for agent_id, item in l2.items()
            if isinstance(item, Mapping)
        },
        "l3_composite_outputs": {
            dimension: _summary_from_l3(dimension, item)
            for dimension, item in l3.items()
            if isinstance(item, Mapping)
        },
        "agent_task_summaries": dag_execution.get("agent_task_summaries", []),
        "report_input_bundle_summaries": {
            "agent_task_summaries": report_input_bundle.get("agent_task_summaries", [])
            if isinstance(report_input_bundle, Mapping)
            else [],
            "l2_agent_summaries": report_input_bundle.get("l2_agent_summaries", [])
            if isinstance(report_input_bundle, Mapping)
            else [],
            "l3_composite_summaries": report_input_bundle.get("l3_composite_summaries", [])
            if isinstance(report_input_bundle, Mapping)
            else [],
            "quality_summary": agent_evidence_bundle.get("quality_summary", {})
            if isinstance(agent_evidence_bundle, Mapping)
            else {},
        },
        "report_result": {
            "title": report.get("title"),
            "status": report.get("status"),
            "answer": report.get("answer"),
            "sections": report.get("sections", []),
            "limitations": report.get("limitations", []),
        },
        "workflow_step_count": len(workflow_snapshot.get("stepResults", {}))
        if isinstance(workflow_snapshot, Mapping)
        else 0,
        "final_answer": result.get("messages", [SimpleNamespace(content="")])[-1].content,
    }
    _assert_no_forbidden_markers(summary)
    _assert_no_forbidden_markers(agent_evidence_bundle if isinstance(agent_evidence_bundle, Mapping) else {})
    _assert_no_forbidden_markers(workflow_snapshot if isinstance(workflow_snapshot, Mapping) else {})
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (artifact_root / "agent_tasks.json").write_text(
        json.dumps(summary["report_input_bundle_summaries"]["agent_task_summaries"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (artifact_root / "agent_evidence_bundle.json").write_text(
        json.dumps(agent_evidence_bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (artifact_root / "workflow_trace.json").write_text(
        json.dumps(workflow_snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (artifact_root / "final_report.md").write_text(
        str(summary["final_answer"]),
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--as-of", default=DEFAULT_AS_OF)
    parser.add_argument(
        "--artifact-root",
        default="",
        help="Defaults to /tmp/lma-r8-13a-e2e-smoke/<UTC timestamp>.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_root = Path(args.artifact_root or f"/tmp/lma-r8-13a-e2e-smoke/{timestamp}")
    summary = asyncio.run(run_smoke(str(args.question), str(args.as_of), artifact_root))
    print(f"artifact_root={artifact_root}")
    print(f"mode={summary['mode']}")
    print(f"mapped_agents={summary['provenance'].get('external_compute_demo_mapped_agents', [])}")
    print(
        "internal_llm_placeholder_conclusions="
        f"{summary['provenance'].get('internal_llm_placeholder_conclusions', 0)}"
    )
    print("final_report:")
    print(summary["final_answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
