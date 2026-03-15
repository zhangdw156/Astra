#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Snapshot:
    total: int
    completed: int
    failed: int
    accepted: int
    rejected: int
    outstanding: int
    open_jobs: int
    leased_jobs: int
    max_sample_updated_at: str | None
    max_job_updated_at: str | None

    @property
    def progress_marker(self) -> tuple[int, int, int, int]:
        return (self.completed, self.accepted, self.failed, self.rejected)


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def append_log(log_path: Path, message: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{now_text()}] {message}\n")


def list_matching_processes(pattern: str) -> list[tuple[int, str]]:
    proc = subprocess.run(
        ["pgrep", "-af", pattern],
        capture_output=True,
        text=True,
        check=False,
    )
    matches: list[tuple[int, str]] = []
    for raw_line in proc.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if not parts:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmd = parts[1] if len(parts) > 1 else ""
        if "watch_pipeline5_run.py" in cmd:
            continue
        if "monitor.log" in cmd:
            continue
        if "pgrep -af" in cmd:
            continue
        matches.append((pid, cmd))
    return matches


def load_snapshot(db_path: Path) -> Snapshot:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        summary = cur.execute(
            """
            SELECT
                COUNT(*),
                SUM(CASE WHEN final_state = 'completed' THEN 1 ELSE 0 END),
                SUM(CASE WHEN final_state = 'failed' THEN 1 ELSE 0 END),
                SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN final_state = 'completed' AND accepted = 0 THEN 1 ELSE 0 END),
                SUM(CASE WHEN final_state IN ('new', 'in_progress') THEN 1 ELSE 0 END),
                MAX(updated_at)
            FROM samples
            """
        ).fetchone()
        jobs = cur.execute(
            """
            SELECT
                SUM(CASE WHEN status IN ('pending', 'leased') THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'leased' THEN 1 ELSE 0 END),
                MAX(updated_at)
            FROM jobs
            """
        ).fetchone()
    finally:
        conn.close()

    return Snapshot(
        total=int(summary[0] or 0),
        completed=int(summary[1] or 0),
        failed=int(summary[2] or 0),
        accepted=int(summary[3] or 0),
        rejected=int(summary[4] or 0),
        outstanding=int(summary[5] or 0),
        open_jobs=int(jobs[0] or 0),
        leased_jobs=int(jobs[1] or 0),
        max_sample_updated_at=str(summary[6]) if summary[6] is not None else None,
        max_job_updated_at=str(jobs[2]) if jobs[2] is not None else None,
    )


def terminate_processes(
    *,
    processes: list[tuple[int, str]],
    grace_sec: int,
    log_path: Path,
) -> None:
    if not processes:
        return

    append_log(log_path, f"Sending SIGTERM to pipeline processes: {[pid for pid, _ in processes]}")
    for pid, _cmd in processes:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue

    deadline = time.time() + grace_sec
    remaining = {pid for pid, _ in processes}
    while time.time() < deadline and remaining:
        time.sleep(1.0)
        for pid in tuple(remaining):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                remaining.discard(pid)

    if not remaining:
        append_log(log_path, "Pipeline processes exited after SIGTERM")
        return

    append_log(log_path, f"Escalating to SIGKILL for processes: {sorted(remaining)}")
    for pid in sorted(remaining):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            continue


def main() -> int:
    parser = argparse.ArgumentParser(description="Watchdog for pipeline5 formal runs")
    parser.add_argument("--queue-db", type=Path, required=True)
    parser.add_argument("--process-pattern", type=str, required=True)
    parser.add_argument("--log-path", type=Path, required=True)
    parser.add_argument("--poll-sec", type=int, default=600)
    parser.add_argument("--stall-threshold-sec", type=int, default=3600)
    parser.add_argument("--kill-grace-sec", type=int, default=30)
    args = parser.parse_args()

    if args.poll_sec <= 0:
        raise ValueError("--poll-sec must be positive")
    if args.stall_threshold_sec <= 0:
        raise ValueError("--stall-threshold-sec must be positive")
    if args.kill_grace_sec <= 0:
        raise ValueError("--kill-grace-sec must be positive")

    queue_db = args.queue_db.resolve()
    log_path = args.log_path.resolve()

    last_progress: tuple[int, int, int, int] | None = None
    last_progress_time = time.time()

    append_log(log_path, f"Watchdog started for queue DB: {queue_db}")
    append_log(log_path, f"Process pattern: {args.process_pattern}")

    while True:
        processes = list_matching_processes(args.process_pattern)
        snapshot = load_snapshot(queue_db)
        progress = snapshot.progress_marker
        if progress != last_progress:
            last_progress = progress
            last_progress_time = time.time()

        stalled_for = int(time.time() - last_progress_time)
        append_log(
            log_path,
            "status total={total} completed={completed} failed={failed} "
            "accepted={accepted} rejected={rejected} outstanding={outstanding} "
            "open_jobs={open_jobs} leased_jobs={leased_jobs} stalled_for={stalled_for}s "
            "processes={pids}".format(
                total=snapshot.total,
                completed=snapshot.completed,
                failed=snapshot.failed,
                accepted=snapshot.accepted,
                rejected=snapshot.rejected,
                outstanding=snapshot.outstanding,
                open_jobs=snapshot.open_jobs,
                leased_jobs=snapshot.leased_jobs,
                stalled_for=stalled_for,
                pids=[pid for pid, _ in processes],
            ),
        )

        if not processes and snapshot.open_jobs > 0:
            append_log(log_path, "Anomaly detected: pipeline process missing while open jobs remain")
            return 1

        should_stop = (
            bool(processes)
            and snapshot.open_jobs > 0
            and stalled_for >= args.stall_threshold_sec
        )
        if should_stop:
            append_log(
                log_path,
                "Anomaly detected: no progress for too long while jobs remain; stopping pipeline",
            )
            terminate_processes(
                processes=processes,
                grace_sec=args.kill_grace_sec,
                log_path=log_path,
            )
            return 2

        time.sleep(args.poll_sec)


if __name__ == "__main__":
    raise SystemExit(main())
