from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


StageName = Literal["planner", "simulation", "eval"]
JobStatus = Literal["pending", "leased", "done", "failed"]
PlannerState = Literal["pending", "running", "succeeded", "failed"]
SimulationState = Literal["blocked", "pending", "running", "succeeded", "failed"]
EvalState = Literal["blocked", "pending", "running", "succeeded", "failed"]
FinalState = Literal["new", "in_progress", "completed", "failed"]


@dataclass(frozen=True, slots=True)
class SampleArtifacts:
    root: Path
    blueprint_path: Path
    trajectory_path: Path
    evaluation_path: Path

    @classmethod
    def from_root(cls, root: Path) -> "SampleArtifacts":
        resolved = root.resolve()
        return cls(
            root=resolved,
            blueprint_path=resolved / "blueprint.json",
            trajectory_path=resolved / "trajectory.json",
            evaluation_path=resolved / "evaluation.json",
        )


@dataclass(slots=True)
class JobRecord:
    job_id: str
    sample_id: str
    stage: StageName
    skill_key: str
    payload: dict[str, Any]
    status: JobStatus
    priority: int
    retry_count: int
    max_retries: int
    leased_by: str | None
    lease_expires_at: str | None
    last_error: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: Any) -> "JobRecord":
        payload = row["payload_json"]
        parsed_payload = json.loads(payload) if isinstance(payload, str) and payload else {}
        return cls(
            job_id=str(row["job_id"]),
            sample_id=str(row["sample_id"]),
            stage=str(row["stage"]),
            skill_key=str(row["skill_key"]),
            payload=parsed_payload if isinstance(parsed_payload, dict) else {},
            status=str(row["status"]),
            priority=int(row["priority"]),
            retry_count=int(row["retry_count"]),
            max_retries=int(row["max_retries"]),
            leased_by=row["leased_by"],
            lease_expires_at=row["lease_expires_at"],
            last_error=str(row["last_error"] or ""),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )


@dataclass(slots=True)
class SampleRecord:
    sample_id: str
    skill_key: str
    skill_dir: str
    persona_text: str
    artifact_root: str
    planner_state: PlannerState
    simulation_state: SimulationState
    eval_state: EvalState
    final_state: FinalState
    accepted: bool | None
    last_error: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: Any) -> "SampleRecord":
        accepted_raw = row["accepted"]
        accepted = None if accepted_raw is None else bool(int(accepted_raw))
        return cls(
            sample_id=str(row["sample_id"]),
            skill_key=str(row["skill_key"]),
            skill_dir=str(row["skill_dir"]),
            persona_text=str(row["persona_text"]),
            artifact_root=str(row["artifact_root"]),
            planner_state=str(row["planner_state"]),
            simulation_state=str(row["simulation_state"]),
            eval_state=str(row["eval_state"]),
            final_state=str(row["final_state"]),
            accepted=accepted,
            last_error=str(row["last_error"] or ""),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
