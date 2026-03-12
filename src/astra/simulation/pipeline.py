from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..agent._eval_agent import EvalAgent
from ..agent._planner_agent import PlannerAgent
from ..utils import logger

from .config import SynthesisPipelineConfig
from .mcp_runtime import LocalMCPRuntime
from .runner import SimulationRunner
from .store import ArtifactStore, to_jsonable
from .types import BatchSynthesisResult, SynthesisSampleResult


class SynthesisPipeline:
    """
    样本合成流水线。

    单条样本流程：
    planner -> blueprint
    runner  -> trajectory
    eval    -> evaluation

    批量流程：
    遍历 persona_texts，按顺序执行单条样本流程，并统一管理 artifacts。
    """

    def __init__(
        self,
        *,
        config: SynthesisPipelineConfig,
        planner_agent: PlannerAgent,
        simulation_runner: SimulationRunner,
        eval_agent: EvalAgent | None = None,
    ):
        self.config = config.normalized()
        self.planner_agent = planner_agent
        self.simulation_runner = simulation_runner
        self.eval_agent = eval_agent

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def run_sample(
        self,
        *,
        skill_dir: Path,
        persona_text: str,
        sample_index: int,
        tools_path: Path | None = None,
        run_id: str | None = None,
        runtime: LocalMCPRuntime | None = None,
    ) -> SynthesisSampleResult:
        """
        运行单条样本：
        planner -> runner -> eval
        """
        tools_path = self.resolve_tools_path(skill_dir=skill_dir, tools_path=tools_path)
        actual_run_id = run_id or f"sample_{sample_index:06d}"

        blueprint_bundle = self.planner_agent.generate(
            skill_dir=skill_dir,
            persona_text=persona_text,
        )
        blueprint = blueprint_bundle.blueprint

        trajectory = self.simulation_runner.run(
            blueprint=blueprint,
            tools_path=tools_path,
            run_id=actual_run_id,
            runtime=runtime,
        )

        evaluation = None
        if self.config.evaluate_after_run:
            if self.eval_agent is None:
                raise RuntimeError("配置要求 evaluate_after_run=True，但未提供 EvalAgent")

            evaluation_bundle = self.eval_agent.evaluate(
                trajectory=to_jsonable(trajectory),
                blueprint=blueprint,
            )
            evaluation = evaluation_bundle.result

        accepted = self.decide_acceptance(evaluation)

        return SynthesisSampleResult(
            sample_index=sample_index,
            run_id=actual_run_id,
            blueprint=blueprint,
            trajectory=trajectory,
            evaluation=evaluation,
            accepted=accepted,
            error="",
        )

    def run_batch(
        self,
        *,
        skill_dir: Path,
        persona_texts: Iterable[str],
        tools_path: Path | None = None,
    ) -> BatchSynthesisResult:
        """
        批量运行样本合成流程，并保存 artifacts。
        """
        pipeline_errors = self.config.validate_basic()
        if pipeline_errors:
            raise ValueError("; ".join(pipeline_errors))

        tools_path = self.resolve_tools_path(skill_dir=skill_dir, tools_path=tools_path)
        store = ArtifactStore(self.config.output_root)

        runtime: LocalMCPRuntime | None = None
        if self.config.reuse_runtime:
            runtime = self.simulation_runner.build_runtime(tools_path=tools_path)
            runtime.start()

        samples: list[SynthesisSampleResult] = []
        succeeded_count = 0
        failed_count = 0
        accepted_count = 0
        rejected_count = 0

        try:
            for sample_index, persona_text in enumerate(persona_texts):
                try:
                    result = self.run_sample(
                        skill_dir=skill_dir,
                        persona_text=persona_text,
                        sample_index=sample_index,
                        tools_path=tools_path,
                        runtime=runtime,
                    )
                    samples.append(result)
                    succeeded_count += 1

                    if result.accepted:
                        accepted_count += 1
                    else:
                        rejected_count += 1

                    self.persist_sample(store=store, result=result)

                    if self.config.save_manifest:
                        store.append_manifest_record(
                            self.build_manifest_record(result=result)
                        )

                except Exception as exc:
                    failed_count += 1
                    failure_result = SynthesisSampleResult(
                        sample_index=sample_index,
                        run_id=f"sample_{sample_index:06d}",
                        blueprint=None,
                        trajectory=None,
                        evaluation=None,
                        accepted=False,
                        error=str(exc),
                    )
                    samples.append(failure_result)

                    logger.error(
                        "Sample {} failed: {}",
                        sample_index,
                        exc,
                    )

                    if self.config.save_manifest:
                        store.append_manifest_record(
                            self.build_manifest_record(result=failure_result)
                        )

                    if self.config.fail_fast:
                        raise

            batch_result = BatchSynthesisResult(
                total_count=len(samples),
                succeeded_count=succeeded_count,
                failed_count=failed_count,
                accepted_count=accepted_count,
                rejected_count=rejected_count,
                samples=samples,
            )

            if self.config.save_manifest:
                store.write_summary(to_jsonable(batch_result))

            return batch_result

        finally:
            if runtime is not None:
                runtime.stop()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def resolve_tools_path(
        self,
        *,
        skill_dir: Path,
        tools_path: Path | None = None,
    ) -> Path:
        """
        解析 tools.jsonl 路径。
        """
        if tools_path is not None:
            return tools_path.resolve() if tools_path.is_absolute() else tools_path.resolve()

        return (skill_dir / "tools.jsonl").resolve()

    def decide_acceptance(self, evaluation) -> bool:
        """
        根据 pipeline config 和 evaluation 结果决定样本是否 accepted。
        """
        if evaluation is None:
            return True

        if self.config.min_eval_score is not None:
            if evaluation.score < self.config.min_eval_score:
                return False

        if self.config.allowed_hallucination_risks is not None:
            if evaluation.hallucination_risk not in self.config.allowed_hallucination_risks:
                return False

        return True

    def persist_sample(
        self,
        *,
        store: ArtifactStore,
        result: SynthesisSampleResult,
    ) -> None:
        """
        将单条样本产物写入 artifacts。
        """
        if self.config.save_blueprint and result.blueprint is not None:
            store.write_blueprint(result.sample_index, result.blueprint)

        if self.config.save_trajectory and result.trajectory is not None:
            store.write_trajectory(result.sample_index, result.trajectory)

        if self.config.save_evaluation and result.evaluation is not None:
            store.write_evaluation(result.sample_index, result.evaluation)

    def build_manifest_record(
        self,
        *,
        result: SynthesisSampleResult,
    ) -> dict:
        """
        构造 manifest.jsonl 的单条记录。
        """
        return {
            "sample_index": result.sample_index,
            "run_id": result.run_id,
            "accepted": result.accepted,
            "error": result.error,
            "blueprint_id": (
                result.blueprint.get("blueprint_id", "")
                if result.blueprint is not None
                else ""
            ),
            "trajectory_id": (
                result.trajectory.trajectory_id
                if result.trajectory is not None
                else ""
            ),
            "score": (
                result.evaluation.score
                if result.evaluation is not None
                else None
            ),
            "hallucination_risk": (
                result.evaluation.hallucination_risk
                if result.evaluation is not None
                else None
            ),
        }