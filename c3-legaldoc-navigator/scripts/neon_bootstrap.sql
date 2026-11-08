-- Neon PostgreSQL bootstrap for C3 LegalDoc Navigator.
-- Run once in the Neon SQL Editor before the first Render deploy.
-- Alembic migrations (`alembic upgrade head`) create the full relational schema.

CREATE EXTENSION IF NOT EXISTS vector;
