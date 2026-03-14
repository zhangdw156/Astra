from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ..simulation import LocalMCPRuntime
from ..utils import logger
from .config import OpencodeDispatcherConfig, QueueStageConfig, SimulationWorkerConfig
from .job_store import SQLiteQueueStore
from .stages import EvalStageRunner, PlannerStageRunner, QueueStageFactory, SimulationStageRunner
from .types import JobRecord, SampleArtifacts, StageName


class SynthesisQueueCoordinator:
    def __init__(self, *, store: SQLiteQueueStore, output_root: Path):
        self.store = store
        self.output_root = output_root.resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)

    def submit_sample(
        self,
        *,
        sample_id: str,
        skill_dir: Path,
        persona_text: str,
        planner_priority: int = 0,
        max_retries: int = 2,
    ) -> SampleArtifacts:
        artifact_root = self.output_root / skill_dir.resolve().name / sample_id
        return self.store.submit_sample(
            sample_id=sample_id,
            skill_dir=skill_dir,
            persona_text=persona_text,
            artifact_root=artifact_root,
            planner_priority=planner_priority,
            max_retries=max_retries,
        )

    def submit_skill_batch(
        self,
        *,
        skill_dir: Path,
        persona_texts: list[str],
        sample_id_prefix: str = "sample",
        planner_priority: int = 0,
        max_retries: int = 2,
    ) -> list[SampleArtifacts]:
        artifacts: list[SampleArtifacts] = []
        skill_name = skill_dir.resolve().name
        for sample_index, persona_text in enumerate(persona_texts):
            sample_id = f"{skill_name}__{sample_id_prefix}_{sample_index:06d}"
            artifacts.append(
                self.submit_sample(
                    sample_id=sample_id,
                    skill_dir=skill_dir,
                    persona_text=persona_text,
                    planner_priority=planner_priority,
                    max_retries=max_retries,
                )
            )
        return artifacts


class OpenCodeDispatcher:
    def __init__(
        self,
        *,
        store: SQLiteQueueStore,
        stage_config: QueueStageConfig,
        dispatcher_config: OpencodeDispatcherConfig | None = None,
    ):
        self.store = store
        self.factory = QueueStageFactory(stage_config)
        self.config = dispatcher_config or OpencodeDispatcherConfig()
        errors = self.config.validate_basic()
        if errors:
            raise ValueError("; ".join(errors))
        self.planner_runner = PlannerStageRunner(store=store, factory=self.factory)
        self.eval_runner = EvalStageRunner(store=store, factory=self.factory)
        self.store.ensure_lane(self.config.lane_name)

    def run_forever(self) -> None:
        while True:
            handled = self.run_once()
            if not handled:
                time.sleep(self.config.poll_interval_sec)

    def run_once(self) -> bool:
        if not self.store.claim_lane(
            lane_name=self.config.lane_name,
            owner_id=self.config.worker_id,
            ttl_sec=self.config.lane_lease_ttl_sec,
        ):
            return False

        try:
            stage = self._choose_next_stage()
            if stage is None:
                return False

            job = self.store.claim_next_job(
                stage=stage,
                worker_id=self.config.worker_id,
                lease_ttl_sec=self.config.job_lease_ttl_sec,
            )
            if job is None and stage == "eval":
                job = self.store.claim_next_job(
                    stage="planner",
                    worker_id=self.config.worker_id,
                    lease_ttl_sec=self.config.job_lease_ttl_sec,
                )
            elif job is None and stage == "planner":
                job = self.store.claim_next_job(
                    stage="eval",
                    worker_id=self.config.worker_id,
                    lease_ttl_sec=self.config.job_lease_ttl_sec,
                )
            if job is None:
                return False

            try:
                if job.stage == "planner":
                    self.planner_runner.run(job)
                else:
                    self.eval_runner.run(job)
                return True
            except Exception as exc:
                self.store.fail_job(job=job, error=str(exc))
                logger.exception(
                    "Opencode dispatcher failed while running {} job {}",
                    job.stage,
                    job.job_id,
                )
                return True
        finally:
            self.store.release_lane(
                lane_name=self.config.lane_name,
                owner_id=self.config.worker_id,
            )

    def _choose_next_stage(self) -> StageName | None:
        pending_planner = self.store.count_available_jobs(stage="planner")
        pending_simulation = self.store.count_available_jobs(stage="simulation")
        pending_eval = self.store.count_available_jobs(stage="eval")

        if pending_planner == 0 and pending_eval == 0:
            return None

        planner_paused = (
            pending_simulation >= self.config.simulation_backlog_high
            or pending_eval >= self.config.eval_backlog_high
        )
        if pending_eval > 0 and (
            pending_simulation >= self.config.simulation_backlog_low or planner_paused
        ):
            return "eval"
        if pending_planner > 0 and not planner_paused and (
            pending_simulation < self.config.simulation_backlog_low or pending_eval == 0
        ):
            return "planner"
        if pending_eval > 0:
            return "eval"
        if pending_planner > 0:
            return "planner"
        return None


class SimulationWorker:
    def __init__(
        self,
        *,
        store: SQLiteQueueStore,
        stage_config: QueueStageConfig,
        worker_config: SimulationWorkerConfig,
    ):
        self.store = store
        self.factory = QueueStageFactory(stage_config)
        self.config = worker_config
        errors = self.config.validate_basic()
        if errors:
            raise ValueError("; ".join(errors))
        self.runner = self.factory.build_simulation_runner(port=self.config.port)
        self.stage_runner = SimulationStageRunner(store=store, factory=self.factory)
        self._current_skill_key: str | None = None
        self._runtime: LocalMCPRuntime | None = None

    def close(self) -> None:
        if self._runtime is not None:
            self._runtime.stop()
            self._runtime = None
        if self._current_skill_key is not None:
            self.store.release_skill_lease(
                skill_key=self._current_skill_key,
                owner_worker_id=self.config.worker_id,
            )
            self._current_skill_key = None

    def run_forever(self) -> None:
        while True:
            handled = self.run_once()
            if not handled:
                time.sleep(self.config.poll_interval_sec)

    def run_once(self) -> bool:
        if self._current_skill_key is not None:
            job = self._claim_preferred_skill_job()
            if job is not None:
                self._run_job(job)
                return True
            self._release_current_skill()

        for skill_key in self.store.list_candidate_simulation_skills():
            if not self.store.claim_skill_lease(
                skill_key=skill_key,
                owner_worker_id=self.config.worker_id,
                port=self.config.port,
                ttl_sec=self.config.skill_lease_ttl_sec,
            ):
                continue

            self._current_skill_key = skill_key
            job = self.store.claim_next_job(
                stage="simulation",
                worker_id=self.config.worker_id,
                lease_ttl_sec=self.config.job_lease_ttl_sec,
                preferred_skill_key=skill_key,
            )
            if job is None:
                self._release_current_skill()
                continue

            self._run_job(job)
            return True

        return False

    def _claim_preferred_skill_job(self) -> JobRecord | None:
        if self._current_skill_key is None:
            return None
        if not self.store.claim_skill_lease(
            skill_key=self._current_skill_key,
            owner_worker_id=self.config.worker_id,
            port=self.config.port,
            ttl_sec=self.config.skill_lease_ttl_sec,
        ):
            self._release_current_skill()
            return None
        return self.store.claim_next_job(
            stage="simulation",
            worker_id=self.config.worker_id,
            lease_ttl_sec=self.config.job_lease_ttl_sec,
            preferred_skill_key=self._current_skill_key,
        )

    def _run_job(self, job: JobRecord) -> None:
        payload = job.payload
        skill_dir = Path(str(payload["skill_dir"])).resolve()
        tools_path = Path(str(payload["tools_path"])).resolve()
        runtime = self._ensure_runtime(skill_dir=skill_dir, tools_path=tools_path)

        try:
            self.stage_runner.run(
                job,
                simulation_runner=self.runner,
                runtime=runtime,
            )
        except Exception as exc:
            self.store.fail_job(job=job, error=str(exc))
            logger.exception(
                "Simulation worker {} failed on job {}",
                self.config.worker_id,
                job.job_id,
            )

    def _ensure_runtime(self, *, skill_dir: Path, tools_path: Path) -> LocalMCPRuntime:
        skill_key = str(skill_dir)
        if self._runtime is not None and self._current_skill_key == skill_key:
            return self._runtime

        if self._runtime is not None:
            self._runtime.stop()
            self._runtime = None

        # TODO: 如果后续要支持更高并发，需要把 skill backend/runtime 改造成真正的会话隔离模型，
        # 这样同一个 skill 才能安全地并行运行多条轨迹，而不是继续依赖单 worker 独占一个 runtime。
        runtime = self.runner.build_runtime(skill_dir=skill_dir, tools_path=tools_path)
        runtime.start()
        self._runtime = runtime
        self._current_skill_key = skill_key
        return runtime

    def _release_current_skill(self) -> None:
        if self._current_skill_key is None:
            return
        if self._runtime is not None:
            self._runtime.stop()
            self._runtime = None
        self.store.release_skill_lease(
            skill_key=self._current_skill_key,
            owner_worker_id=self.config.worker_id,
        )
        self._current_skill_key = None
