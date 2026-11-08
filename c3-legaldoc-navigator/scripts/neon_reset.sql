-- WARNING: Deletes ALL app tables and data. Only run on an empty/test database.
-- Run neon_check.sql first. Skip this if you already have data you need to keep.

DROP TABLE IF EXISTS handoff_escalations CASCADE;
DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS chat_history CASCADE;
DROP TABLE IF EXISTS document_embeddings CASCADE;
DROP TABLE IF EXISTS citations CASCADE;
DROP TABLE IF EXISTS clauses CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS cases CASCADE;
DROP TABLE IF EXISTS statutes CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS alembic_version CASCADE;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents;
DROP TRIGGER IF EXISTS trg_clauses_updated_at ON clauses;
DROP TRIGGER IF EXISTS trg_cases_updated_at ON cases;
DROP TRIGGER IF EXISTS trg_statutes_updated_at ON statutes;
DROP TRIGGER IF EXISTS trg_citations_updated_at ON citations;
DROP TRIGGER IF EXISTS trg_document_embeddings_updated_at ON document_embeddings;
DROP TRIGGER IF EXISTS trg_chat_history_updated_at ON chat_history;
DROP FUNCTION IF EXISTS set_updated_at();
