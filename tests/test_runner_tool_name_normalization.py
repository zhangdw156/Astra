from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from astra.agent._tool_agent import ToolAgentConfig
from astra.agent._user_agent import UserAgentConfig
from astra.simulation.config import MCPRuntimeConfig, SimulationRunnerConfig
from astra.simulation.runner import SimulationRunner


def build_runner() -> SimulationRunner:
    return SimulationRunner(
        config=SimulationRunnerConfig(
            runtime=MCPRuntimeConfig(
                host="127.0.0.1",
                port=19099,
                transport="sse",
                server_name="skill-tools",
            )
        ),
        user_agent_config=UserAgentConfig(
            prompt_path=Path("src/astra/prompts/user_agent.md"),
        ),
        tool_agent_config=ToolAgentConfig(
            prompt_path=Path("src/astra/prompts/tool_agent.md"),
        ),
    )


def test_build_turn_validation_accepts_mcp_prefixed_tool_names() -> None:
    runner = build_runner()
    validation = runner.build_turn_validation(
        blueprint={"possible_tool_calls": [["convert"]]},
        goal_index=1,
        assistant_tool_calls=[SimpleNamespace(name="skill-tools-convert")],
        assistant_message="done",
    )

    assert validation["tool_calls_within_blueprint"] is True
    assert validation["unexpected_tool_names"] == []
    assert validation["normalized_tool_names"] == ["convert"]
