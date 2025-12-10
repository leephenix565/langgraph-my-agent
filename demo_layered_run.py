"""Minimal demo to run the 4-layer pipeline.

Usage:
    # set your API key envs first, e.g. OPENAI_API_KEY/ANTHROPIC_API_KEY
    python demo_layered_run.py
"""

import asyncio

from react_agent import graph
from react_agent.context import Context


async def main() -> None:
    res = await graph.ainvoke(
        {"messages": [("user", "示例：给出新能源车行业的投资观点和风险点")]},
        context=Context(model="deepseek/deepseek-chat"),
    )
    print("Final state keys:", res.keys())
    print("Layer plan:", res.get("layer_plan"))
    print("Layer mode:", res.get("layer_mode"))
    print("Analyst results keys:", list((res.get("analyst_results") or {}).keys()))
    print("Final message:", res["messages"][-1].content if res.get("messages") else "")


if __name__ == "__main__":
    asyncio.run(main())
