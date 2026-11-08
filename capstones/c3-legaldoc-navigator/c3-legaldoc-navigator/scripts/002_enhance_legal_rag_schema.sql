-- =====================================================
-- Legal Document Analysis — Incremental Schema Enhancement
-- Migration: 002_enhance_legal_rag_features
-- Maps reference schema features into existing tables (no renames)
-- =====================================================

-- -----------------------------------------------------
-- documents  ←  reference: document_metadata
-- -----------------------------------------------------
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

-- -----------------------------------------------------
-- clauses  ←  reference: contract_clause_index
-- -----------------------------------------------------
ALTER TABLE clauses ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20);
ALTER TABLE clauses ADD COLUMN IF NOT EXISTS keywords TEXT[];
ALTER TABLE clauses ADD COLUMN IF NOT EXISTS related_clause_ids UUID[];

ALTER TABLE clauses DROP CONSTRAINT IF EXISTS ck_clauses_risk_level;
ALTER TABLE clauses ADD CONSTRAINT ck_clauses_risk_level
    CHECK (risk_level IS NULL OR risk_level IN ('Low', 'Medium', 'High', 'Critical'));

CREATE INDEX IF NOT EXISTS ix_clauses_risk_level ON clauses (risk_level);
CREATE INDEX IF NOT EXISTS ix_clauses_document_risk ON clauses (document_id, risk_level);
CREATE INDEX IF NOT EXISTS ix_clauses_keywords_gin ON clauses USING gin (keywords);

-- -----------------------------------------------------
-- cases  ←  reference: case_law_metadata
-- -----------------------------------------------------
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

-- -----------------------------------------------------
-- statutes  ←  reference: legal_acts_reference
-- -----------------------------------------------------
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

-- -----------------------------------------------------
-- document_embeddings — hybrid chunk retrieval
-- -----------------------------------------------------
ALTER TABLE document_embeddings ADD COLUMN IF NOT EXISTS keywords TEXT[];
ALTER TABLE document_embeddings ADD COLUMN IF NOT EXISTS embedding vector(1536);

CREATE INDEX IF NOT EXISTS ix_document_embeddings_keywords_gin
    ON document_embeddings USING gin (keywords);
CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding_ivfflat
    ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
