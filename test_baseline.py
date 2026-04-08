import os
# 强行关闭 LangSmith 监控，防止报错刷屏
os.environ["LANGCHAIN_TRACING_V2"] = "false" 

import asyncio, json, traceback
from dotenv import load_dotenv
load_dotenv(".env", override=True)

import react_agent.graph as graph_module
from react_agent.context import Context

QUESTION = "请基于最新公开信息，总结今天英伟达最重要的三条动态，并给出来源。"

async def main():
    ctx = Context()
    print("CTX baseline_model =", ctx.baseline_model)
    print("CTX enable_fair_fusion =", ctx.enable_fair_fusion)
    print("CTX baseline_force_search =", ctx.baseline_force_search)

    app = graph_module.get_graph_for_invoke(None)

    try:
        # 开始运行主程序
        state = await app.ainvoke(
            {"messages": [("user", QUESTION)]},
            context=ctx,
        )

        print("\n" + "="*40 + "\n")
        print("baseline_status =", state.get("baseline_status"))
        print("mainline_bundle_present =", bool(state.get("multi_agent_bundle")))
        print("baseline_bundle_present =", bool(state.get("baseline_bundle")))

        search_meta = state.get("baseline_bundle", {}).get("search_meta", {})
        print("search_meta =", json.dumps(search_meta, ensure_ascii=False, indent=2))

        cards = state.get("baseline_bundle", {}).get("evidence_cards", [])
        print("evidence_cards_len =", len(cards))
        if cards:
            print("first_card =", json.dumps(cards[0], ensure_ascii=False, indent=2))

        print("final_message_present =", bool(state.get("messages")))
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())