from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from astra.agent._eval_agent.agent import EvalAgent, OPENAI_REQUEST_TIMEOUT_SEC as EVAL_TIMEOUT
from astra.agent._eval_agent.config import EvalAgentConfig
from astra.agent._planner_agent.agent import PlannerAgent, OPENAI_REQUEST_TIMEOUT_SEC as PLANNER_TIMEOUT
from astra.agent._planner_agent.config import PlannerAgentConfig
from astra.agent._user_agent.agent import UserAgent, OPENAI_REQUEST_TIMEOUT_SEC as USER_TIMEOUT
from astra.agent._user_agent.config import UserAgentConfig


class _FakeCompletions:
    def __init__(self, content: str):
        self._content = content

    def create(self, **_: object):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))]
        )


class _FakeClient:
    def __init__(self, recorder: dict[str, object], content: str, **kwargs: object):
        recorder.update(kwargs)
        self.chat = SimpleNamespace(completions=_FakeCompletions(content))


def test_planner_agent_uses_openai_timeout(monkeypatch) -> None:
    import astra.agent._planner_agent.agent as module

    recorder: dict[str, object] = {}
    monkeypatch.setattr(module.astra_config, "get_planner_agent_api_key", lambda: "k")
    monkeypatch.setattr(module.astra_config, "get_planner_agent_model", lambda: "m")
    monkeypatch.setattr(module.astra_config, "get_planner_agent_base_url", lambda: "http://x")
    monkeypatch.setattr(
        module,
        "OpenAI",
        lambda **kwargs: _FakeClient(recorder, '{"goals":["a"],"possible_tool_calls":[[]],"user_agent_config":{},"end_condition":"done"}', **kwargs),
    )

    agent = PlannerAgent(
        PlannerAgentConfig(prompt_path=Path("src/astra/prompts/planner_agent.md"))
    )
    raw = agent.call_model("hello")
    assert raw
    assert recorder["timeout"] == PLANNER_TIMEOUT
    assert recorder["max_retries"] == 2


def test_user_agent_uses_openai_timeout(monkeypatch) -> None:
    import astra.agent._user_agent.agent as module

    recorder: dict[str, object] = {}
    monkeypatch.setattr(module.astra_config, "get_user_agent_api_key", lambda: "k")
    monkeypatch.setattr(module.astra_config, "get_user_agent_model", lambda: "m")
    monkeypatch.setattr(module.astra_config, "get_user_agent_base_url", lambda: "http://x")
    monkeypatch.setattr(
        module,
        "OpenAI",
        lambda **kwargs: _FakeClient(recorder, "user reply", **kwargs),
    )

    agent = UserAgent(
        UserAgentConfig(prompt_path=Path("src/astra/prompts/user_agent.md"))
    )
    raw = agent.call_model("hello")
    assert raw == "user reply"
    assert recorder["timeout"] == USER_TIMEOUT
    assert recorder["max_retries"] == 2


def test_eval_agent_uses_openai_timeout(monkeypatch) -> None:
    import astra.agent._eval_agent.agent as module

    recorder: dict[str, object] = {}
    monkeypatch.setattr(module.astra_config, "get_eval_agent_api_key", lambda: "k")
    monkeypatch.setattr(module.astra_config, "get_eval_agent_model", lambda: "m")
    monkeypatch.setattr(module.astra_config, "get_eval_agent_base_url", lambda: "http://x")
    monkeypatch.setattr(
        module,
        "OpenAI",
        lambda **kwargs: _FakeClient(
            recorder,
            '{"score":1,"hallucination_risk":"low","task_completion_score":1,"reason":"ok"}',
            **kwargs,
        ),
    )

    agent = EvalAgent(
        EvalAgentConfig(prompt_path=Path("src/astra/prompts/eval_agent.md"))
    )
    raw = agent.call_model("hello")
    assert raw
    assert recorder["timeout"] == EVAL_TIMEOUT
    assert recorder["max_retries"] == 2
