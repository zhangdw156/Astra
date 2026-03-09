"""
Collect Memory Stats Tool - 收集内存系统统计信息

从内存数据库收集匿名化的统计信息，包括检索性能、token使用量、consolidation指标等。
"""

import json
import os
import sqlite3
import platform
from pathlib import Path
from datetime import datetime, timedelta, timezone

TOOL_SCHEMA = {
    "name": "collect_memory_stats",
    "description": "Collect anonymized memory system statistics from the database. "
    "Retrieves memory counts, type distribution, age distribution, retrieval performance metrics, "
    "and consolidation history. Use this to get a comprehensive overview of the memory system state.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "db_path": {
                "type": "string",
                "description": "Path to the memory database file. If not provided, searches default locations.",
            },
            "days": {
                "type": "integer",
                "default": 14,
                "description": "Number of days of history to include (default: 14)",
            },
        },
    },
}

DEFAULT_DB_PATHS = [
    Path.home() / ".openclaw" / "workspace" / "db" / "memory.db",
    Path.home() / ".openclaw" / "workspace" / "db" / "cognitive_memory.db",
    Path.home() / ".openclaw" / "workspace" / "db" / "jarvis.db",
]


def find_db(db_path: str = None) -> Path:
    """Locate the cognitive memory database."""
    if db_path:
        p = Path(db_path)
        if p.exists():
            return p

    for c in DEFAULT_DB_PATHS:
        if c.exists():
            return c
    return None


def get_system_info():
    """Non-identifying system metadata."""
    import os as os_module

    return {
        "os": platform.system(),
        "arch": platform.machine(),
        "python": platform.python_version(),
    }


def collect_memory_stats(conn: sqlite3.Connection, days: int):
    """Collect aggregate memory statistics."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    total = conn.execute("SELECT COUNT(*) FROM memories WHERE is_deleted = 0").fetchone()[0]
    deleted = conn.execute("SELECT COUNT(*) FROM memories WHERE is_deleted = 1").fetchone()[0]

    type_dist = dict(
        conn.execute(
            "SELECT memory_type, COUNT(*) FROM memories WHERE is_deleted = 0 GROUP BY memory_type"
        ).fetchall()
    )

    age_buckets = {"<1d": 0, "1-7d": 0, "7-30d": 0, "30-90d": 0, ">90d": 0}
    try:
        rows = conn.execute(
            "SELECT julianday('now') - julianday(created_at) as age_days FROM memories WHERE is_deleted = 0"
        ).fetchall()
        for (age,) in rows:
            if age < 1:
                age_buckets["<1d"] += 1
            elif age < 7:
                age_buckets["1-7d"] += 1
            elif age < 30:
                age_buckets["7-30d"] += 1
            elif age < 90:
                age_buckets["30-90d"] += 1
            else:
                age_buckets[">90d"] += 1
    except sqlite3.OperationalError:
        pass

    return {
        "total_active": total,
        "total_deleted": deleted,
        "type_distribution": type_dist,
        "age_distribution": age_buckets,
    }


def collect_retrieval_stats(conn: sqlite3.Connection, days: int):
    """Collect retrieval performance metrics if available."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    stats = {"available": False}

    try:
        rows = conn.execute(
            "SELECT strategy, avg_score, result_count, latency_ms, timestamp "
            "FROM retrieval_log WHERE timestamp > ? ORDER BY timestamp DESC LIMIT 500",
            (cutoff,),
        ).fetchall()

        if not rows:
            return stats

        stats["available"] = True
        stats["total_queries"] = len(rows)

        scores = [r[1] for r in rows if r[1] is not None]
        latencies = [r[3] for r in rows if r[3] is not None]

        if scores:
            stats["avg_score"] = {
                "mean": round(sum(scores) / len(scores), 4),
                "min": round(min(scores), 4),
                "max": round(max(scores), 4),
                "n": len(scores),
            }

        if latencies:
            sorted_lat = sorted(latencies)
            stats["latency_ms"] = {
                "mean": round(sum(latencies) / len(latencies), 1),
                "p50": round(sorted_lat[len(sorted_lat) // 2], 1),
                "p95": round(sorted_lat[int(len(sorted_lat) * 0.95)], 1),
            }

    except sqlite3.OperationalError:
        pass

    return stats


def execute(db_path: str = None, days: int = 14) -> str:
    """
    收集内存系统统计信息

    Args:
        db_path: 数据库路径（可选）
        days: 收集的历史天数（默认14天）

    Returns:
        格式化的统计报告
    """
    db = find_db(db_path)

    if not db:
        output = "## Memory Stats Collection Failed\n\n"
        output += "Memory database not found. Searched locations:\n"
        for p in DEFAULT_DB_PATHS:
            output += f"- {p}\n"
        output += "\nUse `--db PATH` to specify manually."
        return output

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row

    output = f"## Memory System Statistics\n\n"
    output += f"**Database**: {db}\n"
    output += f"**Period**: Last {days} days\n"
    output += f"**Collected at**: {datetime.now(timezone.utc).isoformat()}\n\n"

    mem_stats = collect_memory_stats(conn, days)
    output += "### Memory Overview\n\n"
    output += f"- **Active memories**: {mem_stats['total_active']}\n"
    output += f"- **Deleted memories**: {mem_stats['total_deleted']}\n\n"

    if mem_stats["type_distribution"]:
        output += "#### Type Distribution\n\n"
        for mem_type, count in mem_stats["type_distribution"].items():
            output += f"- {mem_type}: {count}\n"
        output += "\n"

    if mem_stats["age_distribution"]:
        output += "#### Age Distribution\n\n"
        for bucket, count in mem_stats["age_distribution"].items():
            output += f"- {bucket}: {count}\n"
        output += "\n"

    retr_stats = collect_retrieval_stats(conn, days)
    output += "### Retrieval Performance\n\n"

    if retr_stats.get("available"):
        output += f"**Total queries logged**: {retr_stats['total_queries']}\n\n"

        if "avg_score" in retr_stats:
            s = retr_stats["avg_score"]
            output += "**Average Score**:\n"
            output += f"- Mean: {s['mean']}\n"
            output += f"- Range: [{s['min']}, {s['max']}]\n"
            output += f"- N: {s['n']}\n\n"

        if "latency_ms" in retr_stats:
            l = retr_stats["latency_ms"]
            output += "**Latency**:\n"
            output += f"- Mean: {l['mean']}ms\n"
            output += f"- P50: {l['p50']}ms\n"
            output += f"- P95: {l['p95']}ms\n\n"
    else:
        output += "No retrieval performance data available.\n"
        output += "Run `run_memory_assessment` tool to measure retrieval quality.\n\n"

    conn.close()

    output += "---\n"
    output += "*Use `run_metric_tests` to verify IR metric calculations.*"

    return output


if __name__ == "__main__":
    print(execute())
