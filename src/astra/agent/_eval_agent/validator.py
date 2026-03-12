from __future__ import annotations

import json
import re


class EvalAgentValidator:
    """
    负责：
    1. 从模型回复中提取 JSON
    2. 校验评估结果 schema
    """

    REQUIRED_FIELDS = [
        "score",
        "hallucination_risk",
        "task_completion_score",
        "reason",
    ]

    ALLOWED_FIELDS = {
        "score",
        "hallucination_risk",
        "task_completion_score",
        "reason",
    }

    ALLOWED_HALLUCINATION_RISKS = {
        "none",
        "low",
        "medium",
        "high",
    }

    @staticmethod
    def extract_json_from_response(text: str) -> dict:
        """
        从模型回复中提取 JSON。

        允许以下情况：
        1. ```json ... ```
        2. ``` ... ```
        3. 前后带说明文字，只取第一个 { 到最后一个 } 的片段
        4. 直接就是 JSON
        """
        text = text.strip()

        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fenced:
            return json.loads(fenced.group(1).strip())

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])

        return json.loads(text)

    @staticmethod
    def count_sentences(text: str) -> int:
        """
        粗略统计句子数。
        支持中英文常见句末标点。
        """
        parts = re.split(r"[.!?。！？]+", text.strip())
        return len([part for part in parts if part.strip()])

    @classmethod
    def validate(cls, data: dict) -> list[str]:
        """
        校验评估结果格式，返回错误列表；空列表表示通过。
        """
        errors: list[str] = []

        for field in cls.REQUIRED_FIELDS:
            if field not in data:
                errors.append(f"缺少必填字段: {field}")

        for key in data:
            if key not in cls.ALLOWED_FIELDS:
                errors.append(f"存在未允许字段: {key}")

        if "score" in data:
            score = data["score"]
            if not isinstance(score, (int, float)):
                errors.append("score 必须为数字")
            elif not (0.0 <= float(score) <= 5.0):
                errors.append(f"score 必须在 [0.0, 5.0] 范围内: {score}")

        if "task_completion_score" in data:
            task_completion_score = data["task_completion_score"]
            if not isinstance(task_completion_score, (int, float)):
                errors.append("task_completion_score 必须为数字")
            elif not (0.0 <= float(task_completion_score) <= 1.0):
                errors.append(
                    "task_completion_score 必须在 [0.0, 1.0] 范围内: "
                    f"{task_completion_score}"
                )

        if "hallucination_risk" in data:
            hallucination_risk = data["hallucination_risk"]
            if not isinstance(hallucination_risk, str) or not hallucination_risk.strip():
                errors.append("hallucination_risk 必须为非空字符串")
            elif hallucination_risk not in cls.ALLOWED_HALLUCINATION_RISKS:
                errors.append(
                    "hallucination_risk 必须为以下之一: "
                    f"{sorted(cls.ALLOWED_HALLUCINATION_RISKS)}"
                )

        if "reason" in data:
            reason = data["reason"]
            if not isinstance(reason, str) or not reason.strip():
                errors.append("reason 必须为非空字符串")
            else:
                sentence_count = cls.count_sentences(reason)
                if not (2 <= sentence_count <= 8):
                    errors.append(
                        f"reason 句子数必须在 [2, 8] 范围内，当前为: {sentence_count}"
                    )

        return errors