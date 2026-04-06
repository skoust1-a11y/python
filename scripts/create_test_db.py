#!/usr/bin/env python3
"""
Create PostgreSQL test database for Wellbeing Coach.
Run this before running tests for the first time.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_test_database():
    """Create PostgreSQL test database if it doesn't exist."""
    
    # Load test environment
    load_dotenv(project_root / ".env.test", override=True)
    
    db_user = os.getenv("DB_USER", "skoust")
    db_password = os.getenv("DB_PASSWORD", "password123")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "wellbeing_coach")
    test_db_name = f"{db_name}_test"
    
    print("🗄️  Creating test database...")
    print("=" * 50)
    print(f"Host: {db_host}:{db_port}")
    print(f"User: {db_user}")
    print(f"Test Database: {test_db_name}")
    print("=" * 50)
    print()
    
    try:
        import psycopg
        
        # Connect to default postgres database
        print("Connecting to PostgreSQL...")
        conn = psycopg.connect(
            host=db_host,
            port=int(db_port),
            user=db_user,
            password=db_password,
            dbname="postgres",
            autocommit=True  # Enable autocommit for CREATE DATABASE
        )
        
        print("✓ Connected to PostgreSQL")
        
        # Get cursor
        cur = conn.cursor()
        
        # Check if test database exists
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (test_db_name,)
        )
        
        if cur.fetchone():
            print(f"✓ Test database '{test_db_name}' already exists")
        else:
            print(f"Creating test database '{test_db_name}'...")
            cur.execute(f"CREATE DATABASE {test_db_name}")
            print(f"✓ Test database '{test_db_name}' created successfully")
        
        # Grant privileges
        cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {test_db_name} TO {db_user}")
        print(f"✓ Granted privileges to {db_user}")
        
        cur.close()
        conn.close()
        
        print()
        print("=" * 50)
        print("✅ Test database setup complete!")
        print("=" * 50)
        print()
        print("Next steps:")
        print("1. Run tests:")
        print("   uv run python -m pytest tests/unit/services/ -v")
        print()
        print("2. Or run all tests:")
        print("   uv run python -m pytest tests/ -v")
        print()
        print("To drop the test database later:")
        print(f"  dropdb -h {db_host} -U {db_user} {test_db_name}")
        print()
        
        return True
        
    except ModuleNotFoundError:
        print("❌ ERROR: psycopg not installed")
        print("Install it with: uv add psycopg2-binary")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        print("Troubleshooting:")
        print(f"1. Check PostgreSQL is running: pg_isready -h {db_host}")
        print(f"2. Verify credentials in .env or .env.test")
        print(f"3. Try connecting manually:")
        print(f"   psql -h {db_host} -U {db_user} -d postgres")
        return False


if __name__ == "__main__":
    success = create_test_database()
    sys.exit(0 if success else 1)
