"""Router -> Manager -> Analysts LangGraph demo."""

from importlib import import_module

graph = import_module("react_agent.graph")
graph_app = graph.graph

__all__ = ["graph", "graph_app"]
