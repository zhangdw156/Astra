from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from ..utils import logger
from .types import JobRecord, SampleArtifacts, SampleRecord, StageName


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_text() -> str:
    return utc_now().isoformat()


def utc_after_text(*, seconds: int) -> str:
    return (utc_now() + timedelta(seconds=seconds)).isoformat()


class SQLiteQueueStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path.resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connections: dict[int, sqlite3.Connection] = {}
        self._connections_lock = threading.Lock()

    def _get_conn(self) -> sqlite3.Connection:
        thread_id = threading.get_ident()
        with self._connections_lock:
            existing = self._connections.get(thread_id)
            if existing is not None:
                return existing

            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30,
                isolation_level=None,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._connections[thread_id] = conn
            return conn

    def close(self) -> None:
        with self._connections_lock:
            for conn in self._connections.values():
                conn.close()
            self._connections.clear()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Cursor]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def initialize(self) -> None:
        with self._transaction() as cur:
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS samples (
                    sample_id TEXT PRIMARY KEY,
                    skill_key TEXT NOT NULL,
                    skill_dir TEXT NOT NULL,
                    persona_text TEXT NOT NULL,
                    artifact_root TEXT NOT NULL,
                    planner_state TEXT NOT NULL,
                    simulation_state TEXT NOT NULL,
                    eval_state TEXT NOT NULL,
                    final_state TEXT NOT NULL,
                    accepted INTEGER DEFAULT NULL,
                    last_error TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    sample_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    skill_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 0,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 2,
                    leased_by TEXT DEFAULT NULL,
                    lease_expires_at TEXT DEFAULT NULL,
                    last_error TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(sample_id) REFERENCES samples(sample_id)
                );

                CREATE TABLE IF NOT EXISTS simulation_skill_leases (
                    skill_key TEXT PRIMARY KEY,
                    owner_worker_id TEXT NOT NULL,
                    lease_expires_at TEXT NOT NULL,
                    current_port INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS resource_lanes (
                    lane_name TEXT PRIMARY KEY,
                    owner_id TEXT DEFAULT NULL,
                    lease_expires_at TEXT DEFAULT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_stage_status_created
                ON jobs(stage, status, priority DESC, created_at);

                CREATE INDEX IF NOT EXISTS idx_jobs_skill_stage_status
                ON jobs(skill_key, stage, status, created_at);

                CREATE INDEX IF NOT EXISTS idx_jobs_lease_expiry
                ON jobs(status, lease_expires_at);
                """
            )

            now = utc_now_text()
            cur.execute(
                """
                INSERT OR IGNORE INTO resource_lanes (
                    lane_name, owner_id, lease_expires_at, updated_at
                )
                VALUES (?, NULL, NULL, ?)
                """,
                ("opencode", now),
            )

    def ensure_lane(self, lane_name: str) -> None:
        with self._transaction() as cur:
            cur.execute(
                """
                INSERT OR IGNORE INTO resource_lanes (
                    lane_name, owner_id, lease_expires_at, updated_at
                )
                VALUES (?, NULL, NULL, ?)
                """,
                (lane_name, utc_now_text()),
            )

    def submit_sample(
        self,
        *,
        sample_id: str,
        skill_dir: Path,
        persona_text: str,
        artifact_root: Path,
        planner_priority: int = 0,
        max_retries: int = 2,
    ) -> SampleArtifacts:
        resolved_skill_dir = skill_dir.resolve()
        artifacts = SampleArtifacts.from_root(artifact_root)
        created_at = utc_now_text()
        payload = {
            "sample_id": sample_id,
            "skill_dir": str(resolved_skill_dir),
            "persona_text": persona_text,
            "artifact_root": str(artifacts.root),
            "blueprint_path": str(artifacts.blueprint_path),
        }

        with self._transaction() as cur:
            existing = cur.execute(
                "SELECT 1 FROM samples WHERE sample_id = ?",
                (sample_id,),
            ).fetchone()
            if existing is not None:
                raise ValueError(f"sample_id 已存在: {sample_id}")

            cur.execute(
                """
                INSERT INTO samples (
                    sample_id,
                    skill_key,
                    skill_dir,
                    persona_text,
                    artifact_root,
                    planner_state,
                    simulation_state,
                    eval_state,
                    final_state,
                    accepted,
                    last_error,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, '', ?, ?)
                """,
                (
                    sample_id,
                    str(resolved_skill_dir),
                    str(resolved_skill_dir),
                    persona_text,
                    str(artifacts.root),
                    "pending",
                    "blocked",
                    "blocked",
                    "new",
                    created_at,
                    created_at,
                ),
            )
            self._insert_job(
                cur,
                sample_id=sample_id,
                stage="planner",
                skill_key=str(resolved_skill_dir),
                payload=payload,
                priority=planner_priority,
                max_retries=max_retries,
            )

        return artifacts

    def get_sample(self, sample_id: str) -> SampleRecord | None:
        row = self._get_conn().execute(
            "SELECT * FROM samples WHERE sample_id = ?",
            (sample_id,),
        ).fetchone()
        if row is None:
            return None
        return SampleRecord.from_row(row)

    def summarize_samples(self) -> dict[str, int]:
        row = self._get_conn().execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN final_state = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN final_state = 'failed' THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) AS accepted,
                SUM(CASE WHEN final_state = 'completed' AND accepted = 0 THEN 1 ELSE 0 END) AS rejected,
                SUM(CASE WHEN final_state IN ('new', 'in_progress') THEN 1 ELSE 0 END) AS outstanding
            FROM samples
            """
        ).fetchone()
        if row is None:
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "accepted": 0,
                "rejected": 0,
                "outstanding": 0,
            }
        return {
            "total": int(row["total"] or 0),
            "completed": int(row["completed"] or 0),
            "failed": int(row["failed"] or 0),
            "accepted": int(row["accepted"] or 0),
            "rejected": int(row["rejected"] or 0),
            "outstanding": int(row["outstanding"] or 0),
        }

    def count_open_jobs(self) -> int:
        row = self._get_conn().execute(
            """
            SELECT COUNT(*) AS cnt
            FROM jobs
            WHERE status IN ('pending', 'leased')
            """
        ).fetchone()
        return int(row["cnt"]) if row is not None else 0

    def recover_active_leases(self) -> None:
        now = utc_now_text()
        with self._transaction() as cur:
            cur.execute(
                """
                UPDATE jobs
                SET status = 'pending',
                    leased_by = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE status = 'leased'
                """,
                (now,),
            )
            cur.execute(
                """
                UPDATE resource_lanes
                SET owner_id = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE owner_id IS NOT NULL
                """,
                (now,),
            )
            cur.execute(
                """
                DELETE FROM simulation_skill_leases
                """
            )

    def claim_lane(self, *, lane_name: str, owner_id: str, ttl_sec: int) -> bool:
        now = utc_now_text()
        expires_at = utc_after_text(seconds=ttl_sec)
        with self._transaction() as cur:
            row = cur.execute(
                "SELECT * FROM resource_lanes WHERE lane_name = ?",
                (lane_name,),
            ).fetchone()
            if row is None:
                cur.execute(
                    """
                    INSERT INTO resource_lanes (
                        lane_name, owner_id, lease_expires_at, updated_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (lane_name, owner_id, expires_at, now),
                )
                return True

            current_owner = row["owner_id"]
            lease_expires_at = row["lease_expires_at"]
            if (
                current_owner in {None, owner_id}
                or (isinstance(lease_expires_at, str) and lease_expires_at <= now)
            ):
                cur.execute(
                    """
                    UPDATE resource_lanes
                    SET owner_id = ?, lease_expires_at = ?, updated_at = ?
                    WHERE lane_name = ?
                    """,
                    (owner_id, expires_at, now, lane_name),
                )
                return True
        return False

    def release_lane(self, *, lane_name: str, owner_id: str) -> None:
        with self._transaction() as cur:
            cur.execute(
                """
                UPDATE resource_lanes
                SET owner_id = NULL, lease_expires_at = NULL, updated_at = ?
                WHERE lane_name = ? AND owner_id = ?
                """,
                (utc_now_text(), lane_name, owner_id),
            )

    def claim_skill_lease(
        self,
        *,
        skill_key: str,
        owner_worker_id: str,
        port: int,
        ttl_sec: int,
    ) -> bool:
        now = utc_now_text()
        expires_at = utc_after_text(seconds=ttl_sec)
        with self._transaction() as cur:
            row = cur.execute(
                """
                SELECT *
                FROM simulation_skill_leases
                WHERE skill_key = ?
                """,
                (skill_key,),
            ).fetchone()
            if row is None:
                cur.execute(
                    """
                    INSERT INTO simulation_skill_leases (
                        skill_key, owner_worker_id, lease_expires_at, current_port, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (skill_key, owner_worker_id, expires_at, port, now),
                )
                return True

            current_owner = row["owner_worker_id"]
            lease_expires_at = row["lease_expires_at"]
            if (
                current_owner == owner_worker_id
                or (isinstance(lease_expires_at, str) and lease_expires_at <= now)
            ):
                cur.execute(
                    """
                    UPDATE simulation_skill_leases
                    SET owner_worker_id = ?, lease_expires_at = ?, current_port = ?, updated_at = ?
                    WHERE skill_key = ?
                    """,
                    (owner_worker_id, expires_at, port, now, skill_key),
                )
                return True
        return False

    def release_skill_lease(self, *, skill_key: str, owner_worker_id: str) -> None:
        with self._transaction() as cur:
            cur.execute(
                """
                DELETE FROM simulation_skill_leases
                WHERE skill_key = ? AND owner_worker_id = ?
                """,
                (skill_key, owner_worker_id),
            )

    def list_candidate_simulation_skills(self, *, limit: int = 32) -> list[str]:
        now = utc_now_text()
        rows = self._get_conn().execute(
            """
            SELECT skill_key, MIN(created_at) AS first_created
            FROM jobs
            WHERE stage = 'simulation'
              AND (
                status = 'pending'
                OR (status = 'leased' AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?)
              )
            GROUP BY skill_key
            ORDER BY first_created ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        return [str(row["skill_key"]) for row in rows]

    def count_available_jobs(self, *, stage: StageName) -> int:
        now = utc_now_text()
        row = self._get_conn().execute(
            """
            SELECT COUNT(*) AS cnt
            FROM jobs
            WHERE stage = ?
              AND (
                status = 'pending'
                OR (status = 'leased' AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?)
              )
            """,
            (stage, now),
        ).fetchone()
        return int(row["cnt"]) if row is not None else 0

    def claim_next_job(
        self,
        *,
        stage: StageName,
        worker_id: str,
        lease_ttl_sec: int,
        preferred_skill_key: str | None = None,
    ) -> JobRecord | None:
        now = utc_now_text()
        expires_at = utc_after_text(seconds=lease_ttl_sec)
        stage_column = self._sample_stage_column(stage)

        query = """
            SELECT *
            FROM jobs
            WHERE stage = ?
              AND (
                status = 'pending'
                OR (status = 'leased' AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?)
              )
        """
        params: list[Any] = [stage, now]
        if preferred_skill_key is not None:
            query += " AND skill_key = ?"
            params.append(preferred_skill_key)
        query += " ORDER BY priority DESC, created_at ASC LIMIT 1"

        with self._transaction() as cur:
            row = cur.execute(query, params).fetchone()
            if row is None:
                return None

            cur.execute(
                """
                UPDATE jobs
                SET status = 'leased',
                    leased_by = ?,
                    lease_expires_at = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (worker_id, expires_at, now, row["job_id"]),
            )
            cur.execute(
                f"""
                UPDATE samples
                SET {stage_column} = 'running',
                    final_state = CASE
                        WHEN final_state = 'new' THEN 'in_progress'
                        ELSE final_state
                    END,
                    last_error = '',
                    updated_at = ?
                WHERE sample_id = ?
                """,
                (now, row["sample_id"]),
            )

            updated_row = cur.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (row["job_id"],),
            ).fetchone()
            if updated_row is None:
                return None
            return JobRecord.from_row(updated_row)

    def complete_planner_job(
        self,
        *,
        job_id: str,
        sample_id: str,
        simulation_payload: dict[str, Any],
        priority: int = 0,
        max_retries: int = 2,
    ) -> None:
        now = utc_now_text()
        sample = self.get_sample(sample_id)
        if sample is None:
            raise ValueError(f"sample 不存在: {sample_id}")

        with self._transaction() as cur:
            cur.execute(
                """
                UPDATE jobs
                SET status = 'done',
                    leased_by = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (now, job_id),
            )
            cur.execute(
                """
                UPDATE samples
                SET planner_state = 'succeeded',
                    simulation_state = 'pending',
                    final_state = 'in_progress',
                    last_error = '',
                    updated_at = ?
                WHERE sample_id = ?
                """,
                (now, sample_id),
            )
            self._insert_job(
                cur,
                sample_id=sample_id,
                stage="simulation",
                skill_key=sample.skill_key,
                payload=simulation_payload,
                priority=priority,
                max_retries=max_retries,
            )

    def complete_simulation_job(
        self,
        *,
        job_id: str,
        sample_id: str,
        eval_payload: dict[str, Any],
        priority: int = 0,
        max_retries: int = 2,
    ) -> None:
        now = utc_now_text()
        sample = self.get_sample(sample_id)
        if sample is None:
            raise ValueError(f"sample 不存在: {sample_id}")

        with self._transaction() as cur:
            cur.execute(
                """
                UPDATE jobs
                SET status = 'done',
                    leased_by = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (now, job_id),
            )
            cur.execute(
                """
                UPDATE samples
                SET simulation_state = 'succeeded',
                    eval_state = 'pending',
                    final_state = 'in_progress',
                    last_error = '',
                    updated_at = ?
                WHERE sample_id = ?
                """,
                (now, sample_id),
            )
            self._insert_job(
                cur,
                sample_id=sample_id,
                stage="eval",
                skill_key=sample.skill_key,
                payload=eval_payload,
                priority=priority,
                max_retries=max_retries,
            )

    def complete_eval_job(
        self,
        *,
        job_id: str,
        sample_id: str,
        accepted: bool,
    ) -> None:
        now = utc_now_text()
        with self._transaction() as cur:
            cur.execute(
                """
                UPDATE jobs
                SET status = 'done',
                    leased_by = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (now, job_id),
            )
            cur.execute(
                """
                UPDATE samples
                SET eval_state = 'succeeded',
                    final_state = 'completed',
                    accepted = ?,
                    last_error = '',
                    updated_at = ?
                WHERE sample_id = ?
                """,
                (1 if accepted else 0, now, sample_id),
            )

    def fail_job(self, *, job: JobRecord, error: str) -> None:
        now = utc_now_text()
        stage_column = self._sample_stage_column(job.stage)
        next_retry_count = job.retry_count + 1
        should_retry = next_retry_count <= job.max_retries

        with self._transaction() as cur:
            if should_retry:
                logger.warning(
                    "Retrying {} job {} for sample {} ({}/{})",
                    job.stage,
                    job.job_id,
                    job.sample_id,
                    next_retry_count,
                    job.max_retries,
                )
                cur.execute(
                    """
                    UPDATE jobs
                    SET status = 'pending',
                        retry_count = ?,
                        leased_by = NULL,
                        lease_expires_at = NULL,
                        last_error = ?,
                        updated_at = ?
                    WHERE job_id = ?
                    """,
                    (next_retry_count, error, now, job.job_id),
                )
                cur.execute(
                    f"""
                    UPDATE samples
                    SET {stage_column} = 'pending',
                        final_state = 'in_progress',
                        last_error = ?,
                        updated_at = ?
                    WHERE sample_id = ?
                    """,
                    (error, now, job.sample_id),
                )
                return

            cur.execute(
                """
                UPDATE jobs
                SET status = 'failed',
                    retry_count = ?,
                    leased_by = NULL,
                    lease_expires_at = NULL,
                    last_error = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (next_retry_count, error, now, job.job_id),
            )
            cur.execute(
                f"""
                UPDATE samples
                SET {stage_column} = 'failed',
                    final_state = 'failed',
                    accepted = 0,
                    last_error = ?,
                    updated_at = ?
                WHERE sample_id = ?
                """,
                (error, now, job.sample_id),
            )

    def _insert_job(
        self,
        cur: sqlite3.Cursor,
        *,
        sample_id: str,
        stage: StageName,
        skill_key: str,
        payload: dict[str, Any],
        priority: int,
        max_retries: int,
    ) -> str:
        job_id = f"job_{stage}_{uuid.uuid4().hex}"
        now = utc_now_text()
        cur.execute(
            """
            INSERT INTO jobs (
                job_id,
                sample_id,
                stage,
                skill_key,
                payload_json,
                status,
                priority,
                retry_count,
                max_retries,
                leased_by,
                lease_expires_at,
                last_error,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, 'pending', ?, 0, ?, NULL, NULL, '', ?, ?)
            """,
            (
                job_id,
                sample_id,
                stage,
                skill_key,
                json.dumps(payload, ensure_ascii=False),
                priority,
                max_retries,
                now,
                now,
            ),
        )
        return job_id

    def _sample_stage_column(self, stage: StageName) -> str:
        if stage == "planner":
            return "planner_state"
        if stage == "simulation":
            return "simulation_state"
        return "eval_state"
