-- 初始状态数据：与 Mock 预置数据一致，保证任务可解性与可复现性（确定性种子）

-- Kalshi: Fed 利率相关
INSERT OR REPLACE INTO kalshi_markets (id, category, title, yes_price, no_price, volume, open_interest, close_date) VALUES
('FED-2026-MAR', 'fed', 'Will the Fed cut rates in March 2026?', 0.35, 0.65, 1250000, 450000, '2026-03-31T00:00:00Z'),
('FED-2026-JUN', 'fed', 'Will the Fed cut rates by June 2026?', 0.55, 0.45, 980000, 320000, '2026-06-30T00:00:00Z'),
('FED-RATE-50BP', 'fed', 'Will Fed cut by 50bps in Q2 2026?', 0.22, 0.78, 650000, 180000, '2026-06-30T00:00:00Z'),
('FED-RATE-25BP', 'fed', 'Will Fed cut by 25bps in Q2 2026?', 0.68, 0.32, 890000, 290000, '2026-06-30T00:00:00Z');

-- Kalshi: 经济预测
INSERT OR REPLACE INTO kalshi_markets (id, category, title, yes_price, no_price, volume, open_interest, close_date) VALUES
('GDP-Q1-2026', 'economics', 'Will US GDP grow >2% in Q1 2026?', 0.62, 0.38, 450000, 150000, '2026-04-30T00:00:00Z'),
('CPI-FEB-2026', 'economics', 'Will CPI be <3% in February 2026?', 0.58, 0.42, 380000, 120000, '2026-02-28T00:00:00Z'),
('CPI-MARCH-2026', 'economics', 'Will CPI be <3% in March 2026?', 0.55, 0.45, 410000, 135000, '2026-03-31T00:00:00Z'),
('GDP-Q2-2026', 'economics', 'Will US GDP grow >2.5% in Q2 2026?', 0.48, 0.52, 520000, 180000, '2026-07-31T00:00:00Z');

-- Kalshi: 热门
INSERT OR REPLACE INTO kalshi_markets (id, category, title, yes_price, no_price, volume, open_interest, close_date) VALUES
('BTC-100K', 'trending', 'Will BTC reach $100K by end of 2026?', 0.72, 0.28, 2100000, 850000, '2026-12-31T00:00:00Z'),
('ETH-5K', 'trending', 'Will ETH reach $5K by end of 2026?', 0.65, 0.35, 1800000, 720000, '2026-12-31T00:00:00Z'),
('AI-JOBS', 'trending', 'Will AI create more jobs than it displaces in 2026?', 0.58, 0.42, 950000, 320000, '2026-12-31T00:00:00Z');

-- Polymarket: 热门
INSERT INTO polymarket_events (category, question, yes_price, no_price, volume_display, description) VALUES
('trending', 'Will Bitcoin reach $150K by end of 2026?', 0.45, 0.55, '$4.2M', 'Bitcoin price prediction market'),
('trending', 'Will Ethereum flip Bitcoin market cap by 2027?', 0.18, 0.82, '$2.8M', 'Ethereum vs Bitcoin competition'),
('trending', 'Will Trump win 2026 midterms?', 0.52, 0.48, '$8.1M', 'US politics prediction market'),
('trending', 'Will there be a Fed rate cut in Q2 2026?', 0.68, 0.32, '$5.4M', 'Federal Reserve policy prediction'),
('trending', 'Will Apple release AR glasses in 2026?', 0.35, 0.65, '$1.9M', 'Tech product release predictions');

-- Polymarket: 加密货币
INSERT INTO polymarket_events (category, question, yes_price, no_price, volume_display, description) VALUES
('crypto', 'Bitcoin > $100K by Dec 2026', 0.72, 0.28, '$12.5M', 'Bitcoin price prediction'),
('crypto', 'Ethereum > $3K by June 2026', 0.58, 0.42, '$6.2M', 'Ethereum price prediction'),
('crypto', 'Solana > $500 by June 2026', 0.45, 0.55, '$3.8M', 'Solana price prediction'),
('crypto', 'XRP > $5 by Dec 2026', 0.28, 0.72, '$2.1M', 'XRP price prediction'),
('crypto', 'New crypto ETF approved in 2026', 0.62, 0.38, '$4.5M', 'Crypto ETF predictions');
