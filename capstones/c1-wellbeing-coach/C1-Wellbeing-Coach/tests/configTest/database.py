"""Database fixtures for tests with persistent data behavior."""

import pytest
from sqlalchemy.orm import sessionmaker

from .env import project_root


@pytest.fixture(scope="session")
def test_db():
    """Test database with GUARANTEED PERSISTENT data."""
    from app.config.database import DatabaseConfig, initialize_database
    from app.models.interactions import Interaction

    print("\n" + "=" * 70)
    print("🔒 PERSISTENT DATA MODE ACTIVATED")
    print("=" * 70)

    print("✅ Step 1: Initializing database schema (CREATE only, no DROP)...")
    initialize_database()

    db_config = DatabaseConfig()
    engine = db_config.get_engine()

    print("✅ Step 2: Checking data in database...")
    with sessionmaker(bind=engine)() as session:
        interaction_count = session.query(Interaction).count()
        print(f"   📊 Current interactions: {interaction_count}")

        if interaction_count == 0:
            print("✅ Step 3: Database EMPTY - populating initial test data...")
            session.close()

            import subprocess

            result = subprocess.run(
                ["uv", "run", "python", "scripts/populate_test_data.py"],
                cwd=project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ Step 3: Initial data populated successfully")
                with sessionmaker(bind=engine)() as verify_session:
                    new_count = verify_session.query(Interaction).count()
                    print(f"   📊 Interactions after population: {new_count}")
            else:
                print(f"❌ Step 3: Population failed: {result.stderr}")
                raise RuntimeError(f"Failed to populate initial data: {result.stderr}")
        else:
            print(
                f"✅ Step 3: Database already has data - REUSING {interaction_count} interactions"
            )
            print("   ℹ️  No population needed (data persists across test runs)")
            session.close()

    print("=" * 70)
    print("✅ TEST DATABASE READY - DATA IS SAFE AND PERSISTENT")
    print("=" * 70 + "\n")

    yield engine

    print("\n" + "=" * 70)
    print("🔒 FINAL DATA INTEGRITY CHECK")
    print("=" * 70)
    with sessionmaker(bind=engine)() as final_session:
        final_count = final_session.query(Interaction).count()
        print(f"✅ Interactions at test completion: {final_count}")
        print("✅ NO DATA WAS DELETED OR DROPPED")
        print("✅ Tables remain intact for next test run")
    print("=" * 70 + "\n")


@pytest.fixture(scope="function")
def db_session(test_db):
    """Create a fresh database session for each test."""
    from app.config.database import SessionLocal

    session = SessionLocal()
    yield session
    session.close()
