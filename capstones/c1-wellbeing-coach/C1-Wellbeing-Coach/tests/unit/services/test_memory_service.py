"""Unit tests for MemoryService - database operations."""

import pytest
from app.services.memory_service import MemoryService
from app.config.database import SessionLocal


class TestMemoryService:
    """Tests for MemoryService - database interaction storage and retrieval."""

    def test_store_interaction(self, sample_interaction_data, db_session):
        """Test storing an interaction."""
        service = MemoryService()
        # Use unique user ID for this test run (persistent data accumulates)
        sample_interaction_data["user_id"] = "test_store_interaction_user"
        interaction_id = service.store_interaction(sample_interaction_data)
        
        assert interaction_id is not None
        assert int(interaction_id) > 0  # Valid ID assigned
        
        # Verify it's in database
        history = service.get_history(sample_interaction_data["user_id"])
        assert len(history) >= 1  # At least our interaction
        assert history[0]["user_input"] == sample_interaction_data["user_input"]

    def test_store_multiple_interactions(self, sample_interaction_data, db_session):
        """Test storing multiple interactions for same user."""
        service = MemoryService()
        
        # Use unique user ID for this test run (persistent data accumulates)
        sample_interaction_data["user_id"] = "test_multiple_user"
        
        # Store first interaction
        id1 = service.store_interaction(sample_interaction_data)
        
        # Store second interaction
        data2 = sample_interaction_data.copy()
        data2["user_input"] = "I feel better now"
        id2 = service.store_interaction(data2)
        
        # Verify both stored
        history = service.get_history(sample_interaction_data["user_id"])
        assert len(history) >= 2  # At least our two interactions
        # Find our interactions by user_id
        our_interactions = [h for h in history if h["user_id"] == sample_interaction_data["user_id"]]
        assert len(our_interactions) >= 2
        assert int(id2) > int(id1)  # Second ID should be greater

    def test_get_history_empty(self, db_session):
        """Test getting history for user with no interactions."""
        service = MemoryService()
        history = service.get_history("non_existent_user")
        
        assert history == []

    def test_get_history_multiple_users(self, sample_interaction_data, db_session):
        """Test that history is separate per user."""
        service = MemoryService()
        
        # Use unique test user IDs (persistent data accumulates)
        user1_id = "test_multiple_users_user1"
        user2_id = "test_multiple_users_user2"
        
        # Store interaction for user1
        sample_interaction_data["user_id"] = user1_id
        id1 = service.store_interaction(sample_interaction_data)
        
        # Store interaction for user2
        data2 = sample_interaction_data.copy()
        data2["user_id"] = user2_id
        id2 = service.store_interaction(data2)
        
        # Verify separation
        history1 = service.get_history(user1_id)
        history2 = service.get_history(user2_id)
        
        assert len(history1) >= 1  # At least our interaction
        assert len(history2) >= 1  # At least our interaction
        # Verify our users are present
        assert any(h["user_id"] == user1_id for h in history1)
        assert any(h["user_id"] == user2_id for h in history2)

    def test_update_feedback_with_rating(self, sample_interaction_data, db_session):
        """Test updating feedback with rating only."""
        service = MemoryService()
        interaction_id = service.store_interaction(sample_interaction_data)
        
        # Update with rating
        service.update_feedback(interaction_id, rating=5)
        
        # Verify update
        history = service.get_history(sample_interaction_data["user_id"])
        assert history[0]["rating"] == 5
        assert history[0]["comment"] is None

    def test_update_feedback_with_comment(self, sample_interaction_data, db_session):
        """Test updating feedback with comment only."""
        service = MemoryService()
        interaction_id = service.store_interaction(sample_interaction_data)
        
        # Update with comment
        service.update_feedback(interaction_id, comment="Very helpful!")
        
        # Verify update
        history = service.get_history(sample_interaction_data["user_id"])
        assert history[0]["rating"] is None
        assert history[0]["comment"] == "Very helpful!"

    def test_update_feedback_with_both(self, sample_interaction_data, db_session):
        """Test updating feedback with both rating and comment."""
        service = MemoryService()
        interaction_id = service.store_interaction(sample_interaction_data)
        
        # Update with both
        service.update_feedback(interaction_id, rating=4, comment="Good interaction")
        
        # Verify update
        history = service.get_history(sample_interaction_data["user_id"])
        assert history[0]["rating"] == 4
        assert history[0]["comment"] == "Good interaction"

    def test_update_feedback_invalid_rating(self, sample_interaction_data, db_session):
        """Test that invalid rating raises error."""
        service = MemoryService()
        interaction_id = service.store_interaction(sample_interaction_data)
        
        # Try to update with invalid rating
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            service.update_feedback(interaction_id, rating=10)

    def test_update_feedback_nonexistent_interaction(self, db_session):
        """Test updating feedback for non-existent interaction."""
        service = MemoryService()
        
        # Try to update non-existent interaction
        with pytest.raises(ValueError, match="Interaction .* not found"):
            service.update_feedback("9999", rating=5)

    def test_update_feedback_no_fields(self, sample_interaction_data, db_session):
        """Test that updating with no fields raises error."""
        service = MemoryService()
        interaction_id = service.store_interaction(sample_interaction_data)
        
        # Try to update with no fields
        with pytest.raises(ValueError, match="At least one feedback field must be provided"):
            service.update_feedback(interaction_id)

    def test_has_feedback_with_rating(self, sample_interaction_data, db_session):
        """Test checking if interaction has feedback."""
        service = MemoryService()
        interaction_id = service.store_interaction(sample_interaction_data)
        
        # No feedback initially
        assert service.has_feedback(interaction_id) is False
        
        # After adding rating
        service.update_feedback(interaction_id, rating=5)
        assert service.has_feedback(interaction_id) is True

    def test_has_feedback_nonexistent_interaction(self, db_session):
        """Test has_feedback for non-existent interaction."""
        service = MemoryService()
        
        # Should return False for non-existent
        assert service.has_feedback("9999") is False
