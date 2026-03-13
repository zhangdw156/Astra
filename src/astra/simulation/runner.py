from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from ..agent._assistant_agent import AssistantAgent, AssistantAgentConfig
from ..agent._user_agent import UserAgent, UserAgentConfig
from ..agent._tool_agent import ToolAgentConfig
from ..envs.validation import compare_state
from ..utils import logger

from .config import SimulationRunnerConfig
from .mcp_runtime import LocalMCPRuntime
from .types import SimulationResult, SimulationTurn


class SimulationRunner:
    """
    单条 trajectory 运行器。

    职责：
    1. 启动 / 复用本地 MCP runtime
    2. 驱动 UserAgent 与 AssistantAgent 多轮交互
    3. 维护唯一 canonical messages
    4. 根据 blueprint 做 turn-level / final-level 软校验
    5. 输出完整 trajectory 结果
    """

    def __init__(
        self,
        *,
        config: SimulationRunnerConfig,
        user_agent_config: UserAgentConfig,
        tool_agent_config: ToolAgentConfig,
    ):
        self.config = config
        self.user_agent = UserAgent(user_agent_config)
        self.tool_agent_config = tool_agent_config

        self._assistant_agent: AssistantAgent | None = None
        self._assistant_signature: tuple[str, tuple[str, ...]] | None = None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def build_runtime(self, *, skill_dir: Path, tools_path: Path) -> LocalMCPRuntime:
        """
        基于 tools.jsonl 构造本地 MCP runtime。
        """
        return LocalMCPRuntime(
            config=self.config.runtime,
            tool_agent_config=self.tool_agent_config,
            skill_dir=skill_dir,
            tools_path=tools_path,
            state_key=self.config.assistant_state_key,
        )

    def run(
        self,
        *,
        blueprint: dict[str, Any],
        skill_dir: Path,
        tools_path: Path,
        run_id: str | None = None,
        runtime: LocalMCPRuntime | None = None,
    ) -> SimulationResult:
        """
        运行单条 trajectory。
        """
        config_errors = self.config.validate_basic()
        if config_errors:
            raise ValueError("; ".join(config_errors))

        self.validate_blueprint_for_run(blueprint)

        actual_run_id = run_id or str(uuid.uuid4())
        own_runtime = runtime is None
        runtime = runtime or self.build_runtime(skill_dir=skill_dir, tools_path=tools_path)

        if own_runtime:
            runtime.start()

        try:
            runtime.reset_state(self.config.assistant_state_key)
            assistant_agent = self.ensure_assistant(runtime=runtime)
            initial_state = runtime.get_state(self.config.assistant_state_key)

            goals = blueprint.get("goals") or []
            messages: list[dict[str, Any]] = []
            turns: list[SimulationTurn] = []

            ended_normally = False
            hit_max_turns = False

            for turn_index in range(1, self.config.max_turns + 1):
                user_turn_count = self.user_agent.count_user_messages(messages)
                goal_index = min(user_turn_count + 1, len(goals)) if goals else 1
                goal_text = (
                    goals[goal_index - 1]
                    if goals and 1 <= goal_index <= len(goals)
                    else ""
                )

                user_result = self.user_agent.generate_message(
                    blueprint=blueprint,
                    messages=messages,
                    user_message_count=user_turn_count,
                )

                user_message = user_result.message

                if user_result.is_task_end:
                    if user_turn_count >= len(goals):
                        ended_normally = True
                        break

                    if self.config.early_task_end_policy == "fallback":
                        user_message = self.build_fallback_user_message(
                            blueprint=blueprint,
                            goal_index=goal_index,
                        )
                        logger.info(
                            "UserAgent 过早输出 [TASK_END]，已回退为 goal {} 的 fallback message",
                            goal_index,
                        )
                    elif self.config.early_task_end_policy == "stop":
                        ended_normally = True
                        break
                    else:
                        raise RuntimeError(
                            "UserAgent 在 goals 尚未全部推进前输出了 [TASK_END]"
                        )

                messages.append({"role": "user", "content": user_message})

                start_time = time.perf_counter()
                assistant_result = assistant_agent.run_turn(messages=messages)
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)

                messages.extend(assistant_result.messages)

                turn_validation = self.build_turn_validation(
                    blueprint=blueprint,
                    goal_index=goal_index,
                    assistant_tool_calls=assistant_result.tool_calls,
                    assistant_message=assistant_result.assistant_message,
                )

                turn = SimulationTurn(
                    turn_index=turn_index,
                    goal_index=goal_index,
                    goal_text=goal_text,
                    user_message=user_message,
                    assistant_message=assistant_result.assistant_message,
                    tool_calls=[
                        {
                            "name": call.name,
                            "arguments": call.arguments,
                            "result": call.result,
                        }
                        for call in assistant_result.tool_calls
                    ],
                    execution_time_ms=execution_time_ms,
                    validation=turn_validation,
                    before_state=(
                        runtime.state_transitions[-1].before_state
                        if runtime.state_transitions
                        else {}
                    ),
                    after_state=(
                        runtime.state_transitions[-1].after_state
                        if runtime.state_transitions
                        else {}
                    ),
                )
                turns.append(turn)

            else:
                hit_max_turns = True

            final_tool_state = runtime.get_state(self.config.assistant_state_key)

            final_validation = self.build_final_validation(
                blueprint=blueprint,
                turns=turns,
                final_tool_state=final_tool_state,
                ended_normally=ended_normally,
                hit_max_turns=hit_max_turns,
            )

            return SimulationResult(
                run_id=actual_run_id,
                trajectory_id=str(uuid.uuid4()),
                blueprint_id=str(blueprint.get("blueprint_id", "")),
                skill_name=str(blueprint.get("skill_name", "")),
                persona_id=str(blueprint.get("persona_id", "")),
                tools=runtime.tools,
                messages=messages,
                structured_turns=turns,
                validation=final_validation,
                final_tool_state=final_tool_state,
                initial_state=initial_state,
                scenario_id=runtime.scenario_id or str(blueprint.get("scenario_id", "")),
                environment_profile=runtime.environment_profile,
                state_transitions=list(runtime.state_transitions),
            )

        finally:
            if own_runtime:
                runtime.stop()

    # -------------------------------------------------------------------------
    # Runtime / Assistant
    # -------------------------------------------------------------------------

    def ensure_assistant(self, *, runtime: LocalMCPRuntime) -> AssistantAgent:
        """
        确保存在一个可复用的 AssistantAgent。

        关键策略：
        - 用固定 assistant_state_key 复用同一个 assistant
        - 每条样本运行前由 runtime.reset_state(...) 清空该 state 分区
        - 避免在 batch 中重复 create() 导致 qwen-agent patch 层层嵌套
        """
        signature = (runtime.url, runtime.tool_name_signature)

        if self._assistant_agent is not None and self._assistant_signature == signature:
            return self._assistant_agent

        assistant_config = AssistantAgentConfig(
            mcp_url=runtime.url,
            verbose=self.config.assistant_verbose,
            enable_mcp_patch=self.config.assistant_enable_mcp_patch,
            enable_json_patch=self.config.assistant_enable_json_patch,
        )
        assistant_agent = AssistantAgent(assistant_config)
        assistant_agent.create(state_key=self.config.assistant_state_key)

        self._assistant_agent = assistant_agent
        self._assistant_signature = signature
        return assistant_agent

    # -------------------------------------------------------------------------
    # Validation / Policies
    # -------------------------------------------------------------------------

    def validate_blueprint_for_run(self, blueprint: dict[str, Any]) -> None:
        """
        对 runner 真正依赖的 blueprint 字段做最小校验。
        """
        required_fields = ["goals", "user_agent_config", "end_condition"]
        for field in required_fields:
            if field not in blueprint:
                raise ValueError(f"blueprint 缺少字段: {field}")

        goals = blueprint.get("goals")
        if not isinstance(goals, list) or len(goals) == 0:
            raise ValueError("blueprint.goals 必须为非空数组")

        if self.config.validate_tool_calls:
            ptc = blueprint.get("possible_tool_calls")
            if ptc is not None:
                if not isinstance(ptc, list):
                    raise ValueError("blueprint.possible_tool_calls 必须为数组")
                if len(ptc) != len(goals):
                    raise ValueError(
                        "blueprint.possible_tool_calls 长度必须与 goals 长度一致"
                    )

    def build_fallback_user_message(
        self,
        *,
        blueprint: dict[str, Any],
        goal_index: int,
    ) -> str:
        """
        当 UserAgent 过早输出 [TASK_END] 时，构造一条保守 fallback 用户消息。
        """
        goals = blueprint.get("goals") or []
        index = goal_index - 1
        if 0 <= index < len(goals):
            return f"I'd also like help with this next part: {goals[index]}"
        return "I'd like help with the next step."

    def build_turn_validation(
        self,
        *,
        blueprint: dict[str, Any],
        goal_index: int,
        assistant_tool_calls: list[Any],
        assistant_message: str,
    ) -> dict[str, Any]:
        """
        构造单轮软校验结果。
        """
        result: dict[str, Any] = {
            "assistant_message_nonempty": bool((assistant_message or "").strip()),
        }

        if not self.config.validate_tool_calls:
            result["tool_call_validation_enabled"] = False
            return result

        possible_tool_calls = blueprint.get("possible_tool_calls") or []
        allowed_tool_names: list[str] = []
        if 1 <= goal_index <= len(possible_tool_calls):
            maybe_allowed = possible_tool_calls[goal_index - 1]
            if isinstance(maybe_allowed, list):
                allowed_tool_names = [str(x) for x in maybe_allowed]

        actual_tool_names = [call.name for call in assistant_tool_calls]
        unexpected_tool_names = [
            name for name in actual_tool_names if name not in allowed_tool_names
        ]

        result.update(
            {
                "tool_call_validation_enabled": True,
                "allowed_tool_names": allowed_tool_names,
                "actual_tool_names": actual_tool_names,
                "unexpected_tool_names": unexpected_tool_names,
                "tool_calls_within_blueprint": len(unexpected_tool_names) == 0,
            }
        )
        return result

    def build_final_validation(
        self,
        *,
        blueprint: dict[str, Any],
        turns: list[SimulationTurn],
        final_tool_state: dict[str, Any],
        ended_normally: bool,
        hit_max_turns: bool,
    ) -> dict[str, Any]:
        """
        构造最终运行级 validation。
        """
        goals = blueprint.get("goals") or []
        num_goals = len(goals)

        user_turn_count = len(turns)
        all_goals_received_user_turn = user_turn_count >= num_goals
        tool_call_validation_passed = all(
            turn.validation.get("tool_calls_within_blueprint", True)
            for turn in turns
        )
        final_assistant_message_nonempty = bool(
            turns and (turns[-1].assistant_message or "").strip()
        )
        final_state_diffs: list[dict[str, Any]] = []
        expected_final_state = blueprint.get("expected_final_state")
        if isinstance(expected_final_state, dict):
            final_state_diffs = compare_state(
                final_tool_state,
                expected_final_state,
                subset=True,
            )

        checkpoint_results: list[dict[str, Any]] = []
        state_checkpoints = blueprint.get("state_checkpoints")
        if isinstance(state_checkpoints, list):
            for checkpoint in state_checkpoints:
                if not isinstance(checkpoint, dict):
                    continue
                turn_index = checkpoint.get("turn_index")
                expected_state = checkpoint.get("expected_state")
                if not isinstance(turn_index, int) or not isinstance(expected_state, dict):
                    continue
                matched_turn = next(
                    (turn for turn in turns if turn.turn_index == turn_index),
                    None,
                )
                actual_state = matched_turn.after_state if matched_turn is not None else None
                checkpoint_results.append(
                    {
                        "turn_index": turn_index,
                        "diffs": compare_state(actual_state, expected_state, subset=True),
                    }
                )

        return {
            "ended_normally": ended_normally,
            "hit_max_turns": hit_max_turns,
            "num_goals": num_goals,
            "user_turn_count": user_turn_count,
            "all_goals_received_user_turn": all_goals_received_user_turn,
            "tool_call_validation_passed": tool_call_validation_passed,
            "final_assistant_message_nonempty": final_assistant_message_nonempty,
            "final_tool_state_nonempty": bool(final_tool_state),
            "final_state_diffs": final_state_diffs,
            "final_state_match": len(final_state_diffs) == 0,
            "state_checkpoints": checkpoint_results,
        }
