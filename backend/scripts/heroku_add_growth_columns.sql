-- Heroku JawsDB (MySQL): 成長ロジック用カラム追加（本番は一度だけ実行）
-- mysql ... < backend/scripts/heroku_add_growth_columns.sql
-- 既に列がある場合はエラーになるので、その ALTER 行をスキップしてください。

ALTER TABLE user_characters ADD COLUMN steps_growth_ymd VARCHAR(10) NULL;
ALTER TABLE user_characters ADD COLUMN steps_xp_paid_tier INT NOT NULL DEFAULT 0;
ALTER TABLE user_characters ADD COLUMN steps_xp_goal_bonus TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE progress_entries ADD COLUMN gained_xp INT NOT NULL DEFAULT 0;
