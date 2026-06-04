from pathlib import Path

from react_agent.fixed_dag_contracts import RESET_RUNTIME_AGENT_IDS


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_fixed_dag_architecture_doc_lists_target_agents() -> None:
    assert len(RESET_RUNTIME_AGENT_IDS) == 27

    path = _repo_root() / "docs" / "ARCHITECTURE_FIXED_DAG.md"
    text = path.read_text(encoding="utf-8")

    missing = [agent_id for agent_id in RESET_RUNTIME_AGENT_IDS if agent_id not in text]

    assert missing == []
    assert text.count("| sentiment_company_radar |") == 1


def test_fixed_dag_architecture_doc_excludes_legacy_route_modes() -> None:
    path = _repo_root() / "docs" / "ARCHITECTURE_FIXED_DAG.md"
    text = path.read_text(encoding="utf-8")

    legacy_modes = ("Star", "Chain", "Debate", "Tree")

    assert not any(mode in text for mode in legacy_modes)
