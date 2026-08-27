-- 進化ビジュアル永続化（JawsDB / MySQL）
-- mysql "$JAWSDB_URL" < backend/scripts/heroku_add_evolution_visuals.sql
-- または: python backend/scripts/run_jawsdb_sql.py backend/scripts/heroku_add_evolution_visuals.sql

ALTER TABLE user_character_growth_stats ADD COLUMN hero_preview_url MEDIUMTEXT NULL;
ALTER TABLE user_character_growth_stats ADD COLUMN next_stage_preview_url MEDIUMTEXT NULL;
ALTER TABLE user_character_growth_stats ADD COLUMN character_dna JSON NULL;
ALTER TABLE user_character_growth_stats ADD COLUMN image_understanding JSON NULL;
