-- Performance indexes for the API optimization pass (2026-09-01).
--
-- Run this directly against Postgres, e.g.:
--   psql "$DATABASE_URL" -f sql/2026_09_01_add_performance_indexes.sql
-- or, inside the db container:
--   docker exec -i yashilqollar-db psql -U postgres -d postgres < sql/2026_09_01_add_performance_indexes.sql
--
-- CONCURRENTLY builds each index without taking a write lock on the table,
-- so the site stays fully usable while these run (a few seconds to a
-- couple of minutes depending on table size). Each statement commits on
-- its own — do NOT wrap this file in BEGIN/COMMIT, and do NOT run it
-- inside a transaction (CREATE INDEX CONCURRENTLY is not allowed there).
--
-- These match the db_index=True / Meta.indexes additions in
-- app_telegram/models.py. This file exists instead of a Django migration
-- because the migration history is currently out of sync with models.py
-- (last migration is 0011, but models.py has ~14 models/fields that were
-- never migrated) — see the conversation this was generated in for detail.
-- Once that gap is reconciled, these can be folded into a proper migration
-- and this file retired.

CREATE INDEX CONCURRENTLY IF NOT EXISTS app_telegram_tguser_region_idx
    ON app_telegram_tguser (region);

CREATE INDEX CONCURRENTLY IF NOT EXISTS app_telegram_tguser_role_idx
    ON app_telegram_tguser (role);

CREATE INDEX CONCURRENTLY IF NOT EXISTS app_telegram_tguser_balance_idx
    ON app_telegram_tguser (balance);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ecoproj_active_date_idx
    ON app_telegram_ecoproject (is_active, date);

CREATE INDEX CONCURRENTLY IF NOT EXISTS comment_article_parent_idx
    ON app_telegram_comment (article_id, parent_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ecoprojcomment_proj_par_idx
    ON app_telegram_ecoprojectcomment (project_id, parent_id);
