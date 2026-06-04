import react_agent.baseline_sidecar as baseline_sidecar_module
import react_agent.graph as graph_module


def test_baseline_sidecar_module_is_retained_but_not_active_runtime() -> None:
    assert hasattr(baseline_sidecar_module, "run_baseline_sidecar")
    assert "baseline_sidecar" not in graph_module.builder.nodes


def test_reset_graph_has_no_google_grounding_dependency() -> None:
    assert "run_baseline_sidecar" not in graph_module.__dict__
