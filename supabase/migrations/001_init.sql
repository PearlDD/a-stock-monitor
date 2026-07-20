-- Supabase migration: initial schema for A股监控系统

CREATE TABLE watchlist (
  code TEXT PRIMARY KEY,
  name TEXT,
  market TEXT,
  sector TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE alert_rules (
  id SERIAL PRIMARY KEY,
  stock_code TEXT NOT NULL,
  stock_name TEXT,
  alert_type TEXT NOT NULL,
  threshold REAL,
  direction TEXT DEFAULT 'above',
  enabled BOOLEAN DEFAULT TRUE,
  triggered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE push_history (
  id SERIAL PRIMARY KEY,
  title TEXT,
  content TEXT,
  status TEXT,
  sent_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE alert_state (
  stock_code TEXT NOT NULL,
  alert_type TEXT NOT NULL,
  last_fired_at TIMESTAMPTZ,
  daily_reset_at DATE,
  PRIMARY KEY (stock_code, alert_type)
);

-- Index for common queries
CREATE INDEX idx_alert_rules_stock ON alert_rules(stock_code);
CREATE INDEX idx_alert_rules_enabled ON alert_rules(enabled) WHERE enabled = TRUE;
CREATE INDEX idx_push_history_sent ON push_history(sent_at);
