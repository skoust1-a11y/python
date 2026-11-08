"""Integration tests for feedback routes."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestFeedbackRoutes:
    """Tests for feedback API endpoints."""

    def test_get_feedback_status(self, client: TestClient):
        """Test GET /feedback/ endpoint."""
        response = client.get("/feedback/")
        
        assert response.status_code == 200
        assert response.json()["status"] == "Feedback endpoint"

    def test_submit_feedback_with_rating_only(self, client: TestClient):
        """Test submitting feedback with only rating."""
        # First create an interaction
        interaction_response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel happy", "user_id": "test_user"}
        )
        interaction_id = interaction_response.json()["interaction_id"]
        
        # Submit feedback with rating only
        response = client.post(
            "/feedback/store",
            json={"interaction_id": interaction_id, "rating": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Feedback submitted successfully"
        assert data["rating"] == 5
        assert data["comment_received"] is False

    def test_submit_feedback_with_comment_only(self, client: TestClient):
        """Test submitting feedback with only comment."""
        # First create an interaction
        interaction_response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel anxious", "user_id": "test_user"}
        )
        interaction_id = interaction_response.json()["interaction_id"]
        
        # Submit feedback with comment only
        response = client.post(
            "/feedback/store",
            json={"interaction_id": interaction_id, "comment": "Very helpful!"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Feedback submitted successfully"
        assert data["rating"] is None
        assert data["comment_received"] is True

    def test_submit_feedback_with_both(self, client: TestClient):
        """Test submitting feedback with both rating and comment."""
        # First create an interaction
        interaction_response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel neutral", "user_id": "test_user"}
        )
        interaction_id = interaction_response.json()["interaction_id"]
        
        # Submit feedback with both
        response = client.post(
            "/feedback/store",
            json={
                "interaction_id": interaction_id,
                "rating": 4,
                "comment": "Good experience"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Feedback submitted successfully"
        assert data["rating"] == 4
        assert data["comment_received"] is True

    def test_submit_feedback_with_neither(self, client: TestClient):
        """Test submitting feedback with neither rating nor comment (should fail)."""
        # First create an interaction
        interaction_response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel stressed", "user_id": "test_user"}
        )
        interaction_id = interaction_response.json()["interaction_id"]
        
        # Try to submit feedback with neither
        response = client.post(
            "/feedback/store",
            json={"interaction_id": interaction_id}
        )
        
        assert response.status_code == 400
        assert "At least a rating, feedback, or comment must be provided" in response.json()["detail"]

    def test_submit_feedback_invalid_rating_too_high(self, client: TestClient):
        """Test that rating > 5 is rejected."""
        # First create an interaction
        interaction_response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel happy", "user_id": "test_user"}
        )
        interaction_id = interaction_response.json()["interaction_id"]
        
        # Try to submit with invalid rating
        response = client.post(
            "/feedback/store",
            json={"interaction_id": interaction_id, "rating": 10}
        )
        
        assert response.status_code == 400
        assert "Rating must be an integer between 1 and 5" in response.json()["detail"]

    def test_submit_feedback_invalid_rating_too_low(self, client: TestClient):
        """Test that rating < 1 is rejected."""
        # First create an interaction
        interaction_response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel happy", "user_id": "test_user"}
        )
        interaction_id = interaction_response.json()["interaction_id"]
        
        # Try to submit with invalid rating
        response = client.post(
            "/feedback/store",
            json={"interaction_id": interaction_id, "rating": 0}
        )
        
        assert response.status_code == 400
        assert "Rating must be an integer between 1 and 5" in response.json()["detail"]

    def test_submit_feedback_comment_too_long(self, client: TestClient):
        """Test that comment > 500 chars is rejected."""
        # First create an interaction
        interaction_response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel happy", "user_id": "test_user"}
        )
        interaction_id = interaction_response.json()["interaction_id"]
        
        # Try to submit with very long comment
        long_comment = "a" * 501
        response = client.post(
            "/feedback/store",
            json={"interaction_id": interaction_id, "comment": long_comment}
        )
        
        assert response.status_code == 400
        assert "Comment must be 500 characters or less" in response.json()["detail"]

    def test_submit_feedback_nonexistent_interaction(self, client: TestClient):
        """Test submitting feedback for non-existent interaction."""
        response = client.post(
            "/feedback/store",
            json={"interaction_id": "9999", "rating": 5}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_submit_feedback_persists_in_history(self, client: TestClient):
        """Test that submitted feedback appears in user history."""
        # Create interaction and feedback
        interaction_response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel great", "user_id": "test_persist_user"}
        )
        interaction_id = interaction_response.json()["interaction_id"]
        
        feedback_response = client.post(
            "/feedback/store",
            json={
                "interaction_id": interaction_id,
                "rating": 5,
                "comment": "Perfect!"
            }
        )
        assert feedback_response.status_code == 200
        
        # Check in history
        history_response = client.get("/wellbeing/history/test_persist_user")
        history = history_response.json()["history"]
        
        assert len(history) > 0
        latest = history[0]
        assert latest["rating"] == 5
        assert latest["comment"] == "Perfect!"

    def test_submit_feedback_text_persists_in_history(self, client: TestClient):
        """Test that feedback text is stored in DB feedback field."""
        interaction_response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel supported", "user_id": "test_feedback_text_user"}
        )
        interaction_id = interaction_response.json()["interaction_id"]

        feedback_response = client.post(
            "/feedback/store",
            json={
                "interaction_id": interaction_id,
                "feedback": "The recommendation quality was good"
            }
        )
        assert feedback_response.status_code == 200

        history_response = client.get("/wellbeing/history/test_feedback_text_user")
        history = history_response.json()["history"]

        assert len(history) > 0
        latest = history[0]
        assert latest["feedback"] == "The recommendation quality was good"

    def test_update_feedback_multiple_times(self, client: TestClient):
        """Test that feedback can be updated multiple times."""
        # Create interaction
        interaction_response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel okay", "user_id": "test_update_user"}
        )
        interaction_id = interaction_response.json()["interaction_id"]
        
        # First feedback submission
        response1 = client.post(
            "/feedback/store",
            json={"interaction_id": interaction_id, "rating": 3}
        )
        assert response1.status_code == 200
        
        # Second feedback submission (update)
        response2 = client.post(
            "/feedback/store",
            json={"interaction_id": interaction_id, "rating": 5, "comment": "Changed my mind!"}
        )
        assert response2.status_code == 200
        
        # Verify latest in history
        history_response = client.get("/wellbeing/history/test_update_user")
        history = history_response.json()["history"]
        latest = history[0]
        
        # Should have the last update
        assert latest["rating"] == 5
        assert latest["comment"] == "Changed my mind!"
