from __future__ import annotations

import importlib.util
from pathlib import Path

from astra.simulation.store import to_jsonable
from astra.simulation.types import SimulationResult, SimulationTurn


def load_export_module():
    module_path = (
        Path("/home/zhang/work/Astra")
        / "exps"
        / "data_synthesis_workflow"
        / "export_one_trajectory_demo.py"
    )
    spec = importlib.util.spec_from_file_location(
        "export_one_trajectory_demo", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_trajectory_format_is_export_compatible() -> None:
    export_module = load_export_module()

    trajectory = SimulationResult(
        run_id="sample_000001",
        trajectory_id="traj-1",
        blueprint_id="bp-1",
        skill_name="3429_unit-convert",
        persona_id="persona-1",
        tools=[
            {
                "name": "convert",
                "description": "Convert units",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "from_unit": {"type": "string"},
                        "to_unit": {"type": "string"},
                    },
                    "required": ["value", "from_unit", "to_unit"],
                },
            }
        ],
        messages=[
            {"role": "user", "content": "Convert 100 cm to m."},
            {
                "role": "assistant",
                "content": "",
                "function_call": {
                    "name": "skill-tools-convert",
                    "arguments": '{"value": 100, "from_unit": "cm", "to_unit": "m"}',
                },
            },
            {
                "role": "function",
                "name": "skill-tools-convert",
                "content": '{"category":"length","input":{"value":100,"unit":"cm"},"output":{"value":1,"unit":"m"}}',
            },
            {
                "role": "assistant",
                "content": "100 cm equals 1 m.",
            },
        ],
        structured_turns=[
            SimulationTurn(
                turn_index=1,
                goal_index=1,
                goal_text="Convert 100 cm to m",
                user_message="Convert 100 cm to m.",
                assistant_message="100 cm equals 1 m.",
                tool_calls=[
                    {
                        "name": "skill-tools-convert",
                        "arguments": '{"value": 100, "from_unit": "cm", "to_unit": "m"}',
                        "result": '{"category":"length","input":{"value":100,"unit":"cm"},"output":{"value":1,"unit":"m"}}',
                    }
                ],
                execution_time_ms=10,
                validation={"tool_execution_succeeded": True},
            )
        ],
        validation={"ended_normally": True},
        final_tool_state={"last_conversion": {"value": 1, "unit": "m"}},
    )

    exported = export_module.build_output_record(
        to_jsonable(trajectory),
        source_trajectory_path="artifacts/pipeline4_results/3429_unit-convert/0/trajectory.json",
    )

    assert exported["run_id"] == "sample_000001"
    assert exported["skill_name"] == "3429_unit-convert"
    assert exported["tools"][0]["name"] == "convert"
    assert exported["messages"][0]["role"] == "system"
    assert exported["messages"][1] == {
        "role": "user",
        "content": "Convert 100 cm to m.",
    }
    assert "<tool_call>" in exported["messages"][2]["content"]
    assert '"name":"convert"' in exported["messages"][2]["content"]
    assert exported["messages"][3]["role"] == "user"
    assert "<tool_response>" in exported["messages"][3]["content"]
    assert exported["messages"][4] == {
        "role": "assistant",
        "content": "100 cm equals 1 m.",
    }
