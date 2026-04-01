import asyncio
import statistics
import time

from react_agent import graph_app
from react_agent.context import Context

PROMPT = "请从宏观、产业、风险和结论四个层面，简要分析人工智能基础设施赛道未来一年的主要机会与风险，并给出结构化结论。"
N = 3
times = []

for i in range(N):
    t0 = time.perf_counter()
    result = asyncio.run(
        graph_app.ainvoke(
            {"messages": [("user", PROMPT)]},
            context=Context()
        )
    )
    dt = time.perf_counter() - t0
    times.append(dt)

    messages = result.get("messages", [])
    last = messages[-1].content if messages else ""
    if not isinstance(last, str):
        last = str(last)

    print(f"\n=== run {i+1}/{N} ===")
    print(f"e2e_sec = {dt:.3f}")
    print("answer_preview =", last[:300].replace("\n", " "))

print("\n=== summary ===")
print("runs_sec =", [round(x, 3) for x in times])
print("avg_sec  =", round(statistics.mean(times), 3))
print("p50_sec  =", round(statistics.median(times), 3))
if len(times) >= 2:
    qs = statistics.quantiles(times, n=10, method="inclusive")
    print("p90_sec  =", round(qs[8], 3))
