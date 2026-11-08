# Quick Start - PostgreSQL Testing Setup

Get testing up and running in 5 minutes.

## Prerequisites

- PostgreSQL running on localhost:5432
- User `skoust` with password `password123`
- Python 3.12+
- uv package manager installed

## Setup (One-time)

### 1. Create PostgreSQL Databases

**Main database:**
```bash
createdb -h localhost -U skoust wellbeing_coach
```

**Test database:**
```bash
uv run python scripts/create_test_db.py
```

### 2. Verify Setup

```bash
# Check main database
psql -h localhost -U skoust -d wellbeing_coach -c "SELECT version();"

# Check test database
psql -h localhost -U skoust -d wellbeing_coach_test -c "SELECT version();"
```

## Running Tests

```bash
# Run service tests
uv run python -m pytest tests/unit/services/ -v

# Run all tests
uv run python -m pytest tests/ -v

# Run with coverage
uv run python -m pytest tests/ --cov=app --cov-report=html

# Run specific test file
uv run python -m pytest tests/unit/services/test_emotion_service.py -v
```

## Running the Application

```bash
uv run python -m run
```

Application runs at `http://localhost:9000`

## Common Issues

### "Connection refused"
```bash
# Start PostgreSQL
brew services start postgresql  # macOS
sudo systemctl start postgresql # Linux
```

### "database wellbeing_coach_test does not exist"
```bash
# Create test database
uv run python scripts/create_test_db.py
```

### "role skoust does not exist"
```bash
# Create user
psql -U postgres -c "CREATE USER skoust WITH PASSWORD 'password123';"
psql -U postgres -c "ALTER USER skoust CREATEDB;"

# Then create databases
createdb -h localhost -U skoust wellbeing_coach
uv run python scripts/create_test_db.py
```

## Environment Files

| File | Used For | Database |
|------|----------|----------|
| `.env` | Running app | `wellbeing_coach` |
| `.env.test` | Running tests | `wellbeing_coach_test` |
| `.env.example` | Reference | N/A |
| `.env.local` | Local dev (SQLite) | `wellbeing_coach_dev.db` |

## More Information

- [Full Setup Guide](ENV_SETUP.md)
- [Configuration Reference](ENV_CONFIG_REFERENCE.md)
- [Script Help](scripts/README.md)
- [Testing Guide](SERVICES_TEST_GUIDE.md)

---

## Database Schema

Tests automatically create tables in the test database. Schema is defined in `app/config.py` under the `Interaction` model.

Main table: `interactions`
- `interaction_id` (Integer, Primary Key)
- `user_id` (String)
- `user_input` (Text)
- `mood` (String)
- `intensity` (Float)
- `confidence` (Float)
- `activity` (Text)
- `message` (Text)
- `rating` (Integer, Optional)
- `feedback` (Text, Optional)
- `comment` (Text, Optional)
- `created_at` (DateTime)

---

That's it! You're ready to develop and test. 🚀
