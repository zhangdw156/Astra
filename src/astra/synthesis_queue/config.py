from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..utils import config as astra_config


@dataclass(frozen=True, slots=True)
class QueueStageConfig:
    planner_prompt_path: Path
    user_prompt_path: Path
    tool_prompt_path: Path
    eval_prompt_path: Path
    project_root: Path = astra_config.get_project_root()
    planner_verbose: bool = False
    eval_verbose: bool = False
    planner_repair_attempts: int = 1
    eval_repair_attempts: int = 1
    eval_max_message_chars: int | None = 4000
    min_eval_score: float | None = None
    allowed_hallucination_risks: tuple[str, ...] | None = None
    simulation_max_turns: int = 12
    simulation_early_task_end_policy: str = "fallback"
    simulation_validate_tool_calls: bool = True
    simulation_assistant_state_key: str = "simulation"
    simulation_assistant_verbose: bool = False
    simulation_assistant_enable_mcp_patch: bool = True
    simulation_assistant_enable_json_patch: bool = True
    runtime_host: str = "127.0.0.1"
    runtime_transport: str = "sse"
    runtime_server_name: str = "skill-tools"
    runtime_start_timeout_sec: int = 30
    runtime_poll_interval_sec: float = 0.5
    user_model_temperature: float = 0.5
    tool_model_temperature: float = 0.3

    def normalized(self) -> "QueueStageConfig":
        return QueueStageConfig(
            planner_prompt_path=self.planner_prompt_path.resolve(),
            user_prompt_path=self.user_prompt_path.resolve(),
            tool_prompt_path=self.tool_prompt_path.resolve(),
            eval_prompt_path=self.eval_prompt_path.resolve(),
            project_root=self.project_root.resolve(),
            planner_verbose=self.planner_verbose,
            eval_verbose=self.eval_verbose,
            planner_repair_attempts=self.planner_repair_attempts,
            eval_repair_attempts=self.eval_repair_attempts,
            eval_max_message_chars=self.eval_max_message_chars,
            min_eval_score=self.min_eval_score,
            allowed_hallucination_risks=self.allowed_hallucination_risks,
            simulation_max_turns=self.simulation_max_turns,
            simulation_early_task_end_policy=self.simulation_early_task_end_policy,
            simulation_validate_tool_calls=self.simulation_validate_tool_calls,
            simulation_assistant_state_key=self.simulation_assistant_state_key,
            simulation_assistant_verbose=self.simulation_assistant_verbose,
            simulation_assistant_enable_mcp_patch=self.simulation_assistant_enable_mcp_patch,
            simulation_assistant_enable_json_patch=self.simulation_assistant_enable_json_patch,
            runtime_host=self.runtime_host,
            runtime_transport=self.runtime_transport,
            runtime_server_name=self.runtime_server_name,
            runtime_start_timeout_sec=self.runtime_start_timeout_sec,
            runtime_poll_interval_sec=self.runtime_poll_interval_sec,
            user_model_temperature=self.user_model_temperature,
            tool_model_temperature=self.tool_model_temperature,
        )

    def validate_basic(self) -> list[str]:
        errors: list[str] = []
        for name, path in (
            ("planner_prompt_path", self.planner_prompt_path),
            ("user_prompt_path", self.user_prompt_path),
            ("tool_prompt_path", self.tool_prompt_path),
            ("eval_prompt_path", self.eval_prompt_path),
        ):
            if not path.exists():
                errors.append(f"{name} 不存在: {path}")

        if self.planner_repair_attempts < 0:
            errors.append(
                f"planner_repair_attempts 不能小于 0: {self.planner_repair_attempts}"
            )
        if self.eval_repair_attempts < 0:
            errors.append(
                f"eval_repair_attempts 不能小于 0: {self.eval_repair_attempts}"
            )
        if self.eval_max_message_chars is not None and self.eval_max_message_chars <= 0:
            errors.append(
                "eval_max_message_chars 必须为正整数或 None: "
                f"{self.eval_max_message_chars}"
            )
        if self.simulation_max_turns <= 0:
            errors.append(
                f"simulation_max_turns 必须为正整数: {self.simulation_max_turns}"
            )
        if self.simulation_early_task_end_policy not in {"fallback", "stop", "error"}:
            errors.append(
                "simulation_early_task_end_policy 必须为 fallback / stop / error: "
                f"{self.simulation_early_task_end_policy}"
            )
        if self.min_eval_score is not None and not (0.0 <= self.min_eval_score <= 5.0):
            errors.append(
                f"min_eval_score 必须在 [0.0, 5.0]: {self.min_eval_score}"
            )
        if self.allowed_hallucination_risks is not None:
            allowed = {"none", "low", "medium", "high"}
            bad = [x for x in self.allowed_hallucination_risks if x not in allowed]
            if bad:
                errors.append(
                    "allowed_hallucination_risks 只能包含 none/low/medium/high: "
                    f"{bad}"
                )
        return errors


@dataclass(frozen=True, slots=True)
class OpencodeDispatcherConfig:
    worker_id: str = "opencode-dispatcher"
    lane_name: str = "opencode"
    poll_interval_sec: float = 1.0
    job_lease_ttl_sec: int = 1800
    lane_lease_ttl_sec: int = 1800
    simulation_backlog_low: int = 4
    simulation_backlog_high: int = 8
    eval_backlog_high: int = 8

    def validate_basic(self) -> list[str]:
        errors: list[str] = []
        if self.poll_interval_sec <= 0:
            errors.append(
                f"poll_interval_sec 必须为正数: {self.poll_interval_sec}"
            )
        if self.job_lease_ttl_sec <= 0:
            errors.append(
                f"job_lease_ttl_sec 必须为正整数: {self.job_lease_ttl_sec}"
            )
        if self.lane_lease_ttl_sec <= 0:
            errors.append(
                f"lane_lease_ttl_sec 必须为正整数: {self.lane_lease_ttl_sec}"
            )
        if self.simulation_backlog_low < 0:
            errors.append(
                "simulation_backlog_low 不能小于 0: "
                f"{self.simulation_backlog_low}"
            )
        if self.simulation_backlog_high < self.simulation_backlog_low:
            errors.append(
                "simulation_backlog_high 不能小于 simulation_backlog_low: "
                f"{self.simulation_backlog_high}"
            )
        if self.eval_backlog_high < 0:
            errors.append(
                f"eval_backlog_high 不能小于 0: {self.eval_backlog_high}"
            )
        return errors


@dataclass(frozen=True, slots=True)
class SimulationWorkerConfig:
    worker_id: str
    port: int
    poll_interval_sec: float = 1.0
    job_lease_ttl_sec: int = 1800
    skill_lease_ttl_sec: int = 1800

    def validate_basic(self) -> list[str]:
        errors: list[str] = []
        if not self.worker_id.strip():
            errors.append("worker_id 不能为空")
        if self.port <= 0:
            errors.append(f"port 必须为正整数: {self.port}")
        if self.poll_interval_sec <= 0:
            errors.append(
                f"poll_interval_sec 必须为正数: {self.poll_interval_sec}"
            )
        if self.job_lease_ttl_sec <= 0:
            errors.append(
                f"job_lease_ttl_sec 必须为正整数: {self.job_lease_ttl_sec}"
            )
        if self.skill_lease_ttl_sec <= 0:
            errors.append(
                f"skill_lease_ttl_sec 必须为正整数: {self.skill_lease_ttl_sec}"
            )
        return errors
