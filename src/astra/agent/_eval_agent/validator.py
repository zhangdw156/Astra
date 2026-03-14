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
    def _load_first_json_object(text: str) -> dict:
        """
        从文本中解析第一个 JSON 对象，允许后面跟额外解释文字。
        """
        decoder = json.JSONDecoder()
        stripped = text.lstrip()
        obj, _ = decoder.raw_decode(stripped)
        if not isinstance(obj, dict):
            raise ValueError("评估结果必须是 JSON 对象")
        return obj

    @staticmethod
    def _collect_json_object_candidates(text: str) -> list[dict]:
        """
        扫描文本中的所有 JSON 对象候选，优先选择最像评估结果的对象。
        """
        decoder = json.JSONDecoder()
        candidates: list[dict] = []
        seen: set[tuple[str, ...]] = set()

        start = 0
        while True:
            start = text.find("{", start)
            if start == -1:
                break

            try:
                obj, _ = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                start += 1
                continue

            if isinstance(obj, dict):
                key = tuple(sorted(obj.keys()))
                if key not in seen:
                    candidates.append(obj)
                    seen.add(key)

            start += 1

        return candidates

    @classmethod
    def _select_best_candidate(cls, candidates: list[dict]) -> dict:
        if not candidates:
            raise ValueError("未找到可解析的评估 JSON 对象")

        def sort_key(candidate: dict) -> tuple[int, int]:
            required_count = sum(1 for field in cls.REQUIRED_FIELDS if field in candidate)
            return (required_count, len(json.dumps(candidate, ensure_ascii=False)))

        return max(candidates, key=sort_key)

    @classmethod
    def extract_json_from_response(cls, text: str) -> dict:
        """
        从模型回复中提取 JSON。

        允许以下情况：
        1. ```json ... ```
        2. ``` ... ```
        3. 前后带说明文字，只取第一个 { 到最后一个 } 的片段
        4. 直接就是 JSON
        """
        text = text.strip()
        candidates: list[dict] = []

        fenced_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        for block in fenced_blocks:
            candidates.extend(cls._collect_json_object_candidates(block.strip()))

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.extend(cls._collect_json_object_candidates(text[start : end + 1]))

        candidates.extend(cls._collect_json_object_candidates(text))
        if candidates:
            return cls._select_best_candidate(candidates)

        return cls._load_first_json_object(text)

    @staticmethod
    def count_sentences(text: str) -> int:
        """
        粗略统计句子数。
        支持中英文常见句末标点。
        """
        parts = re.split(r"[.!?。！？]+", text.strip())
        return len([part for part in parts if part.strip()])

    @staticmethod
    def split_sentences(text: str) -> list[str]:
        """
        粗略切分句子并尽量保留原始句末标点。
        """
        matches = re.findall(r"[^.!?。！？]+(?:[.!?。！？]+|$)", text.strip())
        return [item.strip() for item in matches if item.strip()]

    @classmethod
    def normalize(cls, data: dict) -> dict:
        """
        对模型输出做轻量归一化，避免微小格式偏差直接导致样本失败。
        当前仅处理过长的 reason：保留前 8 句。
        """
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        reason = normalized.get("reason")
        if isinstance(reason, str):
            sentences = cls.split_sentences(reason)
            if len(sentences) > 8:
                normalized["reason"] = " ".join(sentences[:8]).strip()
        return normalized

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
