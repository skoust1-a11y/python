-- =============================================================================
-- C3 LegalDoc Navigator — full Neon schema (migrations 001–005)
-- Run in: Neon Dashboard → SQL Editor
--
-- BEFORE RUNNING:
--   1. Run neon_check.sql (or the CHECK section below) to see what exists.
--   2. If you have a broken partial migration, run neon_reset.sql first.
--   3. Then run this file.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- users
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(32) NOT NULL DEFAULT 'analyst',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);
CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active);

-- -----------------------------------------------------------------------------
-- cases
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY,
    case_citation VARCHAR(512) NOT NULL UNIQUE,
    case_name VARCHAR(512) NOT NULL,
    court VARCHAR(255),
    jurisdiction VARCHAR(128),
    decision_date DATE,
    docket_number VARCHAR(128),
    summary TEXT,
    full_text TEXT,
    case_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_cases_court ON cases (court);
CREATE INDEX IF NOT EXISTS ix_cases_jurisdiction ON cases (jurisdiction);
CREATE INDEX IF NOT EXISTS ix_cases_decision_date ON cases (decision_date);
CREATE INDEX IF NOT EXISTS ix_cases_docket_number ON cases (docket_number);

-- -----------------------------------------------------------------------------
-- statutes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS statutes (
    id UUID PRIMARY KEY,
    statute_code VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(512),
    jurisdiction VARCHAR(128),
    section_number VARCHAR(64),
    full_text TEXT,
    effective_date DATE,
    statute_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_statutes_jurisdiction ON statutes (jurisdiction);
CREATE INDEX IF NOT EXISTS ix_statutes_section_number ON statutes (section_number);
CREATE INDEX IF NOT EXISTS ix_statutes_effective_date ON statutes (effective_date);

-- -----------------------------------------------------------------------------
-- documents
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users (id) ON DELETE SET NULL,
    filename VARCHAR(512) NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    storage_path VARCHAR(1024),
    title VARCHAR(512),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    content_hash VARCHAR(64),
    page_count INTEGER,
    doc_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_documents_user_id ON documents (user_id);
CREATE INDEX IF NOT EXISTS ix_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS ix_documents_content_hash ON documents (content_hash);
CREATE INDEX IF NOT EXISTS ix_documents_created_at ON documents (created_at);

-- -----------------------------------------------------------------------------
-- clauses
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clauses (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    parent_clause_id UUID REFERENCES clauses (id) ON DELETE SET NULL,
    clause_number VARCHAR(64),
    title VARCHAR(512),
    content TEXT NOT NULL,
    clause_type VARCHAR(64),
    page_number INTEGER,
    position_order INTEGER NOT NULL DEFAULT 0,
    clause_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_clauses_document_id ON clauses (document_id);
CREATE INDEX IF NOT EXISTS ix_clauses_parent_clause_id ON clauses (parent_clause_id);
CREATE INDEX IF NOT EXISTS ix_clauses_clause_type ON clauses (clause_type);
CREATE INDEX IF NOT EXISTS ix_clauses_document_position ON clauses (document_id, position_order);

-- -----------------------------------------------------------------------------
-- citations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS citations (
    id UUID PRIMARY KEY,
    source_type VARCHAR(32) NOT NULL,
    source_document_id UUID REFERENCES documents (id) ON DELETE CASCADE,
    source_clause_id UUID REFERENCES clauses (id) ON DELETE CASCADE,
    cited_case_id UUID REFERENCES cases (id) ON DELETE SET NULL,
    cited_statute_id UUID REFERENCES statutes (id) ON DELETE SET NULL,
    citation_text TEXT NOT NULL,
    context TEXT,
    position_start INTEGER,
    position_end INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_citations_source_type ON citations (source_type);
CREATE INDEX IF NOT EXISTS ix_citations_source_document_id ON citations (source_document_id);
CREATE INDEX IF NOT EXISTS ix_citations_source_clause_id ON citations (source_clause_id);
CREATE INDEX IF NOT EXISTS ix_citations_cited_case_id ON citations (cited_case_id);
CREATE INDEX IF NOT EXISTS ix_citations_cited_statute_id ON citations (cited_statute_id);

-- -----------------------------------------------------------------------------
-- document_embeddings
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    clause_id UUID REFERENCES clauses (id) ON DELETE SET NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    embedding_model VARCHAR(128) NOT NULL,
    vector_store_id VARCHAR(255),
    token_count INTEGER,
    content_preview TEXT,
    embed_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_document_embeddings_doc_chunk UNIQUE (document_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS ix_document_embeddings_document_id ON document_embeddings (document_id);
CREATE INDEX IF NOT EXISTS ix_document_embeddings_clause_id ON document_embeddings (clause_id);
CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding_model ON document_embeddings (embedding_model);

-- -----------------------------------------------------------------------------
-- chat_history
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users (id) ON DELETE SET NULL,
    document_id UUID REFERENCES documents (id) ON DELETE SET NULL,
    session_id UUID NOT NULL,
    role VARCHAR(32) NOT NULL,
    message TEXT NOT NULL,
    provider VARCHAR(64),
    model VARCHAR(128),
    token_count INTEGER,
    chat_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_history_user_id ON chat_history (user_id);
CREATE INDEX IF NOT EXISTS ix_chat_history_document_id ON chat_history (document_id);
CREATE INDEX IF NOT EXISTS ix_chat_history_session_id ON chat_history (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_history_created_at ON chat_history (created_at);
CREATE INDEX IF NOT EXISTS ix_chat_history_session_created ON chat_history (session_id, created_at);

-- -----------------------------------------------------------------------------
-- Migration 002: extra columns + indexes
-- -----------------------------------------------------------------------------
ALTER TABLE documents ADD COLUMN IF NOT EXISTS contract_id VARCHAR(100);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_subtype VARCHAR(100);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_date DATE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS parties_involved TEXT[];
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunk_count INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS keywords TEXT[];
ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_contract_id ON documents (contract_id);
CREATE INDEX IF NOT EXISTS ix_documents_document_subtype ON documents (document_subtype);
CREATE INDEX IF NOT EXISTS ix_documents_document_date ON documents (document_date);
CREATE INDEX IF NOT EXISTS ix_documents_keywords_gin ON documents USING gin (keywords);
CREATE INDEX IF NOT EXISTS ix_documents_parties_gin ON documents USING gin (parties_involved);

ALTER TABLE clauses ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20);
ALTER TABLE clauses ADD COLUMN IF NOT EXISTS keywords TEXT[];
ALTER TABLE clauses ADD COLUMN IF NOT EXISTS related_clause_ids UUID[];
ALTER TABLE clauses DROP CONSTRAINT IF EXISTS ck_clauses_risk_level;
ALTER TABLE clauses ADD CONSTRAINT ck_clauses_risk_level
    CHECK (risk_level IS NULL OR risk_level IN ('Low', 'Medium', 'High', 'Critical'));
CREATE INDEX IF NOT EXISTS ix_clauses_risk_level ON clauses (risk_level);
CREATE INDEX IF NOT EXISTS ix_clauses_document_risk ON clauses (document_id, risk_level);
CREATE INDEX IF NOT EXISTS ix_clauses_keywords_gin ON clauses USING gin (keywords);

ALTER TABLE cases ADD COLUMN IF NOT EXISTS filing_date DATE;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS case_type VARCHAR(100);
ALTER TABLE cases ADD COLUMN IF NOT EXISTS case_status VARCHAR(50);
ALTER TABLE cases ADD COLUMN IF NOT EXISTS primary_judge VARCHAR(200);
ALTER TABLE cases ADD COLUMN IF NOT EXISTS keywords TEXT[];
ALTER TABLE cases ADD COLUMN IF NOT EXISTS legal_act_references TEXT[];
ALTER TABLE cases ADD COLUMN IF NOT EXISTS embedding vector(1536);
CREATE INDEX IF NOT EXISTS ix_cases_filing_date ON cases (filing_date);
CREATE INDEX IF NOT EXISTS ix_cases_case_type ON cases (case_type);
CREATE INDEX IF NOT EXISTS ix_cases_case_status ON cases (case_status);
CREATE INDEX IF NOT EXISTS ix_cases_keywords_gin ON cases USING gin (keywords);
CREATE INDEX IF NOT EXISTS ix_cases_legal_act_refs_gin ON cases USING gin (legal_act_references);
CREATE INDEX IF NOT EXISTS ix_cases_embedding_ivfflat ON cases
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

ALTER TABLE statutes ADD COLUMN IF NOT EXISTS act_name TEXT;
ALTER TABLE statutes ADD COLUMN IF NOT EXISTS act_short_name VARCHAR(200);
ALTER TABLE statutes ADD COLUMN IF NOT EXISTS section_title TEXT;
ALTER TABLE statutes ADD COLUMN IF NOT EXISTS enactment_year INTEGER;
ALTER TABLE statutes ADD COLUMN IF NOT EXISTS category VARCHAR(100);
ALTER TABLE statutes ADD COLUMN IF NOT EXISTS application_notes TEXT;
ALTER TABLE statutes ADD COLUMN IF NOT EXISTS keywords TEXT[];
ALTER TABLE statutes ADD COLUMN IF NOT EXISTS embedding vector(1536);
CREATE INDEX IF NOT EXISTS ix_statutes_act_short_name ON statutes (act_short_name);
CREATE INDEX IF NOT EXISTS ix_statutes_category ON statutes (category);
CREATE INDEX IF NOT EXISTS ix_statutes_enactment_year ON statutes (enactment_year);
CREATE INDEX IF NOT EXISTS ix_statutes_keywords_gin ON statutes USING gin (keywords);
CREATE INDEX IF NOT EXISTS ix_statutes_embedding_ivfflat ON statutes
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

ALTER TABLE document_embeddings ADD COLUMN IF NOT EXISTS keywords TEXT[];
ALTER TABLE document_embeddings ADD COLUMN IF NOT EXISTS embedding vector(1536);
CREATE INDEX IF NOT EXISTS ix_document_embeddings_keywords_gin ON document_embeddings USING gin (keywords);
CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding_ivfflat ON document_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- -----------------------------------------------------------------------------
-- Migration 003: chunk_text
-- -----------------------------------------------------------------------------
ALTER TABLE document_embeddings ADD COLUMN IF NOT EXISTS chunk_text TEXT;

-- -----------------------------------------------------------------------------
-- Migration 004: feedback
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    query_text TEXT,
    document_id UUID REFERENCES documents (id) ON DELETE SET NULL,
    session_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_feedback_document_id ON feedback (document_id);
CREATE INDEX IF NOT EXISTS ix_feedback_created_at ON feedback (created_at);

-- -----------------------------------------------------------------------------
-- Migration 005: handoff_escalations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS handoff_escalations (
    id UUID PRIMARY KEY,
    session_id UUID,
    user_id UUID REFERENCES users (id) ON DELETE SET NULL,
    document_id UUID REFERENCES documents (id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    answer TEXT,
    summary TEXT NOT NULL,
    conversation_history JSONB,
    retrieved_documents JSONB,
    sources JSONB,
    confidence_score DOUBLE PRECISION NOT NULL,
    escalation_reasons JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_handoff_escalations_status
        CHECK (status IN ('pending', 'assigned', 'resolved'))
);
CREATE INDEX IF NOT EXISTS ix_handoff_escalations_session_id ON handoff_escalations (session_id);
CREATE INDEX IF NOT EXISTS ix_handoff_escalations_status ON handoff_escalations (status);
CREATE INDEX IF NOT EXISTS ix_handoff_escalations_created_at ON handoff_escalations (created_at);

-- -----------------------------------------------------------------------------
-- updated_at triggers
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'users', 'documents', 'clauses', 'cases', 'statutes', 'citations',
        'document_embeddings', 'chat_history', 'feedback', 'handoff_escalations'
    ]
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_updated_at ON %I', t, t);
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
            t, t
        );
    END LOOP;
END $$;

-- -----------------------------------------------------------------------------
-- Alembic version (short ID fits VARCHAR(32))
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('005_handoff_escalations');
