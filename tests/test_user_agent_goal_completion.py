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


def test_user_agent_ends_after_one_extra_follow_up_turn(monkeypatch) -> None:
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
