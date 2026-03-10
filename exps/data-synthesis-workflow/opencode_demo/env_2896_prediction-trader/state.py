"""
状态访问层（State Access Layer）

依据 DATA_SYNTHESIS_TECH_ROUTE：工具通过本层操作 SQLite，状态可追踪、可回滚、可验证。
封装 read / write / delete / transaction，Mock 与 tools 统一从同一数据库读取。
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any, Dict, List, Optional


_CURRENT_RUN_ID: ContextVar[Optional[str]] = ContextVar("current_run_id", default=None)

# 默认数据库路径：项目根下 data/state.db，可由 STATE_DB_PATH 覆盖
def _db_path() -> Path:
    path = os.environ.get("STATE_DB_PATH")
    if path:
        return Path(path)
    base = Path(__file__).parent
    return base / "data" / "state.db"


def get_connection(read_only: bool = False) -> sqlite3.Connection:
    """获取数据库连接。调用方负责关闭，或使用 transaction() / connection() 上下文。"""
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection():
    """获取连接并在退出时关闭。"""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction():
    """事务上下文：提交或回滚。"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def set_run_id(run_id: Optional[str]) -> Token:
    """设置当前运行上下文中的 run_id，供运行态接口自动隔离使用。"""
    return _CURRENT_RUN_ID.set(run_id)


def reset_run_id(token: Token) -> None:
    """恢复上一个运行上下文。"""
    _CURRENT_RUN_ID.reset(token)


@contextmanager
def run_context(run_id: str):
    """在 with 作用域内绑定当前 run_id。"""
    token = set_run_id(run_id)
    try:
        yield run_id
    finally:
        reset_run_id(token)


def current_run_id() -> Optional[str]:
    """返回当前上下文中的 run_id；若未绑定则返回 None。"""
    return _CURRENT_RUN_ID.get()


def require_run_id(run_id: Optional[str] = None) -> str:
    """获取有效 run_id；若未提供且上下文中也没有，则抛错。"""
    resolved = run_id or current_run_id()
    if not resolved:
        raise RuntimeError("运行态读写必须绑定 run_id，请先设置 run_context()。")
    return resolved


def read(
    table: str,
    *,
    columns: Optional[List[str]] = None,
    where: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    通用读：按条件查询表，返回字典列表。

    Args:
        table: 表名（kalshi_markets / polymarket_events）
        columns: 要返回的列，None 表示 *
        where: 条件键值对（AND 组合）
        order_by: 例如 "volume DESC"
        limit: 最大行数
    """
    cols = ", ".join(columns) if columns else "*"
    sql = f"SELECT {cols} FROM {table}"
    params: List[Any] = []
    if where:
        parts = [f"{k} = ?" for k in where]
        sql += " WHERE " + " AND ".join(parts)
        params.extend(where.values())
    if order_by:
        sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += f" LIMIT {limit}"

    with connection() as conn:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def write(table: str, row: Dict[str, Any], *, pk: str = "id") -> None:
    """
    写入一行：若主键存在则 UPDATE，否则 INSERT。
    本环境以只读查询为主，写接口保留供扩展或验证脚本使用。
    """
    with transaction() as conn:
        cur = conn.execute(f"SELECT 1 FROM {table} WHERE {pk} = ?", (row.get(pk),))
        if cur.fetchone():
            set_parts = ", ".join(f"{k} = ?" for k in row if k != pk)
            set_params = [v for k, v in row.items() if k != pk]
            set_params.append(row[pk])
            conn.execute(f"UPDATE {table} SET {set_parts} WHERE {pk} = ?", set_params)
        else:
            cols = ", ".join(row.keys())
            placeholders = ", ".join("?" for _ in row)
            conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", list(row.values()))


def delete(table: str, where: Dict[str, Any]) -> None:
    """按条件删除。"""
    sql = f"DELETE FROM {table} WHERE " + " AND ".join(f"{k} = ?" for k in where)
    with transaction() as conn:
        conn.execute(sql, list(where.values()))


def create_run(
    run_id: str,
    *,
    blueprint_id: str = "",
    skill_name: str = "",
    persona_id: str = "",
    status: str = "created",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """创建或覆盖一条运行记录。"""
    row = {
        "run_id": run_id,
        "blueprint_id": blueprint_id,
        "skill_name": skill_name,
        "persona_id": persona_id,
        "status": status,
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
    }
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO trajectory_runs (run_id, blueprint_id, skill_name, persona_id, status, metadata_json)
            VALUES (:run_id, :blueprint_id, :skill_name, :persona_id, :status, :metadata_json)
            ON CONFLICT(run_id) DO UPDATE SET
                blueprint_id = excluded.blueprint_id,
                skill_name = excluded.skill_name,
                persona_id = excluded.persona_id,
                status = excluded.status,
                metadata_json = excluded.metadata_json,
                updated_at = datetime('now')
            """,
            row,
        )


def update_run_status(run_id: Optional[str] = None, *, status: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """更新运行状态，可选合并 metadata。"""
    resolved_run_id = require_run_id(run_id)
    existing = read_run(resolved_run_id) or {}
    merged_metadata = existing.get("metadata", {})
    if metadata:
        merged_metadata = {**merged_metadata, **metadata}

    with transaction() as conn:
        conn.execute(
            """
            UPDATE trajectory_runs
               SET status = ?,
                   metadata_json = ?,
                   updated_at = datetime('now')
             WHERE run_id = ?
            """,
            (status, json.dumps(merged_metadata, ensure_ascii=False), resolved_run_id),
        )


def read_run(run_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """读取单条运行记录。"""
    resolved_run_id = require_run_id(run_id)
    with connection() as conn:
        cur = conn.execute(
            """
            SELECT run_id, blueprint_id, skill_name, persona_id, status, metadata_json, created_at, updated_at
              FROM trajectory_runs
             WHERE run_id = ?
            """,
            (resolved_run_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    item = dict(row)
    item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    return item


def log_tool_call(
    *,
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    result_text: str = "",
    turn_index: Optional[int] = None,
    run_id: Optional[str] = None,
) -> None:
    """记录工具调用日志。"""
    resolved_run_id = require_run_id(run_id)
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO tool_call_logs (run_id, turn_index, tool_name, arguments_json, result_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                resolved_run_id,
                turn_index,
                tool_name,
                json.dumps(arguments or {}, ensure_ascii=False),
                result_text,
            ),
        )


def read_tool_call_logs(run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """读取当前 run 的工具调用日志。"""
    resolved_run_id = require_run_id(run_id)
    with connection() as conn:
        cur = conn.execute(
            """
            SELECT id, run_id, turn_index, tool_name, arguments_json, result_text, created_at
              FROM tool_call_logs
             WHERE run_id = ?
             ORDER BY id ASC
            """,
            (resolved_run_id,),
        )
        rows = cur.fetchall()

    result: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["arguments"] = json.loads(item.pop("arguments_json") or "{}")
        result.append(item)
    return result


def save_run_output(
    *,
    trajectory_path: str,
    output_json: Dict[str, Any],
    validation: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
) -> None:
    """保存轨迹输出与验证结果。"""
    resolved_run_id = require_run_id(run_id)
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO run_outputs (run_id, trajectory_path, validation_json, output_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                trajectory_path = excluded.trajectory_path,
                validation_json = excluded.validation_json,
                output_json = excluded.output_json,
                updated_at = datetime('now')
            """,
            (
                resolved_run_id,
                trajectory_path,
                json.dumps(validation or {}, ensure_ascii=False),
                json.dumps(output_json, ensure_ascii=False),
            ),
        )


def read_run_output(run_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """读取运行输出。"""
    resolved_run_id = require_run_id(run_id)
    with connection() as conn:
        cur = conn.execute(
            """
            SELECT run_id, trajectory_path, validation_json, output_json, created_at, updated_at
              FROM run_outputs
             WHERE run_id = ?
            """,
            (resolved_run_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    item = dict(row)
    item["validation"] = json.loads(item.pop("validation_json") or "{}")
    item["output"] = json.loads(item.pop("output_json") or "{}")
    return item


def save_run_snapshot(
    snapshot: Dict[str, Any],
    *,
    snapshot_kind: str = "final",
    run_id: Optional[str] = None,
) -> None:
    """写入一份运行快照。"""
    resolved_run_id = require_run_id(run_id)
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO run_snapshots (run_id, snapshot_kind, snapshot_json)
            VALUES (?, ?, ?)
            """,
            (resolved_run_id, snapshot_kind, json.dumps(snapshot, ensure_ascii=False)),
        )


def read_run_snapshots(run_id: Optional[str] = None, *, snapshot_kind: Optional[str] = None) -> List[Dict[str, Any]]:
    """读取当前 run 的快照列表。"""
    resolved_run_id = require_run_id(run_id)
    sql = """
        SELECT id, run_id, snapshot_kind, snapshot_json, created_at
          FROM run_snapshots
         WHERE run_id = ?
    """
    params: List[Any] = [resolved_run_id]
    if snapshot_kind:
        sql += " AND snapshot_kind = ?"
        params.append(snapshot_kind)
    sql += " ORDER BY id ASC"

    with connection() as conn:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()

    result: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["snapshot"] = json.loads(item.pop("snapshot_json") or "{}")
        result.append(item)
    return result


def export_run_state(run_id: Optional[str] = None, *, include_static_tables: bool = True) -> Dict[str, Any]:
    """导出当前 run 的运行态视图；可选附带共享静态表。"""
    resolved_run_id = require_run_id(run_id)
    snapshot: Dict[str, Any] = {
        "run_id": resolved_run_id,
        "trajectory_run": read_run(resolved_run_id),
        "tool_call_logs": read_tool_call_logs(resolved_run_id),
        "run_output": read_run_output(resolved_run_id),
        "run_snapshots": read_run_snapshots(resolved_run_id),
    }
    if include_static_tables:
        snapshot["kalshi_markets"] = read_kalshi_markets(limit=100)
        snapshot["polymarket_events"] = read_polymarket_events(limit=100)
    return snapshot


# ---------- 领域便捷接口：供 tools 与 mocks 使用 ----------

def read_kalshi_markets(
    category: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """读取 Kalshi 市场。category: fed | economics | trending；search_query 时按 title 模糊匹配。"""
    if search_query:
        with connection() as conn:
            cur = conn.execute(
                """SELECT id, category, title, yes_price, no_price, volume, open_interest, close_date
                   FROM kalshi_markets WHERE title LIKE ? ORDER BY volume DESC LIMIT ?""",
                (f"%{search_query}%", limit),
            )
            return [dict(r) for r in cur.fetchall()]
    where = {"category": category} if category else None
    return read(
        "kalshi_markets",
        where=where,
        order_by="volume DESC",
        limit=limit,
    )


def read_polymarket_events(
    category: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """读取 Polymarket 事件。category: trending | crypto；search_query 时按 question 模糊匹配。"""
    if search_query:
        with connection() as conn:
            cur = conn.execute(
                """SELECT id, category, question, yes_price, no_price, volume_display, description
                   FROM polymarket_events WHERE question LIKE ? LIMIT ?""",
                (f"%{search_query}%", limit or 20),
            )
            return [dict(r) for r in cur.fetchall()]
    where = {"category": category} if category else None
    return read(
        "polymarket_events",
        where=where,
        limit=limit or 50,
    )


def ensure_schema_and_initial_data(db_path: Optional[Path] = None) -> None:
    """
    若数据库不存在或表为空，则执行 schema.sql 与 initial_data.sql。
    用于启动时初始化（本地或 Docker）。
    """
    path = db_path or _db_path()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    base = Path(__file__).parent
    schema_file = base / "database" / "schema.sql"
    initial_file = base / "database" / "initial_data.sql"

    conn = sqlite3.connect(str(path))
    try:
        with open(schema_file, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        cur = conn.execute("SELECT COUNT(*) FROM kalshi_markets")
        if cur.fetchone()[0] == 0:
            with open(initial_file, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
        conn.commit()
    finally:
        conn.close()
