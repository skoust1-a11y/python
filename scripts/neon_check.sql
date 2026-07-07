-- Run this first in Neon SQL Editor to see current database state.

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

SELECT * FROM alembic_version;
