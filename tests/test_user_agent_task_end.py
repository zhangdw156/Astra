from __future__ import annotations

from pathlib import Path

from astra.agent._user_agent.agent import TASK_END_MARKER, UserAgent
from astra.agent._user_agent.config import UserAgentConfig


def make_agent() -> UserAgent:
    return UserAgent(UserAgentConfig(prompt_path=Path("src/astra/prompts/user_agent.md")))


def test_user_agent_treats_pure_task_end_as_terminal(monkeypatch) -> None:
    agent = make_agent()
    monkeypatch.setattr(agent, "call_model", lambda prompt: TASK_END_MARKER)

    result = agent.generate_message(
        blueprint={
            "goals": ["goal 1"],
            "user_agent_config": {},
            "end_condition": "done",
        },
        messages=[],
        user_message_count=1,
    )

    assert result.is_task_end is True
    assert result.message == TASK_END_MARKER


def test_user_agent_treats_embedded_task_end_as_terminal_after_all_goals(monkeypatch) -> None:
    agent = make_agent()
    monkeypatch.setattr(
        agent,
        "call_model",
        lambda prompt: "We covered everything we needed here.\n\n[TASK_END]",
    )

    result = agent.generate_message(
        blueprint={
            "goals": ["goal 1", "goal 2", "goal 3"],
            "user_agent_config": {},
            "end_condition": "done",
        },
        messages=[],
        user_message_count=3,
    )

    assert result.is_task_end is True
    assert result.message == TASK_END_MARKER


def test_user_agent_strips_embedded_task_end_before_final_goal(monkeypatch) -> None:
    agent = make_agent()
    monkeypatch.setattr(
        agent,
        "call_model",
        lambda prompt: "Could you also check the remaining files?\n\n[TASK_END]",
    )

    result = agent.generate_message(
        blueprint={
            "goals": ["goal 1", "goal 2", "goal 3"],
            "user_agent_config": {},
            "end_condition": "done",
        },
        messages=[],
        user_message_count=1,
    )

    assert result.is_task_end is False
    assert TASK_END_MARKER not in result.message
    assert "remaining files" in result.message
