from __future__ import annotations

from pathlib import Path

from astra.agent._user_agent.agent import TASK_END_MARKER, UserAgent
from astra.agent._user_agent.config import UserAgentConfig


def _build_agent() -> UserAgent:
    root = Path(__file__).resolve().parents[1]
    return UserAgent(
        UserAgentConfig(prompt_path=root / "src" / "astra" / "prompts" / "user_agent.md")
    )


def test_user_agent_ends_once_all_goals_are_covered_without_follow_up(monkeypatch) -> None:
    agent = _build_agent()
    called = {"value": False}

    def fake_call_model(prompt: str) -> str:
        del prompt
        called["value"] = True
        return "This should not be used."

    monkeypatch.setattr(agent, "call_model", fake_call_model)

    result = agent.generate_message(
        blueprint={
            "goals": ["Inspect the repo", "Find the helper implementation"],
            "user_agent_config": {
                "role": "engineer",
                "personality": "brief",
                "knowledge_boundary": "repo-only",
            },
            "end_condition": "The user found the relevant code.",
        },
        messages=[
            {"role": "user", "content": "Can you inspect the repo?"},
            {"role": "assistant", "content": "I checked the structure and found the main folders."},
            {"role": "user", "content": "Please look for the helper implementation too."},
            {"role": "assistant", "content": "I found a likely helper in src/utils.py."},
        ],
    )

    assert result.is_task_end is True
    assert result.message == TASK_END_MARKER
    assert called["value"] is False


def test_user_agent_allows_one_extra_follow_up_after_goals_if_assistant_asks(monkeypatch) -> None:
    agent = _build_agent()
    monkeypatch.setattr(agent, "call_model", lambda prompt: "It was the helper under src/utils.py.")

    result = agent.generate_message(
        blueprint={
            "goals": ["Inspect the repo", "Find the helper implementation"],
            "user_agent_config": {
                "role": "engineer",
                "personality": "brief",
                "knowledge_boundary": "repo-only",
            },
            "end_condition": "The user found the relevant code.",
        },
        messages=[
            {"role": "user", "content": "Can you inspect the repo?"},
            {"role": "assistant", "content": "I checked the structure and found the main folders."},
            {"role": "user", "content": "Please look for the helper implementation too."},
            {"role": "assistant", "content": "I found several matches. Which path do you want me to open?"},
        ],
    )

    assert result.is_task_end is False
    assert "src/utils.py" in result.message


def test_user_agent_ends_after_follow_up_when_assistant_stops_asking(monkeypatch) -> None:
    agent = _build_agent()
    called = {"value": False}

    def fake_call_model(prompt: str) -> str:
        del prompt
        called["value"] = True
        return "This should not be used."

    monkeypatch.setattr(agent, "call_model", fake_call_model)

    result = agent.generate_message(
        blueprint={
            "goals": ["Inspect the repo", "Find the helper implementation"],
            "user_agent_config": {
                "role": "engineer",
                "personality": "brief",
                "knowledge_boundary": "repo-only",
            },
            "end_condition": "The user found the relevant code.",
        },
        messages=[
            {"role": "user", "content": "Can you inspect the repo?"},
            {"role": "assistant", "content": "I checked the structure and found the main folders."},
            {"role": "user", "content": "Please look for the helper implementation too."},
            {"role": "assistant", "content": "I found several matches. Which path do you want me to open?"},
            {"role": "user", "content": "Please open src/utils.py."},
            {"role": "assistant", "content": "The helper is defined there."},
        ],
    )

    assert result.is_task_end is True
    assert result.message == TASK_END_MARKER
    assert called["value"] is False


def test_user_agent_allows_multiple_follow_up_turns_until_cap(monkeypatch) -> None:
    agent = _build_agent()
    monkeypatch.setattr(
        agent,
        "call_model",
        lambda prompt: "Jordan is fine, and please use my main number.",
    )

    result = agent.generate_message(
        blueprint={
            "goals": ["Inspect the repo", "Find the helper implementation"],
            "user_agent_config": {
                "role": "engineer",
                "personality": "brief",
                "knowledge_boundary": "repo-only",
            },
            "end_condition": "The user found the relevant code.",
        },
        messages=[
            {"role": "user", "content": "Can you inspect the repo?"},
            {"role": "assistant", "content": "I checked the structure and found the main folders."},
            {"role": "user", "content": "Please look for the helper implementation too."},
            {"role": "assistant", "content": "I found several matches. Which path do you want me to open?"},
            {"role": "user", "content": "Please open src/utils.py."},
            {"role": "assistant", "content": "I found the helper. What name should I put in the confirmation message?"},
        ],
    )

    assert result.is_task_end is False
    assert "Jordan" in result.message


def test_user_agent_ends_after_follow_up_cap(monkeypatch) -> None:
    agent = _build_agent()
    called = {"value": False}

    def fake_call_model(prompt: str) -> str:
        del prompt
        called["value"] = True
        return "This should not be used."

    monkeypatch.setattr(agent, "call_model", fake_call_model)

    result = agent.generate_message(
        blueprint={
            "goals": ["Inspect the repo", "Find the helper implementation"],
            "user_agent_config": {
                "role": "engineer",
                "personality": "brief",
                "knowledge_boundary": "repo-only",
            },
            "end_condition": "The user found the relevant code.",
        },
        messages=[
            {"role": "user", "content": "Can you inspect the repo?"},
            {"role": "assistant", "content": "I checked the structure and found the main folders."},
            {"role": "user", "content": "Please look for the helper implementation too."},
            {"role": "assistant", "content": "I found several matches. Which path do you want me to open?"},
            {"role": "user", "content": "Please open src/utils.py."},
            {"role": "assistant", "content": "I found the helper. What name should I put in the confirmation message?"},
            {"role": "user", "content": "Jordan is fine."},
            {"role": "assistant", "content": "Thanks. Which phone number should I use?"},
            {"role": "user", "content": "Use my main number."},
            {"role": "assistant", "content": "Anything else should I include?"},
            {"role": "user", "content": "No, that's all."},
            {"role": "assistant", "content": "Understood. One more detail: should I send it now?"},
        ],
    )

    assert result.is_task_end is True
    assert result.message == TASK_END_MARKER
    assert called["value"] is False


def test_user_agent_normalizes_simple_square_bracket_placeholders(monkeypatch) -> None:
    agent = _build_agent()
    monkeypatch.setattr(agent, "call_model", lambda prompt: "Please sign it as [my name].")

    result = agent.generate_message(
        blueprint={
            "goals": ["Reply to the message"],
            "user_agent_config": {
                "role": "engineer",
                "personality": "brief",
                "knowledge_boundary": "repo-only",
            },
            "end_condition": "The message is ready.",
        },
        messages=[],
        user_message_count=0,
    )

    assert result.is_task_end is False
    assert "[" not in result.message
    assert "my name" in result.message
