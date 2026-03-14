from __future__ import annotations

import json
import re
from pathlib import Path

from astra.agent._planner_agent_v2.agent import PlannerAgentV2
from astra.agent._planner_agent_v2.config import PlannerAgentV2Config


class FakeOpenCodeExecutor:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[str] = []

    def run(self, task_text: str, cwd: Path, verbose: bool = False) -> int:
        del cwd, verbose
        self.calls.append(task_text)
        match = re.search(r"Output blueprint path: `([^`]+)`", task_text)
        if match is None:
            match = re.search(r"Overwrite this file with exactly one valid JSON object: ([^\n]+)", task_text)
        if match is None:
            raise AssertionError(f"Could not find output path in task:\n{task_text}")

        output_path = Path(match.group(1).strip())
        payload = self.responses.pop(0)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
        return 0


def test_planner_agent_v2_reads_blueprint_file_from_executor() -> None:
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / "artifacts" / "env_top30_skills" / "3429_unit-convert"
    persona_path = root / "persona" / "persona_5K.jsonl"
    persona_text = persona_path.read_text(encoding="utf-8").splitlines()[0].strip()

    executor = FakeOpenCodeExecutor(
        [
            json.dumps(
                {
                    "goals": ["Convert centimeters to meters"],
                    "possible_tool_calls": [["convert"]],
                    "initial_state": {},
                    "expected_final_state": {},
                    "state_checkpoints": [],
                    "user_agent_config": {
                        "role": "analyst",
                        "personality": "brief",
                        "knowledge_boundary": "does not know tool internals",
                    },
                    "end_condition": "The conversion is complete.",
                }
            )
        ]
    )
    agent = PlannerAgentV2(
        PlannerAgentV2Config(
            prompt_path=root / "src" / "astra" / "prompts" / "planner_agent_v2.md"
        ),
        executor=executor,
    )

    result = agent.generate(skill_dir=skill_dir, persona_text=persona_text)

    assert result.blueprint["scenario_id"] == "default"
    assert result.blueprint["environment_profile"]["backend_mode"] == "program-direct"
    assert len(result.blueprint["goals"]) >= 2
    assert executor.calls


def test_planner_agent_v2_repairs_invalid_file_once() -> None:
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / "artifacts" / "env_top30_skills" / "3429_unit-convert"
    persona_path = root / "persona" / "persona_5K.jsonl"
    persona_text = persona_path.read_text(encoding="utf-8").splitlines()[0].strip()

    executor = FakeOpenCodeExecutor(
        [
            json.dumps({"role": "analyst"}),
            json.dumps(
                {
                    "goals": ["Convert centimeters to meters"],
                    "possible_tool_calls": [["convert"]],
                    "initial_state": {},
                    "expected_final_state": {},
                    "state_checkpoints": [],
                    "user_agent_config": {
                        "role": "analyst",
                        "personality": "brief",
                        "knowledge_boundary": "does not know tool internals",
                    },
                    "end_condition": "The conversion is complete.",
                }
            ),
        ]
    )
    agent = PlannerAgentV2(
        PlannerAgentV2Config(
            prompt_path=root / "src" / "astra" / "prompts" / "planner_agent_v2.md"
        ),
        executor=executor,
    )

    result = agent.generate(skill_dir=skill_dir, persona_text=persona_text)

    assert len(executor.calls) == 2
    assert len(result.blueprint["goals"]) >= 2
    assert result.blueprint["user_agent_config"]["role"] == "analyst"


def test_planner_agent_v2_sanitizes_overly_specific_expected_final_state() -> None:
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / "artifacts" / "env_top30_skills" / "1534_voipms-sms"
    persona_path = root / "persona" / "persona_5K.jsonl"
    persona_text = persona_path.read_text(encoding="utf-8").splitlines()[0].strip()

    executor = FakeOpenCodeExecutor(
        [
            json.dumps(
                {
                    "goals": ["Check available numbers", "Send a confirmation reply"],
                    "possible_tool_calls": [["list_dids"], ["get_sms", "send_sms"]],
                    "initial_state": {
                        "messages": [],
                        "next_id": 3,
                    },
                    "expected_final_state": {
                        "messages": [
                            {
                                "id": "sms_3",
                                "did": "15551234567",
                                "dst": "15557654321",
                                "direction": "outbound",
                                "message": "Yes, I can confirm the appointment.",
                                "timestamp": "2026-03-13T12:00:00Z",
                            }
                        ],
                        "next_id": 4,
                    },
                    "state_checkpoints": [],
                    "user_agent_config": {
                        "role": "designer",
                        "personality": "brief",
                        "knowledge_boundary": "does not know tool internals",
                    },
                    "end_condition": "The user has checked the numbers and sent the reply.",
                }
            )
        ]
    )
    agent = PlannerAgentV2(
        PlannerAgentV2Config(
            prompt_path=root / "src" / "astra" / "prompts" / "planner_agent_v2.md"
        ),
        executor=executor,
    )

    result = agent.generate(skill_dir=skill_dir, persona_text=persona_text)
    message_state = result.blueprint["expected_final_state"]["messages"][0]

    assert "timestamp" not in message_state
    assert "id" not in message_state
    assert message_state["did"] == "15551234567"
    assert message_state["dst"] == "15557654321"
    assert message_state["message"] == {"nonempty": True}
