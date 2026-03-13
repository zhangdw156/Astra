from __future__ import annotations

from openai import OpenAI

from ...utils import config as astra_config
from ...utils import logger

from .config import EvalAgentConfig
from .prompt_builder import EvalAgentPromptBuilder
from .types import EvaluationBundle, EvaluationResult
from .validator import EvalAgentValidator


OPENAI_REQUEST_TIMEOUT_SEC = 120.0


class EvalAgent:
    """
    EvalAgent：根据 trajectory 与 blueprint 对单条样本进行评估打分。

    职责：
    1. 清理并构造评估视图
    2. 生成评估 prompt
    3. 调用模型
    4. 提取并校验结构化评分结果
    5. 注入程序控制字段
    """

    def __init__(self, config: EvalAgentConfig):
        self.config = config.normalized()
        self.prompt_builder = EvalAgentPromptBuilder(
            prompt_path=self.config.prompt_path,
            max_message_chars=self.config.max_message_chars,
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def evaluate(
        self,
        *,
        trajectory: dict,
        blueprint: dict,
    ) -> EvaluationBundle:
        """
        对单条样本进行评估，返回结构化评估结果与调试信息。
        """
        config_errors = self.config.validate_basic()
        if config_errors:
            raise ValueError("; ".join(config_errors))

        prompt = self.prompt_builder.build(
            blueprint=blueprint,
            trajectory=trajectory,
        )

        raw_response = self.call_model(prompt)
        parsed = EvalAgentValidator.extract_json_from_response(raw_response)
        parsed = EvalAgentValidator.normalize(parsed)

        validation_errors = EvalAgentValidator.validate(parsed)
        if validation_errors:
            raise ValueError("评估结果格式校验失败: " + "; ".join(validation_errors))

        result = self.build_evaluation_result(
            parsed=parsed,
            blueprint=blueprint,
            trajectory=trajectory,
        )

        return EvaluationBundle(
            result=result,
            prompt=prompt,
            raw_response=raw_response,
        )

    def build_evaluation_result(
        self,
        *,
        parsed: dict,
        blueprint: dict,
        trajectory: dict,
    ) -> EvaluationResult:
        """
        将解析后的 JSON 结果转成 EvaluationResult，并注入程序控制字段。
        """
        return EvaluationResult(
            score=float(parsed["score"]),
            hallucination_risk=str(parsed["hallucination_risk"]),
            task_completion_score=float(parsed["task_completion_score"]),
            reason=str(parsed["reason"]).strip(),
            run_id=str(trajectory.get("run_id", "")),
            blueprint_id=str(blueprint.get("blueprint_id", "")),
            trajectory_id=str(trajectory.get("trajectory_id", "")),
            diagnostics={
                "final_state_match": trajectory.get("validation", {}).get(
                    "final_state_match"
                ),
                "state_checkpoints": trajectory.get("validation", {}).get(
                    "state_checkpoints"
                ),
            },
        )

    # -------------------------------------------------------------------------
    # LLM
    # -------------------------------------------------------------------------

    def call_model(self, prompt: str) -> str:
        """
        调用模型生成评估结果原始文本。
        """
        api_key = astra_config.get_eval_agent_api_key()
        model = astra_config.get_eval_agent_model()
        base_url = astra_config.get_eval_agent_base_url()

        logger.info("Calling eval model: {}", model)
        logger.debug("Eval prompt length: {} chars", len(prompt))

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=OPENAI_REQUEST_TIMEOUT_SEC,
            max_retries=2,
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.model_temperature,
        )

        raw = (response.choices[0].message.content or "").strip()
        logger.debug("Eval raw response length: {} chars", len(raw))
        return raw
