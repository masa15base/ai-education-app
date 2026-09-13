-- Google Fit 連携・歩数ソース列（JawsDB / MySQL）
-- mysql "$JAWSDB_URL" < backend/scripts/heroku_add_fitness_connections.sql

ALTER TABLE daily_steps ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'manual';

CREATE TABLE IF NOT EXISTS user_fitness_connections (
  user_id VARCHAR(128) NOT NULL PRIMARY KEY,
  provider VARCHAR(32) NOT NULL DEFAULT 'google_fit',
  refresh_token MEDIUMTEXT NOT NULL,
  last_sync_at DATETIME NULL,
  connected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
