#!/bin/bash
# Create PostgreSQL test database for Wellbeing Coach
# Run this before running tests for the first time

set -e

# Configuration
DB_USER="skoust"
DB_PASSWORD="password123"
DB_HOST="localhost"
DB_PORT="5432"
TEST_DB="wellbeing_coach_test"
ADMIN_DB="postgres"

echo "🗄️  Creating test database..."
echo "================================"
echo "Host: $DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo "Database: $TEST_DB"
echo "================================"

# Check if PostgreSQL is running
if ! pg_isready -h "$DB_HOST" -U "$DB_USER" > /dev/null 2>&1; then
    echo "❌ ERROR: PostgreSQL is not running or user '$DB_USER' cannot connect"
    echo ""
    echo "Try one of the following:"
    echo "1. Start PostgreSQL: brew services start postgresql"
    echo "2. Check connection: psql -h $DB_HOST -U $DB_USER -d $ADMIN_DB"
    echo "3. Verify .env.test has correct DB_USER and DB_PASSWORD"
    exit 1
fi

# Create test database if it doesn't exist
echo "✓ PostgreSQL is running"
echo ""

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$ADMIN_DB" <<EOF
-- Create test database if not exists
SELECT 'CREATE DATABASE $TEST_DB' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$TEST_DB')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $TEST_DB TO $DB_USER;

-- Show status
\l $TEST_DB

EOF

echo ""
echo "✅ Test database created successfully!"
echo ""
echo "Next steps:"
echo "1. Run tests: uv run python -m pytest tests/unit/services/ -v"
echo "2. Or: uv run python -m pytest tests/ -v"
echo ""
echo "To drop the test database later:"
echo "  PGPASSWORD=$DB_PASSWORD dropdb -h $DB_HOST -U $DB_USER $TEST_DB"
