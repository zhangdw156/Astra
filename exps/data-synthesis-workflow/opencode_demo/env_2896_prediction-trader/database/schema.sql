-- Prediction Trader 环境状态 Schema
-- 依据 DATA_SYNTHESIS_TECH_ROUTE 数据库驱动状态管理，SQLite 作为唯一状态后端

-- Kalshi 预测市场（CFTC 监管美国市场：美联储、经济等）
CREATE TABLE IF NOT EXISTS kalshi_markets (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,  -- fed | economics | trending
    title TEXT NOT NULL,
    yes_price REAL NOT NULL,
    no_price REAL NOT NULL,
    volume INTEGER NOT NULL DEFAULT 0,
    open_interest INTEGER NOT NULL DEFAULT 0,
    close_date TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_kalshi_category ON kalshi_markets(category);
CREATE INDEX IF NOT EXISTS idx_kalshi_title ON kalshi_markets(title);

-- Polymarket 预测事件（离岸 Polygon 市场：加密货币、政治、体育等）
CREATE TABLE IF NOT EXISTS polymarket_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,  -- trending | crypto | search
    question TEXT NOT NULL,
    yes_price REAL NOT NULL,
    no_price REAL NOT NULL,
    volume_display TEXT,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_polymarket_category ON polymarket_events(category);
CREATE INDEX IF NOT EXISTS idx_polymarket_question ON polymarket_events(question);

-- 运行态：轨迹级别元数据（按 run_id 隔离）
CREATE TABLE IF NOT EXISTS trajectory_runs (
    run_id TEXT PRIMARY KEY,
    blueprint_id TEXT,
    skill_name TEXT,
    persona_id TEXT,
    status TEXT NOT NULL DEFAULT 'created',  -- created | running | completed | failed
    metadata_json TEXT,  -- 运行时补充信息（模型、环境、备注等）
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_trajectory_runs_status ON trajectory_runs(status);

-- 运行态：工具调用日志（按 run_id 隔离）
CREATE TABLE IF NOT EXISTS tool_call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    turn_index INTEGER,
    tool_name TEXT NOT NULL,
    arguments_json TEXT,
    result_text TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES trajectory_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tool_call_logs_run_id ON tool_call_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_tool_call_logs_run_turn ON tool_call_logs(run_id, turn_index);

-- 运行态：轨迹输出与验证结果（按 run_id 隔离）
CREATE TABLE IF NOT EXISTS run_outputs (
    run_id TEXT PRIMARY KEY,
    trajectory_path TEXT,
    validation_json TEXT,
    output_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES trajectory_runs(run_id) ON DELETE CASCADE
);

-- 运行态：状态快照（按 run_id 隔离）
CREATE TABLE IF NOT EXISTS run_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    snapshot_kind TEXT NOT NULL DEFAULT 'final',  -- initial | final | custom
    snapshot_json TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES trajectory_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_run_snapshots_run_kind ON run_snapshots(run_id, snapshot_kind);
