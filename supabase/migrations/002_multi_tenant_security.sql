-- Multi-user isolation. This migration preserves legacy rows; it never deletes them.
-- Legacy rows have user_id NULL and are intentionally not exposed to a newly logged-in user.

ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE push_history ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE watchlist DROP CONSTRAINT IF EXISTS watchlist_pkey;
-- NULL user_id keeps legacy rows intact; PostgreSQL considers NULL values
-- distinct, while each authenticated user gets a unique (user_id, code) pair.
ALTER TABLE watchlist ADD CONSTRAINT watchlist_user_code_key UNIQUE (user_id, code);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_user_enabled ON alert_rules(user_id) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_push_history_user_sent ON push_history(user_id, sent_at);

CREATE TABLE IF NOT EXISTS push_settings (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  token_ciphertext TEXT NOT NULL,
  token_iv TEXT NOT NULL,
  token_tag TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alert_deliveries (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  alert_rule_id INTEGER NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
  trading_date DATE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('sending', 'sent', 'failed')),
  attempts INTEGER NOT NULL DEFAULT 1,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(alert_rule_id, trading_date)
);

ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_history ENABLE ROW LEVEL SECURITY;
-- Legacy state is superseded by alert_deliveries. Keep it inaccessible rather
-- than exposing historical trigger data to every authenticated user.
ALTER TABLE alert_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_deliveries ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users manage own watchlist" ON watchlist;
CREATE POLICY "Users manage own watchlist" ON watchlist FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "Users manage own alert rules" ON alert_rules;
CREATE POLICY "Users manage own alert rules" ON alert_rules FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "Users view own push history" ON push_history;
CREATE POLICY "Users view own push history" ON push_history FOR SELECT USING (user_id = auth.uid());
DROP POLICY IF EXISTS "Users manage own push settings" ON push_settings;
CREATE POLICY "Users manage own push settings" ON push_settings FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "Users view own deliveries" ON alert_deliveries;
CREATE POLICY "Users view own deliveries" ON alert_deliveries FOR SELECT USING (
  EXISTS (SELECT 1 FROM alert_rules WHERE alert_rules.id = alert_deliveries.alert_rule_id AND alert_rules.user_id = auth.uid())
);

-- Atomically reserve one send. A stale reservation is retried after 10 minutes.
CREATE OR REPLACE FUNCTION claim_alert_delivery(p_rule_id INTEGER, p_date DATE)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO alert_deliveries (alert_rule_id, trading_date, status)
  VALUES (p_rule_id, p_date, 'sending')
  ON CONFLICT (alert_rule_id, trading_date) DO UPDATE
  SET status = 'sending', attempts = alert_deliveries.attempts + 1, updated_at = now(), last_error = NULL
  WHERE alert_deliveries.status = 'failed'
     OR (alert_deliveries.status = 'sending' AND alert_deliveries.updated_at < now() - interval '10 minutes');
  RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION finish_alert_delivery(p_rule_id INTEGER, p_date DATE, p_success BOOLEAN, p_error TEXT DEFAULT NULL)
RETURNS VOID LANGUAGE sql SECURITY DEFINER SET search_path = public AS $$
  UPDATE alert_deliveries SET status = CASE WHEN p_success THEN 'sent' ELSE 'failed' END,
    last_error = p_error, updated_at = now()
  WHERE alert_rule_id = p_rule_id AND trading_date = p_date;
$$;
