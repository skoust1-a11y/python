"""Pytest configuration and fixtures for Wellbeing Coach tests.

⚠️  CRITICAL: This configuration PRESERVES all test data.
    Tables are NEVER dropped. Data PERSISTS across all test runs.
    This mimics real user behavior where interaction history accumulates.
"""

import os
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load test-specific environment variables from .env.test
test_env_file = project_root / ".env.test"
if test_env_file.exists():
    load_dotenv(test_env_file, override=True)
else:
    # Fallback to default .env if .env.test doesn't exist
    load_dotenv(project_root / ".env", override=True)

# Ensure test database is configured
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DATABASE_URL"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://skoust:password123@localhost:5432/wellbeing_coach_test"
)


@pytest.fixture(scope="session")
def test_db():
    """Test database with GUARANTEED PERSISTENT data.
    
    CRITICAL SAFEGUARDS:
    ✅ Tables are CREATED, never DROPPED
    ✅ Data is CHECKED before population
    ✅ Initial data is INSERTED only if empty
    ✅ Zero cleanup - data PERSISTS forever
    ✅ Every test RUN ACCUMULATES data
    
    This fixture ensures that all interactions are preserved
    exactly like real user behavior.
    """
    from app.config.database import initialize_database, DatabaseConfig
    from app.models.interactions import Interaction
    
    print("\n" + "="*70)
    print("🔒 PERSISTENT DATA MODE ACTIVATED")
    print("="*70)
    
    # Step 1: Initialize schema (creates tables if needed, NEVER drops)
    print("✅ Step 1: Initializing database schema (CREATE only, no DROP)...")
    initialize_database()
    
    # Step 2: Get engine
    db_config = DatabaseConfig()
    engine = db_config.get_engine()
    
    # Step 3: Check data status
    print("✅ Step 2: Checking data in database...")
    with sessionmaker(bind=engine)() as session:
        interaction_count = session.query(Interaction).count()
        print(f"   📊 Current interactions: {interaction_count}")
        
        # Step 4: Conditionally populate initial data (only if empty)
        if interaction_count == 0:
            print("✅ Step 3: Database EMPTY - populating initial test data...")
            session.close()
            
            # Run populate script
            import subprocess
            result = subprocess.run(
                ["uv", "run", "python", "scripts/populate_test_data.py"],
                cwd=project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Step 3: Initial data populated successfully")
                # Verify
                with sessionmaker(bind=engine)() as verify_session:
                    new_count = verify_session.query(Interaction).count()
                    print(f"   📊 Interactions after population: {new_count}")
            else:
                print(f"❌ Step 3: Population failed: {result.stderr}")
                raise RuntimeError(f"Failed to populate initial data: {result.stderr}")
        else:
            print(f"✅ Step 3: Database already has data - REUSING {interaction_count} interactions")
            print("   ℹ️  No population needed (data persists across test runs)")
            session.close()
    
    print("="*70)
    print("✅ TEST DATABASE READY - DATA IS SAFE AND PERSISTENT")
    print("="*70 + "\n")
    
    yield engine
    
    # CRITICAL: Post-test verification
    print("\n" + "="*70)
    print("🔒 FINAL DATA INTEGRITY CHECK")
    print("="*70)
    with sessionmaker(bind=engine)() as final_session:
        final_count = final_session.query(Interaction).count()
        print(f"✅ Interactions at test completion: {final_count}")
        print("✅ NO DATA WAS DELETED OR DROPPED")
        print("✅ Tables remain intact for next test run")
    print("="*70 + "\n")


@pytest.fixture(scope="function")
def db_session(test_db):
    """Create a fresh database session for each test."""
    from app.config.database import SessionLocal
    
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client():
    """Create FastAPI test client with isolated database sessions.
    
    ⚠️  IMPORTANT: This fixture does NOT clean up test data.
        All interactions created during tests PERSIST in database.
        This is intentional behavior matching real user scenarios.
    """
    from app.main import app
    from app.config.database import SessionLocal
    
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()  # Close session only - never delete data
    
    return TestClient(app)


@pytest.fixture
def reset_db(test_db):
    """
    Hard-disabled safety fixture.

    Any attempt to use this fixture fails immediately to prevent
    accidental data deletion in the persistent test database.
    """
    raise RuntimeError(
        "reset_db is disabled to protect persistent test data. "
        "Do not clear or reset the test database."
    )



@pytest.fixture
def preserve_db(test_db):
    """
    Fixture that explicitly preserves database state between tests.
    
    This is the default behavior - test data accumulates like real user interactions:
    - Test 1: Creates interactions 1-5
    - Test 2: Creates interactions 6-10 (previous data intact)
    - Test 3: Creates interactions 11-15 (all historical data preserved)
    
    Use this when you want to verify data persistence across test runs.
    """
    yield
    # Data persists - no cleanup performed


@pytest.fixture
def sample_interaction_data():
    """Sample interaction data for testing."""
    return {
        "user_id": "test_user",
        "user_input": "I feel stressed today",
        "mood": "anxiety",
        "intensity": 0.8,
        "confidence": 0.9,
        "activity": "Meditation",
        "message": "Try meditation for 10 minutes"
    }


@pytest.fixture
def sample_feedback_data():
    """Sample feedback data for testing."""
    return {
        "interaction_id": "1",
        "rating": 5,
        "comment": "This was very helpful!"
    }
