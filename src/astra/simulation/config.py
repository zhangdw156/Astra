from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MCPRuntimeConfig:
    """
    本地轻量 MCP runtime 配置。

    说明：
    - host / port / transport: MCP 服务监听参数
    - server_name: FastMCP 服务名
    - start_timeout_sec: 启动等待超时
    - poll_interval_sec: 启动轮询间隔
    """

    host: str = "127.0.0.1"
    port: int = 8000
    transport: str = "sse"
    server_name: str = "skill-tools"
    start_timeout_sec: int = 30
    poll_interval_sec: float = 0.5

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/sse"

    def validate_basic(self) -> list[str]:
        errors: list[str] = []

        if not self.host.strip():
            errors.append("runtime.host 不能为空")
        if self.port <= 0:
            errors.append(f"runtime.port 必须为正整数: {self.port}")
        if self.transport not in {"sse"}:
            errors.append(f"runtime.transport 目前仅支持 sse: {self.transport}")
        if self.start_timeout_sec <= 0:
            errors.append(
                f"runtime.start_timeout_sec 必须为正整数: {self.start_timeout_sec}"
            )
        if self.poll_interval_sec <= 0:
            errors.append(
                f"runtime.poll_interval_sec 必须为正数: {self.poll_interval_sec}"
            )

        return errors


@dataclass(frozen=True, slots=True)
class SimulationRunnerConfig:
    """
    单条 trajectory 运行配置。

    说明：
    - max_turns: 安全上限
    - early_task_end_policy:
        - fallback: UserAgent 过早输出 [TASK_END] 时，自动补发一条 fallback 用户消息
        - stop: 直接接受结束
        - error: 直接报错
    - validate_tool_calls: 是否根据 blueprint.possible_tool_calls 做软校验
    - assistant_state_key: 运行时共享的 tool state 分区 key
    - assistant_*: AssistantAgent 构造参数
    - runtime: 本地 MCP runtime 配置
    """

    max_turns: int = 20
    early_task_end_policy: str = "fallback"
    validate_tool_calls: bool = True
    assistant_state_key: str = "simulation"
    assistant_verbose: bool = False
    assistant_enable_mcp_patch: bool = True
    assistant_enable_json_patch: bool = True
    assistant_request_timeout_sec: float = 120.0
    assistant_max_retries: int = 2
    assistant_max_llm_calls_per_run: int = 6
    runtime: MCPRuntimeConfig = field(default_factory=MCPRuntimeConfig)

    def validate_basic(self) -> list[str]:
        errors: list[str] = []

        if self.max_turns <= 0:
            errors.append(f"max_turns 必须为正整数: {self.max_turns}")

        if self.early_task_end_policy not in {"fallback", "stop", "error"}:
            errors.append(
                "early_task_end_policy 必须为 fallback / stop / error 之一: "
                f"{self.early_task_end_policy}"
            )

        if not self.assistant_state_key.strip():
            errors.append("assistant_state_key 不能为空")
        if self.assistant_request_timeout_sec <= 0:
            errors.append(
                "assistant_request_timeout_sec 必须为正数: "
                f"{self.assistant_request_timeout_sec}"
            )
        if self.assistant_max_retries < 0:
            errors.append(
                f"assistant_max_retries 不能小于 0: {self.assistant_max_retries}"
            )
        if self.assistant_max_llm_calls_per_run <= 0:
            errors.append(
                "assistant_max_llm_calls_per_run 必须为正整数: "
                f"{self.assistant_max_llm_calls_per_run}"
            )

        errors.extend(self.runtime.validate_basic())
        return errors


@dataclass(frozen=True, slots=True)
class SynthesisPipelineConfig:
    """
    批量合成流水线配置。

    说明：
    - output_root: artifacts 根目录
    - evaluate_after_run: 是否在 trajectory 后立即做评估
    - reuse_runtime: 是否在一个 batch 内复用同一个本地 MCP runtime
    - save_*: 是否保存各类产物
    - min_eval_score: 若设置，则低于该阈值的样本标记为 rejected
    - allowed_hallucination_risks: 若设置，则不在允许集合内的样本标记为 rejected
    - fail_fast: 某条样本失败时是否立刻终止整个 batch
    """

    output_root: Path
    evaluate_after_run: bool = True
    reuse_runtime: bool = True
    save_blueprint: bool = True
    save_trajectory: bool = True
    save_evaluation: bool = True
    save_manifest: bool = True
    min_eval_score: float | None = None
    allowed_hallucination_risks: tuple[str, ...] | None = None
    fail_fast: bool = False

    def normalized(self) -> "SynthesisPipelineConfig":
        return SynthesisPipelineConfig(
            output_root=self.output_root.resolve(),
            evaluate_after_run=self.evaluate_after_run,
            reuse_runtime=self.reuse_runtime,
            save_blueprint=self.save_blueprint,
            save_trajectory=self.save_trajectory,
            save_evaluation=self.save_evaluation,
            save_manifest=self.save_manifest,
            min_eval_score=self.min_eval_score,
            allowed_hallucination_risks=self.allowed_hallucination_risks,
            fail_fast=self.fail_fast,
        )

    def validate_basic(self) -> list[str]:
        errors: list[str] = []

        if self.min_eval_score is not None and not (0.0 <= self.min_eval_score <= 5.0):
            errors.append(
                f"min_eval_score 必须在 [0.0, 5.0] 范围内: {self.min_eval_score}"
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
