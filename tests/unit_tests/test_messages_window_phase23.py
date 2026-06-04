from react_agent.public_contracts import PublicTurn
from react_agent.public_mapping import replay_messages


def test_replay_messages_keeps_public_transcript_only() -> None:
    turns = [
        PublicTurn(id="u1", role="user", text="hello", createdAt="2026-06-04 10:00"),
        PublicTurn(id="a1", role="assistant", text="answer", createdAt="2026-06-04 10:01"),
    ]
    assert replay_messages(turns, "next") == [
        ("user", "hello"),
        ("assistant", "answer"),
        ("user", "next"),
    ]
