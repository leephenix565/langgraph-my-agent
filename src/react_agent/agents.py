"""Agent接口协议、元数据与注册表。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import BaseTool


class AgentInput(Dict[str, Any]):
    """约束逻辑字段的简单 TypedDict 替代（避免额外依赖）。"""

    question: str  # 原始用户问题
    subtask: str  # Manager 分配的子任务描述
    shared_context: Dict[str, Any]  # 其它 Agent 的中间结论
    history: List[Dict[str, Any]]  # 与该 Agent 相关的历史对话
    tools_config: Dict[str, Any]  # 工具配置


class AgentOutput(Dict[str, Any]):
    """Agent 标准输出字段。"""

    analysis: str
    key_points: List[str]
    evidence: List[str]
    confidence: float


@dataclass
class AgentMetadata:
    """元数据用于 Router / 管理员。"""

    id: str
    name: str
    description: str
    capabilities: List[str]
    input_type: str
    latency_level: str
    cost_level: str
    version: str


# 运行时注册表（默认包含内置 Agent）
AGENT_METADATA: Dict[str, AgentMetadata] = {}
AGENT_TOOLS: Dict[str, BaseTool] = {}


def register_agent(metadata: AgentMetadata, tool: BaseTool) -> None:
    """注册单个 Agent 的元数据和工具。"""
    AGENT_METADATA[metadata.id] = metadata
    AGENT_TOOLS[metadata.id] = tool


def load_metadata_from_dir(path: Path) -> None:
    """可选：从目录扫描 agent_{id}.json/yaml，填充元数据。

    简化处理：只解析 JSON，YAML 可后续扩展。
    """
    for file in path.glob("agent_*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            meta = AgentMetadata(**data)
            if meta.id not in AGENT_METADATA:
                AGENT_METADATA[meta.id] = meta
        except Exception:
            continue
