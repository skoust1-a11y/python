# Environment Configuration Guide

This document explains the different environment configuration files and how to use them.

## Configuration Files

### `.env` (Production/Development)
**Default environment file for running the application.** Uses PostgreSQL database.

Current settings:
- Database: PostgreSQL 18 on `localhost:5432`
- LLM: Google's Generative Language API (Gemini)
- API Port: 9000

**Setup Required:**
- PostgreSQL server running with user `skoust` / password `password123`
- OpenAI API key configured

**Usage:**
```bash
uv run python -m run
```

---

### `.env.test` (Testing)
**Test environment file for pytest runs.** Uses PostgreSQL database in a separate test database.

Current settings:
- Database: PostgreSQL 18 on `localhost:5432` in `wellbeing_coach_test` database
- LLM: Test mode with mocked responses
- Log Level: DEBUG
- Test Mode: Enabled

**Benefits:**
- ✅ Same PostgreSQL as production (consistent testing)
- ✅ Isolated test database (separate from development data)
- ✅ Automatic table creation and cleanup
- ✅ Reproducible test results

**Setup Required:**
- PostgreSQL server running
- Test database created (see setup instructions below)

**Usage:**
```bash
# Automatically uses .env.test when running pytest
uv run python -m pytest tests/unit/services/ -v

# Or explicitly
uv run python -m pytest tests/ --tb=short
```

**Creating Test Database:**

Option 1: Using Python script (cross-platform)
```bash
uv run python scripts/create_test_db.py
```

Option 2: Using bash script (macOS/Linux)
```bash
bash scripts/create_test_db.sh
```

Option 3: Manual
```bash
# Create database
PGPASSWORD=password123 createdb -h localhost -U skoust wellbeing_coach_test

# Verify
psql -h localhost -U skoust -d wellbeing_coach_test -c "SELECT version();"
```

---

### `.env.example`
**Template file showing all available configuration options.**

Use this as a reference to:
- See what environment variables are available
- Understand what each setting does
- Create new configuration files

**Not used directly by the application** - it's documentation only.

---

## Quick Start

### For Running the Application

```bash
# Run with default .env (PostgreSQL):
uv run python -m run
```

### For Running Tests

```bash
# Step 1: Create test database (first time only)
uv run python scripts/create_test_db.py

# Step 2: Run tests (automatically uses .env.test)
uv run python -m pytest tests/unit/services/ -v

# Or run all tests
uv run python -m pytest tests/ -v
```

---

## Environment File Precedence

When running pytest, conftest.py loads environment variables in this order:

1. **`.env.test`** (if it exists) - ✅ Test-specific settings (PostgreSQL test database)
2. **`.env`** (fallback) - Production/development settings
3. **Environment variables** - Highest priority

This ensures tests always use the dedicated test database even if `.env` is configured for the main database.

---

## Creating Custom Test Configurations

Need a different test setup? Create a new env file:

```bash
# For load testing (SQLite with relaxed limits)
cp .env.test .env.loadtest
# Then edit .env.loadtest and adjust settings

# For CI/CD (minimal logging)
cp .env.test .env.ci
# Edit .env.ci: LOG_LEVEL=ERROR
```

To use custom env file:
1. Edit `tests/conftest.py` 
2. Change the env file path in the `load_dotenv()` call
3. Run tests

---

## Database Configuration Examples

### PostgreSQL (Production)
```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/dbname
```

### SQLite (Testing/Development)
```env
# File-based (persists across runs)
DATABASE_URL=sqlite:///./wellbeing_coach.db

# In-memory (fresh database each run)
DATABASE_URL=sqlite:///:memory:
```

### From Individual Variables
```env
DB_USER=skoust
DB_PASSWORD=password123
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wellbeing_coach
```

---

## Troubleshooting

### "Connection to server at localhost:5432 failed"
**Problem:** PostgreSQL not running or test database doesn't exist

**Solution:** 
- Start PostgreSQL: `brew services start postgresql` (macOS)
- Create test database: `uv run python scripts/create_test_db.py`
- Check connection: `psql -h localhost -U skoust -d postgres`

### "FATAL: database 'wellbeing_coach_test' does not exist"
**Problem:** Test database not created

**Solution:** Create it with:
```bash
uv run python scripts/create_test_db.py
```

### "FATAL: role 'skoust' does not exist"
**Problem:** PostgreSQL user doesn't exist

**Solution:**
```bash
# Create the user
psql -U postgres -c "CREATE USER skoust WITH PASSWORD 'password123';"
psql -U postgres -c "ALTER USER skoust CREATEDB;"

# Then create test database
uv run python scripts/create_test_db.py
```

### "no such table: interactions"
**Problem:** Tables not created in test database

**Solution:** Normal! Tests create tables automatically via conftest.py fixtures.
- Check conftest.py is being loaded
- Verify test database exists: `psql -h localhost -U skoust -d wellbeing_coach_test -c "\dt"`

### Tests using production database
**Problem:** Tests modifying main database instead of test database

**Solution:** Ensure `.env.test` exists with correct test database name:
```bash
# Check file exists
ls -la .env.test

# Verify DATABASE_URL or DB_NAME points to test database
grep -E "DATABASE_URL|DB_NAME" .env.test
```

---

## Best Practices

✅ **Do:**
- Use `.env.test` for pytest runs
- Keep `.env` for production/development
- Use `.env.example` as documentation
- Don't commit `.env` (it contains secrets!)
- Add `.env*` to `.gitignore`

❌ **Don't:**
- Share `.env` files with credentials
- Modify `.env.example` with real secrets
- Use production PostgreSQL for testing
- Commit changes to `.env.test` if using CI/CD

---

## See Also

- [pytest Documentation](https://docs.pytest.org/)
- [SQLAlchemy Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [Testing Guide](SERVICES_TEST_GUIDE.md)
