"""Integration tests for persistent test data.

These tests verify that initial data populates correctly and persists
across test runs. New interactions can be added while maintaining
historical data, mimicking real user behavior.
"""

import pytest
from app.services.memory_service import MemoryService
from app.config.database import SessionLocal
from app.models.interactions import Interaction


class TestPersistentData:
    """Tests for persistent data across test runs."""

    def test_initial_data_exists(self, db_session):
        """Verify initial test data is populated in database."""
        session = SessionLocal()
        interaction_count = session.query(Interaction).count()
        session.close()
        
        # Should have at least the 75 initial interactions
        assert interaction_count >= 75, f"Expected >= 75 interactions, found {interaction_count}"

    def test_initial_data_has_alice(self, db_session):
        """Verify Alice's interactions are in initial data."""
        session = SessionLocal()
        alice_interactions = session.query(Interaction).filter(
            Interaction.user_id == "initial_data_alice"
        ).all()
        session.close()
        
        assert len(alice_interactions) > 0, "No interactions found for alice"
        assert all("alice" in interaction.user_id.lower() for interaction in alice_interactions)

    def test_initial_data_has_bob(self, db_session):
        """Verify Bob's interactions are in initial data."""
        session = SessionLocal()
        bob_interactions = session.query(Interaction).filter(
            Interaction.user_id == "initial_data_bob"
        ).all()
        session.close()
        
        assert len(bob_interactions) > 0, "No interactions found for bob"
        assert all("bob" in interaction.user_id.lower() for interaction in bob_interactions)

    def test_initial_data_has_charlie(self, db_session):
        """Verify Charlie's interactions are in initial data."""
        session = SessionLocal()
        charlie_interactions = session.query(Interaction).filter(
            Interaction.user_id == "initial_data_charlie"
        ).all()
        session.close()
        
        assert len(charlie_interactions) > 0, "No interactions found for charlie"
        assert all("charlie" in interaction.user_id.lower() for interaction in charlie_interactions)

    def test_new_interaction_appends_to_existing_data(self, db_session):
        """Verify new interactions append to existing data without deletion."""
        session = SessionLocal()
        initial_count = session.query(Interaction).count()
        session.close()
        
        service = MemoryService()
        new_interaction_data = {
            "user_id": "new_test_user",
            "user_input": "Testing data persistence",
            "mood": "joy",
            "intensity": 0.8,
            "confidence": 0.9,
            "activity": "Testing",
            "message": "This is a test interaction"
        }
        
        new_id = service.store_interaction(new_interaction_data)
        
        session = SessionLocal()
        final_count = session.query(Interaction).count()
        session.close()
        
        # New count should be exactly one more
        assert final_count == initial_count + 1, \
            f"Expected {initial_count + 1} interactions, found {final_count}"
        assert int(new_id) > 0

    def test_all_moods_exist_in_initial_data(self, db_session):
        """Verify all mood types are represented in initial data."""
        session = SessionLocal()
        moods = set(session.query(Interaction.mood).distinct().all())
        session.close()
        
        mood_values = {mood[0] for mood in moods}
        expected_moods = {"joy", "anxiety", "sadness", "contentment", "stress"}
        
        assert expected_moods.issubset(mood_values), \
            f"Missing moods. Expected {expected_moods}, found {mood_values}"

    def test_all_activities_exist_in_initial_data(self, db_session):
        """Verify all activity types are represented in initial data."""
        session = SessionLocal()
        activities = set(session.query(Interaction.activity).distinct().all())
        session.close()
        
        activity_values = {activity[0] for activity in activities}
        expected_activities = {"Meditation", "Walk", "Yoga", "Journaling", "Deep Breathing"}
        
        assert expected_activities.issubset(activity_values), \
            f"Missing activities. Expected {expected_activities}, found {activity_values}"

    def test_memory_service_reads_persistent_data(self, db_session):
        """Verify MemoryService can read all persistent data."""
        service = MemoryService()
        
        # Get history for initial test users
        alice_history = service.get_history("initial_data_alice")
        bob_history = service.get_history("initial_data_bob")
        charlie_history = service.get_history("initial_data_charlie")
        
        assert len(alice_history) > 0, "MemoryService failed to read Alice's history"
        assert len(bob_history) > 0, "MemoryService failed to read Bob's history"
        assert len(charlie_history) > 0, "MemoryService failed to read Charlie's history"

    def test_interaction_ids_are_sequential(self, db_session):
        """Verify interaction IDs are sequential across all data."""
        session = SessionLocal()
        interactions = session.query(Interaction).order_by(
            Interaction.interaction_id.asc()
        ).all()
        session.close()
        
        assert len(interactions) > 0, "No interactions in database"
        
        # Check that IDs are sequential
        for i, interaction in enumerate(interactions):
            assert interaction.interaction_id == i + 1, \
                f"ID sequence broken at position {i}: expected {i + 1}, got {interaction.interaction_id}"

    def test_timestamps_are_set(self, db_session):
        """Verify all initial interactions have timestamps."""
        session = SessionLocal()
        interactions_without_timestamps = session.query(Interaction).filter(
            Interaction.created_at == None
        ).all()
        session.close()
        
        assert len(interactions_without_timestamps) == 0, \
            f"Found {len(interactions_without_timestamps)} interactions without timestamps"
