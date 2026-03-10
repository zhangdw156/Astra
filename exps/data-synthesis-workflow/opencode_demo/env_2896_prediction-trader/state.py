"""
状态访问层（State Access Layer）

依据 DATA_SYNTHESIS_TECH_ROUTE：工具通过本层操作 SQLite，状态可追踪、可回滚、可验证。
封装 read / write / delete / transaction，Mock 与 tools 统一从同一数据库读取。
"""

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

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
