from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationResult:
    """
    单条样本的结构化评估结果。
    """

    score: float
    hallucination_risk: str
    task_completion_score: float
    reason: str

    run_id: str = ""
    blueprint_id: str = ""
    trajectory_id: str = ""


@dataclass(slots=True)
class EvaluationBundle:
    """
    EvalAgent 一次评估的完整返回。
    """

    result: EvaluationResult
    prompt: str
    raw_response: str