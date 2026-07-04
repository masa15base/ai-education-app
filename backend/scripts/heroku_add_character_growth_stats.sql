-- キャラ成長・進化ステータス（JawsDB / MySQL）
CREATE TABLE IF NOT EXISTS user_character_growth_stats (
  user_id VARCHAR(128) NOT NULL PRIMARY KEY,
  stage VARCHAR(20) NOT NULL DEFAULT 'egg',
  quiz_correct_count INT NOT NULL DEFAULT 0,
  quiz_total_count INT NOT NULL DEFAULT 0,
  quiz_streak_days INT NOT NULL DEFAULT 0,
  total_steps INT NOT NULL DEFAULT 0,
  login_streak_days INT NOT NULL DEFAULT 0,
  last_quiz_ymd VARCHAR(10) NULL,
  last_login_ymd VARCHAR(10) NULL,
  has_character_image TINYINT(1) NOT NULL DEFAULT 0,
  excited_until DATETIME NULL,
  hero_preview_url MEDIUMTEXT NULL,
  next_stage_preview_url MEDIUMTEXT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 既存テーブル向け（列がある場合はエラーになるので手動で実行）
-- ALTER TABLE user_character_growth_stats ADD COLUMN hero_preview_url MEDIUMTEXT NULL;
-- ALTER TABLE user_character_growth_stats ADD COLUMN next_stage_preview_url MEDIUMTEXT NULL;
