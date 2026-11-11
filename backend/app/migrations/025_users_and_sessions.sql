-- Sign-in (SRS USR-1 to USR-4).
--
-- users: the people who sign in, with a role of admin or operator.
-- user_sessions: one row per signed-in browser. The cookie carries a random
--   token; only its SHA-256 digest is stored, so a copy of this table cannot
--   be replayed as a session.
-- login_attempts: one row per sign-in attempt, for rate limiting.
-- recorded_by_user_id: who entered each bag event and each harvest. Null on
--   rows written before sign-in existed.
CREATE TABLE IF NOT EXISTS users (
  user_id SERIAL PRIMARY KEY,
  email VARCHAR(254) NOT NULL UNIQUE,
  display_name VARCHAR(120) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'operator' CHECK (role IN ('admin', 'operator')),
  password_hash VARCHAR(200) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ,
  CHECK (email = lower(email))
);

CREATE TABLE IF NOT EXISTS user_sessions (
  session_id SERIAL PRIMARY KEY,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  user_agent VARCHAR(300),
  ip_address VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS ix_user_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_expires ON user_sessions(expires_at);

CREATE TABLE IF NOT EXISTS login_attempts (
  login_attempt_id SERIAL PRIMARY KEY,
  email VARCHAR(254) NOT NULL,
  ip_address VARCHAR(64),
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  succeeded BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_login_attempts_email_time ON login_attempts(email, attempted_at);
CREATE INDEX IF NOT EXISTS ix_login_attempts_ip_time ON login_attempts(ip_address, attempted_at);

ALTER TABLE bag_status_events
  ADD COLUMN IF NOT EXISTS recorded_by_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL;
ALTER TABLE harvest_events
  ADD COLUMN IF NOT EXISTS recorded_by_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL;
