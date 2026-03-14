from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..agent._eval_agent import EvaluationResult
from ..envs import StateTransitionRecord


@dataclass(slots=True)
class SimulationTurn:
    """
    单轮对话记录。
    """

    turn_index: int
    goal_index: int
    goal_text: str
    user_message: str
    assistant_message: str
    tool_calls: list[dict[str, Any]]
    execution_time_ms: int
    validation: dict[str, Any]
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SimulationResult:
    """
    单条 trajectory 运行结果。
    """

    run_id: str
    trajectory_id: str
    blueprint_id: str
    skill_name: str
    persona_id: str
    tools: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    structured_turns: list[SimulationTurn]
    validation: dict[str, Any]
    final_tool_state: dict[str, Any]
    initial_state: dict[str, Any] = field(default_factory=dict)
    scenario_id: str = ""
    environment_profile: dict[str, Any] | None = None
    state_transitions: list[StateTransitionRecord] = field(default_factory=list)


@dataclass(slots=True)
class SynthesisSampleResult:
    """
    单条样本的完整流水线结果。
    """

    sample_index: int
    run_id: str
    blueprint: dict[str, Any] | None = None
    trajectory: SimulationResult | None = None
    evaluation: EvaluationResult | None = None
    evaluation_artifacts: dict[str, Any] | None = None
    accepted: bool = False
    error: str = ""


@dataclass(slots=True)
class BatchSynthesisResult:
    """
    一次 batch 合成结果。
    """

    total_count: int
    succeeded_count: int
    failed_count: int
    accepted_count: int
    rejected_count: int
    samples: list[SynthesisSampleResult] = field(default_factory=list)
