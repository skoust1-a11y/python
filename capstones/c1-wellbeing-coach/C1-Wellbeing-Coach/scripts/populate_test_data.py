#!/usr/bin/env python3
"""
Populate test database with sample interactions.

This script adds initial test data to the wellbeing_coach_test database.
Tests will read and verify this persistent data without resetting it.

Usage:
    uv run python scripts/populate_test_data.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load test environment
load_dotenv(project_root / ".env.test", override=True)

from sqlalchemy import create_engine, text
from app.config.database import SessionLocal
from app.models.interactions import Interaction


def populate_test_data():
    """Add sample interactions to test database."""
    
    session = SessionLocal()
    
    try:
        # Initialize database tables if they don't exist
        from app.config.database import initialize_database
        initialize_database()
        print("✅ Database tables initialized")
        
        # Sample users
        users = ["alice", "bob", "charlie"]
        moods = ["joy", "anxiety", "sadness", "contentment", "stress"]
        activities = ["Meditation", "Walk", "Yoga", "Journaling", "Deep Breathing"]
        
        print("🌱 Populating test database with sample interactions...")
        
        interactions_added = 0
        base_time = datetime.now()
        
        for day in range(500):  # 500 days worth of data
            for user_idx, user in enumerate(users):
                for mood_idx, mood in enumerate(moods):
                    # Create timestamp for each interaction
                    created_at = base_time - timedelta(days=500-day, hours=user_idx*8 + mood_idx*2)
                    
                    interaction = Interaction(
                        user_id=f"initial_data_{user}",
                        user_input=f"{user.capitalize()} says: I'm feeling {mood} today",
                        mood=mood,
                        intensity=0.5 + (mood_idx * 0.1),
                        confidence=0.8 + (user_idx * 0.05),
                        activity=activities[mood_idx % len(activities)],
                        message=f"Recommendation: Try {activities[mood_idx % len(activities)].lower()} to help with {mood}",
                        created_at=created_at
                    )
                    session.add(interaction)
                    interactions_added += 1
        
        session.commit()
        print(f"✅ Successfully added {interactions_added} initial interactions to test database!")
        
        # Display summary
        count = session.query(Interaction).count()
        print(f"\n📊 Total interactions in database: {count}")
        
        # Show sample data
        print("\n📋 Sample data added:")
        samples = session.query(Interaction).order_by(Interaction.interaction_id.desc()).limit(5).all()
        for sample in reversed(samples):
            print(f"  - {sample.user_id}: {sample.user_input[:50]}... (ID: {sample.interaction_id})")
        
    except Exception as e:
        print(f"❌ Error populating test data: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    populate_test_data()
