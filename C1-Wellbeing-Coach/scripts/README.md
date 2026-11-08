# Setup Scripts

Utility scripts for configuring the Wellbeing Coach environment.

## create_test_db.py

Python script to create the PostgreSQL test database.

**Usage:**
```bash
uv run python scripts/create_test_db.py
```

**What it does:**
1. ✅ Connects to PostgreSQL using credentials from `.env.test`
2. ✅ Creates `wellbeing_coach_test` database if it doesn't exist
3. ✅ Grants privileges to the configured user
4. ✅ Shows connection details

**Requirements:**
- PostgreSQL running on localhost:5432
- User `skoust` with password `password123` (or configured in `.env.test`)

**Output:**
```
🗄️  Creating test database...
==================================================
Host: localhost:5432
User: skoust
Test Database: wellbeing_coach_test
==================================================

✓ PostgreSQL is running
✓ Test database created successfully!

Next steps:
1. Run tests: uv run python -m pytest tests/unit/services/ -v
2. Or: uv run python -m pytest tests/ -v
```

**Troubleshooting:**

If PostgreSQL is not running:
```bash
# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql
```

If user doesn't exist:
```bash
psql -U postgres -c "CREATE USER skoust WITH PASSWORD 'password123';"
psql -U postgres -c "ALTER USER skoust CREATEDB;"
```

---

## create_test_db.sh

Bash script alternative to Python version (macOS/Linux only).

**Usage:**
```bash
bash scripts/create_test_db.sh
```

**Same functionality as Python version** but uses bash.

**Note:** Not available on Windows. Use `create_test_db.py` instead.

---

## Quick Start

### First Time Setup
```bash
# 1. Create main database (once)
createdb -h localhost -U skoust wellbeing_coach

# 2. Create test database
uv run python scripts/create_test_db.py

# 3. Run tests
uv run python -m pytest tests/ -v
```

### Running Tests
```bash
# Tests automatically use .env.test
uv run python -m pytest tests/unit/services/ -v
```

### Cleanup

Drop test database when no longer needed:
```bash
PGPASSWORD=password123 dropdb -h localhost -U skoust wellbeing_coach_test
```

---

## Files in this directory

- `create_test_db.py` - Python script to create test database
- `create_test_db.sh` - Bash script to create test database (macOS/Linux)
- `README.md` - This file

---

See Also:
- [ENV_SETUP.md](../ENV_SETUP.md) - Full environment setup guide
- [ENV_CONFIG_REFERENCE.md](../ENV_CONFIG_REFERENCE.md) - Configuration reference
