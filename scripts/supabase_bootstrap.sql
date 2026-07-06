-- Supabase bootstrap for C3 LegalDoc Navigator.
-- Run this once in the Supabase SQL Editor before deploying the Render service.
-- The table schema is managed by Alembic: alembic upgrade head.

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

INSERT INTO storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
)
VALUES (
    'legal-documents',
    'legal-documents',
    false,
    52428800,
    ARRAY[
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ]
)
ON CONFLICT (id) DO UPDATE
SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;
