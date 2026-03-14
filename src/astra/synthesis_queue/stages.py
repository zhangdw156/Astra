from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..agent._eval_agent_v2 import EvalAgentV2, EvalAgentV2Config
from ..agent._planner_agent_v2 import PlannerAgentV2, PlannerAgentV2Config
from ..agent._tool_agent import ToolAgentConfig
from ..agent._user_agent import UserAgentConfig
from ..simulation import MCPRuntimeConfig, SimulationRunner, SimulationRunnerConfig, to_jsonable
from ..utils import logger
from .config import QueueStageConfig
from .job_store import SQLiteQueueStore
from .types import JobRecord


def atomic_write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    serialized = json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2)
    tmp_path.write_text(serialized, encoding="utf-8")
    os.replace(tmp_path, path)
    return path


def atomic_write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)
    return path


def load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"JSON 文件必须为对象: {path}")
    return raw


class QueueStageFactory:
    def __init__(self, config: QueueStageConfig):
        self.config = config.normalized()
        errors = self.config.validate_basic()
        if errors:
            raise ValueError("; ".join(errors))
        self._planner_agent: PlannerAgentV2 | None = None
        self._eval_agent: EvalAgentV2 | None = None

    def planner_agent(self) -> PlannerAgentV2:
        if self._planner_agent is None:
            self._planner_agent = PlannerAgentV2(
                PlannerAgentV2Config(
                    prompt_path=self.config.planner_prompt_path,
                    project_root=self.config.project_root,
                    verbose=self.config.planner_verbose,
                    repair_attempts=self.config.planner_repair_attempts,
                )
            )
        return self._planner_agent

    def eval_agent(self) -> EvalAgentV2:
        if self._eval_agent is None:
            self._eval_agent = EvalAgentV2(
                EvalAgentV2Config(
                    prompt_path=self.config.eval_prompt_path,
                    project_root=self.config.project_root,
                    verbose=self.config.eval_verbose,
                    repair_attempts=self.config.eval_repair_attempts,
                    max_message_chars=self.config.eval_max_message_chars,
                )
            )
        return self._eval_agent

    def build_simulation_runner(self, *, port: int) -> SimulationRunner:
        return SimulationRunner(
            config=SimulationRunnerConfig(
                max_turns=self.config.simulation_max_turns,
                early_task_end_policy=self.config.simulation_early_task_end_policy,
                validate_tool_calls=self.config.simulation_validate_tool_calls,
                assistant_state_key=self.config.simulation_assistant_state_key,
                assistant_verbose=self.config.simulation_assistant_verbose,
                assistant_enable_mcp_patch=self.config.simulation_assistant_enable_mcp_patch,
                assistant_enable_json_patch=self.config.simulation_assistant_enable_json_patch,
                runtime=MCPRuntimeConfig(
                    host=self.config.runtime_host,
                    port=port,
                    transport=self.config.runtime_transport,
                    server_name=self.config.runtime_server_name,
                    start_timeout_sec=self.config.runtime_start_timeout_sec,
                    poll_interval_sec=self.config.runtime_poll_interval_sec,
                ),
            ),
            user_agent_config=UserAgentConfig(
                prompt_path=self.config.user_prompt_path,
                model_temperature=self.config.user_model_temperature,
            ),
            tool_agent_config=ToolAgentConfig(
                prompt_path=self.config.tool_prompt_path,
                model_temperature=self.config.tool_model_temperature,
            ),
        )

    def decide_acceptance(self, *, evaluation: Any) -> bool:
        if self.config.min_eval_score is not None and evaluation.score < self.config.min_eval_score:
            return False
        if self.config.allowed_hallucination_risks is not None:
            if evaluation.hallucination_risk not in self.config.allowed_hallucination_risks:
                return False
        return True


class PlannerStageRunner:
    def __init__(self, *, store: SQLiteQueueStore, factory: QueueStageFactory):
        self.store = store
        self.factory = factory

    def run(self, job: JobRecord) -> Path:
        payload = job.payload
        skill_dir = Path(str(payload["skill_dir"])).resolve()
        persona_text = str(payload["persona_text"])
        blueprint_path = Path(str(payload["blueprint_path"])).resolve()
        artifact_root = Path(str(payload["artifact_root"])).resolve()

        bundle = self.factory.planner_agent().generate(
            skill_dir=skill_dir,
            persona_text=persona_text,
        )
        atomic_write_json(blueprint_path, bundle.blueprint)

        simulation_payload = {
            "sample_id": job.sample_id,
            "skill_dir": str(skill_dir),
            "tools_path": str((skill_dir / "tools.jsonl").resolve()),
            "blueprint_path": str(blueprint_path),
            "trajectory_path": str((artifact_root / "trajectory.json").resolve()),
            "artifact_root": str(artifact_root),
            "run_id": job.sample_id,
        }
        self.store.complete_planner_job(
            job_id=job.job_id,
            sample_id=job.sample_id,
            simulation_payload=simulation_payload,
        )
        logger.info("Planner stage finished for sample {}", job.sample_id)
        return blueprint_path


class SimulationStageRunner:
    def __init__(self, *, store: SQLiteQueueStore, factory: QueueStageFactory):
        self.store = store
        self.factory = factory

    def run(
        self,
        job: JobRecord,
        *,
        simulation_runner: SimulationRunner,
        runtime: Any | None = None,
    ) -> Path:
        payload = job.payload
        skill_dir = Path(str(payload["skill_dir"])).resolve()
        tools_path = Path(str(payload["tools_path"])).resolve()
        blueprint_path = Path(str(payload["blueprint_path"])).resolve()
        trajectory_path = Path(str(payload["trajectory_path"])).resolve()
        artifact_root = Path(str(payload["artifact_root"])).resolve()
        run_id = str(payload.get("run_id", job.sample_id))

        blueprint = load_json(blueprint_path)
        trajectory = simulation_runner.run(
            blueprint=blueprint,
            skill_dir=skill_dir,
            tools_path=tools_path,
            run_id=run_id,
            runtime=runtime,
        )
        atomic_write_json(trajectory_path, trajectory)

        eval_payload = {
            "sample_id": job.sample_id,
            "skill_dir": str(skill_dir),
            "blueprint_path": str(blueprint_path),
            "trajectory_path": str(trajectory_path),
            "evaluation_path": str((artifact_root / "evaluation.json").resolve()),
            "artifact_root": str(artifact_root),
        }
        self.store.complete_simulation_job(
            job_id=job.job_id,
            sample_id=job.sample_id,
            eval_payload=eval_payload,
        )
        logger.info("Simulation stage finished for sample {}", job.sample_id)
        return trajectory_path


class EvalStageRunner:
    def __init__(self, *, store: SQLiteQueueStore, factory: QueueStageFactory):
        self.store = store
        self.factory = factory

    def run(self, job: JobRecord) -> Path:
        payload = job.payload
        skill_dir = Path(str(payload["skill_dir"])).resolve()
        blueprint_path = Path(str(payload["blueprint_path"])).resolve()
        trajectory_path = Path(str(payload["trajectory_path"])).resolve()
        evaluation_path = Path(str(payload["evaluation_path"])).resolve()
        artifact_root = Path(str(payload["artifact_root"])).resolve()

        blueprint = load_json(blueprint_path)
        trajectory = load_json(trajectory_path)
        bundle = self.factory.eval_agent().evaluate(
            trajectory=trajectory,
            blueprint=blueprint,
            skill_dir=skill_dir,
        )
        atomic_write_json(evaluation_path, bundle.result)
        self._write_eval_sidecars(artifact_root=artifact_root, artifacts=bundle.artifacts)

        accepted = self.factory.decide_acceptance(evaluation=bundle.result)
        self.store.complete_eval_job(
            job_id=job.job_id,
            sample_id=job.sample_id,
            accepted=accepted,
        )
        logger.info("Eval stage finished for sample {}", job.sample_id)
        return evaluation_path

    def _write_eval_sidecars(
        self,
        *,
        artifact_root: Path,
        artifacts: dict[str, Any] | None,
    ) -> None:
        if not artifacts:
            return

        mapping = {
            "review": "eval_review.json",
            "repair_report": "repair_report.json",
            "training_export": "repair_training_export.json",
        }
        for key, filename in mapping.items():
            payload = artifacts.get(key)
            if payload is not None:
                atomic_write_json((artifact_root / filename).resolve(), payload)

        repair_markdown = artifacts.get("repair_markdown")
        if isinstance(repair_markdown, str) and repair_markdown.strip():
            atomic_write_text((artifact_root / "repair_plan.md").resolve(), repair_markdown)
