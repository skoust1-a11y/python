# Environment Configuration Files Summary

## Quick Reference

| File | Purpose | Database | Use Case |
|------|---------|----------|----------|
| `.env` | Production/Development | PostgreSQL (wellbeing_coach) | Running the app with real data |
| `.env.test` | Testing | PostgreSQL (wellbeing_coach_test) | Running pytest (most common) |
| `.env.local` | Local Development | SQLite | Development without PostgreSQL |
| `.env.example` | Documentation | N/A | Reference - never loaded |
| `.env.ci` | CI/CD Pipeline | PostgreSQL | Automated testing (GitHub Actions) |

---

## File Details

### `.env` - Production/Development Configuration
**When to use:** Running the application

```bash
uv run python -m run
```

**Key settings:**
- Database: PostgreSQL on localhost:5432, database `wellbeing_coach`
- User: skoust
- Debug: True (can set to False for production)
- API endpoints available at http://localhost:9000

**Credentials:** Edit before running:
- `DB_PASSWORD=password123`
- `OPENAI_API_KEY=sk-proj-...`

---

### `.env.test` 👍 Test Environment
**When to use:** Running pytest

```bash
# Step 1: Create test database (first time only)
uv run python scripts/create_test_db.py

# Step 2: Run pytest
uv run python -m pytest tests/unit/services/ -v
```

**Key features:**
- ✅ PostgreSQL database (isolated test database)
- ✅ Same database engine as production
- ✅ Automatic table creation/cleanup
- ✅ Separate from development data
- ✅ Perfect for CI/CD

**Why PostgreSQL for tests:**
- Uses same database as production (fewer surprises)
- Isolated test database (doesn't affect development data)
- Automatic cleanup between test sessions
- Reliable and reproducible
- Better catches database-specific issues

**Setup:**
```bash
# Create test database
uv run python scripts/create_test_db.py

# Verify it works
psql -h localhost -U skoust -d wellbeing_coach_test
```

### `.env.local` - Local Development
**When to use:** Local development with SQLite

```bash
# Copy to .env for local development
cp .env.local .env
uv run python -m run
```

**Key settings:**
- Database: SQLite (wellbeing_coach_dev.db)
- Debug: True
- Mock data: Enabled
- Relaxed rate limiting

**Benefits:**
- No PostgreSQL required
- Persistent local data
- Easy testing and debugging

---

### `.env.example` - Configuration Reference
**When to use:** Reference for available settings

- Shows all environment variables
- Explains what each setting does
- Template for creating new configs

**Never loaded automatically** - it's documentation only.

---

### `.env.ci` - CI/CD Configuration
**When to use:** GitHub Actions / CI pipelines

Located at: `.github/workflows/tests.yml`

**Configuration:**
- Database: SQLite with in-memory option
- Logging: ERROR level (less output)
- Coverage reporting: Enabled
- Test parallelization: Supported

---

## How Environment Variables Are Loaded

### For Running the Application
```python
from dotenv import load_dotenv
load_dotenv('.env')  # Loads production/dev config (PostgreSQL main database)
```

### For Running Tests
```python
# conftest.py automatically loads:
load_dotenv('.env.test', override=True)  # Test config (PostgreSQL test database)
```

**Precedence (highest to lowest):**
1. `.env.test` (for pytest - PostgreSQL test DB)
2. `.env` (fallback - PostgreSQL main DB)
3. System environment variables
4. Default values in code

**Result:** Tests use isolated `wellbeing_coach_test` database while app uses `wellbeing_coach`

---

## Setup Instructions

### First Time Setup

1. **Create main database** (for development/production)
```bash
PGPASSWORD=password123 createdb -h localhost -U skoust wellbeing_coach
```

2. **Create test database** (for pytest)
```bash
uv run python scripts/create_test_db.py
```

3. **Verify connections**
```bash
# Main database
psql -h localhost -U skoust -d wellbeing_coach

# Test database
psql -h localhost -U skoust -d wellbeing_coach_test
```

4. **Run application**
```bash
uv run python -m run
```

5. **Run tests**
```bash
uv run python -m pytest tests/ -v
```

---

## Environment Variables Reference

### Database
```env
# Option 1: Connection string (recommended)
# Main database
DATABASE_URL=postgresql+psycopg://skoust:password123@localhost:5432/wellbeing_coach

# Test database (in .env.test)
DATABASE_URL=postgresql+psycopg://skoust:password123@localhost:5432/wellbeing_coach_test

# Option 2: Individual variables
DB_USER=skoust
DB_PASSWORD=password123
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wellbeing_coach              # Main database name
# DB_NAME=wellbeing_coach_test       # Test database name (in .env.test)
```

### Logging
```env
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
LOG_FILE=wellbeing_coach.log
DEBUG=True|False
```

### API
```env
API_TITLE=Wellbeing Coach
API_VERSION=1.0.0
RATE_LIMIT_PER_MINUTE=3
HOST=0.0.0.0
PORT=9000
```

### LLM Services
```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:1b
```

### Testing
```env
TEST_WITH_MOCK_DATA=true  # Use mock responses instead of real LLM
```

---

## Common Scenarios

### Setting Up PostgreSQL (First Time)
```bash
# Create main database
createdb wellbeing_coach

# Create test database
uv run python scripts/create_test_db.py

# Verify
psql -l | grep wellbeing_coach
```

### Running Tests Locally
```bash
# Tests automatically use .env.test
uv run python -m pytest tests/unit/services/ -v

# Show coverage
uv run python -m pytest tests/ --cov=app
```

### Local Development with PostgreSQL
```bash
# Edit .env if needed (default should work)
uv run python -m run

# App runs at http://localhost:9000
```

### Debugging Tests
```bash
# Use DEBUG env and verbose output
LOG_LEVEL=DEBUG uv run python -m pytest tests/ -vv -s

# Show print statements
uv run python -m pytest tests/ -s

# Stop on first failure
uv run python -m pytest tests/ -x
```

---

## Security Best Practices

### Do's ✅
- ✅ Add `.env*` to `.gitignore`
- ✅ Use `.env.example` for documentation
- ✅ Store real secrets in system environment
- ✅ Use different passwords for different environments
- ✅ Rotate API keys regularly

### Don'ts ❌
- ❌ Commit `.env` files with real secrets
- ❌ Share `.env` files with teammates
- ❌ Use same password everywhere
- ❌ Hardcode secrets in code
- ❌ Modify `.env.example` with real values

---

## Useful Commands

```bash
# View current configuration
cat .env

# Test database connection
uv run python -c "from sqlalchemy import create_engine; engine = create_engine('sqlite:///./test.db'); print(engine)"

# Run specific test
uv run python -m pytest tests/unit/services/test_emotion_service.py -v

# Run tests with output
uv run python -m pytest tests/ -v -s

# Generate coverage report
uv run python -m pytest tests/ --cov=app --cov-report=html

# List all available tests
uv run python -m pytest --collect-only
```

---

## Troubleshooting

### Tests fail: "Connection refused"
**Problem:** PostgreSQL not running
**Solution:** Start PostgreSQL:
```bash
# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql

# Verify
pg_isready -h localhost
```

### Tests fail: "database 'wellbeing_coach_test' does not exist"
**Problem:** Test database not created
**Solution:**
```bash
uv run python scripts/create_test_db.py
```

### Tests fail: "role 'skoust' does not exist"
**Problem:** PostgreSQL user doesn't exist
**Solution:**
```bash
psql -U postgres -c "CREATE USER skoust WITH PASSWORD 'password123';"
psql -U postgres -c "ALTER USER skoust CREATEDB;"
uv run python scripts/create_test_db.py
```

### App crashes: "Connection to server at localhost:5432 failed"
**Problem:** Main database not created or PostgreSQL not running
**Solution:**
```bash
# Check PostgreSQL
pg_isready -h localhost

# Create database
createdb -h localhost -U skoust wellbeing_coach
```

---

## See Also

- [Environment Setup Guide](ENV_SETUP.md)
- [Testing Guide](SERVICES_TEST_GUIDE.md)
- [pytest Documentation](https://docs.pytest.org/)
- [SQLAlchemy Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
