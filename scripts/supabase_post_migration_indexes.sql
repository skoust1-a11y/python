-- Idempotent pgvector and metadata indexes for Supabase PostgreSQL.
-- Alembic creates these during `alembic upgrade head`; run this only to verify
-- or repair indexes after a manual schema restore.

CREATE INDEX IF NOT EXISTS ix_documents_keywords_gin
    ON documents USING gin (keywords);

CREATE INDEX IF NOT EXISTS ix_documents_parties_gin
    ON documents USING gin (parties_involved);

CREATE INDEX IF NOT EXISTS ix_clauses_keywords_gin
    ON clauses USING gin (keywords);

CREATE INDEX IF NOT EXISTS ix_cases_keywords_gin
    ON cases USING gin (keywords);

CREATE INDEX IF NOT EXISTS ix_cases_legal_act_refs_gin
    ON cases USING gin (legal_act_references);

CREATE INDEX IF NOT EXISTS ix_cases_embedding_ivfflat
    ON cases USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS ix_statutes_keywords_gin
    ON statutes USING gin (keywords);

CREATE INDEX IF NOT EXISTS ix_statutes_embedding_ivfflat
    ON statutes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS ix_document_embeddings_keywords_gin
    ON document_embeddings USING gin (keywords);

CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding_ivfflat
    ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
