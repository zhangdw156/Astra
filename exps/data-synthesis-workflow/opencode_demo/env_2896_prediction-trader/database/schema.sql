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
