"""Integration tests for wellbeing routes."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestWellbeingRoutes:
    """Tests for wellbeing API endpoints."""

    def test_analyze_emotion_success(self, client: TestClient):
        """Test successful emotion analysis."""
        response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel very happy today!", "user_id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "interaction_id" in data
        assert "emotion" in data
        assert "confidence" in data
        assert "message" in data
        assert "recommendations" in data

    def test_analyze_emotion_missing_text(self, client: TestClient):
        """Test emotion analysis with missing text."""
        response = client.post(
            "/wellbeing/analyze",
            json={"user_id": "test_user"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity

    def test_analyze_emotion_missing_user_id(self, client: TestClient):
        """Test emotion analysis with missing user_id."""
        response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel happy"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity

    def test_analyze_emotion_gibberish_returns_custom_error(self, client: TestClient):
        response = client.post(
            "/wellbeing/analyze",
            json={"text": "@@@ 1234 !!! z", "user_id": "gibberish_user"}
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Unable to detect emotion from the input. Please enter a clear feeling or sentence."

    def test_analyze_emotion_returns_interaction_id(self, client: TestClient):
        """Test that emotion analysis returns valid interaction_id."""
        response = client.post(
            "/wellbeing/analyze",
            json={"text": "Feeling stressed", "user_id": "test_user_1"}
        )
        
        data = response.json()
        interaction_id = data["interaction_id"]
        
        # interaction_id should be a string representation of an integer
        assert interaction_id.isdigit()

    def test_analyze_emotion_creates_entry_in_history(self, client: TestClient):
        """Test that emotion analysis creates database entry."""
        # Analyze emotion
        response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel anxious", "user_id": "test_user_2"}
        )
        assert response.status_code == 200
        interaction_id = response.json()["interaction_id"]
        
        # Check in history
        history_response = client.get("/wellbeing/history/test_user_2")
        assert history_response.status_code == 200
        
        history = history_response.json()["history"]
        assert len(history) > 0
        
        found = False
        for entry in history:
            if str(entry["interaction_id"]) == interaction_id:
                found = True
                break
        assert found is True

    def test_get_history_empty(self, client: TestClient):
        """Test getting history for user with no interactions."""
        response = client.get("/wellbeing/history/nonexistent_user")
        
        assert response.status_code == 200
        data = response.json()
        assert data["history"] == []

    def test_get_history_multiple_interactions(self, client: TestClient):
        """Test getting history with multiple interactions."""
        # Use test-specific user ID to keep data isolated per test run
        user_id = "test_get_history_multiple_interactions"
        
        # Get initial count
        response_before = client.get(f"/wellbeing/history/{user_id}")
        initial_count = len(response_before.json()["history"]) if response_before.status_code == 200 else 0
        
        # Create multiple interactions
        for i in range(3):
            client.post(
                "/wellbeing/analyze",
                json={"text": f"Feeling {i}", "user_id": user_id}
            )
        
        # Get history
        response = client.get(f"/wellbeing/history/{user_id}")
        
        assert response.status_code == 200
        history = response.json()["history"]
        # History endpoint is capped at 50 entries
        expected_count = min(50, initial_count + 3)
        assert len(history) >= expected_count

    def test_get_history_order_most_recent_first(self, client: TestClient):
        """Test that history returns most recent interactions first."""
        # Use test-specific user ID to keep data isolated per test run
        user_id = "test_get_history_order_most_recent_first"
        
        # Create interactions with different texts
        texts = ["First", "Second", "Third"]
        for text in texts:
            client.post(
                "/wellbeing/analyze",
                json={"text": text, "user_id": user_id}
            )
        
        # Get history
        response = client.get(f"/wellbeing/history/{user_id}")
        history = response.json()["history"]
        
        # Most recent should be "Third"
        assert history[0]["user_input"] == "Third"
        assert history[1]["user_input"] == "Second"
        assert history[2]["user_input"] == "First"

    def test_get_history_limit_50(self, client: TestClient):
        """Test that history is limited to 50 entries."""
        # Use test-specific user ID to keep data isolated per test run
        user_id = "test_get_history_limit_50"
        
        # Create 55 interactions
        for i in range(55):
            client.post(
                "/wellbeing/analyze",
                json={"text": f"Interaction {i}", "user_id": user_id}
            )
        
        # Get history
        response = client.get(f"/wellbeing/history/{user_id}")
        history = response.json()["history"]
        
        # Should be limited to 50
        assert len(history) == 50

    def test_analyze_emotion_response_structure(self, client: TestClient):
        """Test the response structure of emotion analysis."""
        response = client.post(
            "/wellbeing/analyze",
            json={"text": "I feel great", "user_id": "test_structure_user"}
        )
        
        data = response.json()
        
        # Check required fields
        assert "interaction_id" in data
        assert "emotion" in data
        assert "confidence" in data
        assert "message" in data
        assert "recommendations" in data
        
        # Check recommendations structure
        recommendations = data["recommendations"]
        assert "activity" in recommendations
        assert "message" in recommendations

    def test_analyze_emotion_different_users_separate_history(self, client: TestClient):
        """Test that different users have separate histories."""
        # Use test-specific user IDs to keep data isolated per test run
        user1 = "test_analyze_emotion_different_users_separate_history_user1"
        user2 = "test_analyze_emotion_different_users_separate_history_user2"
        
        # Get initial counts
        response1_before = client.get(f"/wellbeing/history/{user1}")
        count1_before = len(response1_before.json()["history"]) if response1_before.status_code == 200 else 0
        
        response2_before = client.get(f"/wellbeing/history/{user2}")
        count2_before = len(response2_before.json()["history"]) if response2_before.status_code == 200 else 0
        
        # Create interaction for user1
        client.post(
            "/wellbeing/analyze",
            json={"text": "User 1 feeling happy", "user_id": user1}
        )
        
        # Create interaction for user2
        client.post(
            "/wellbeing/analyze",
            json={"text": "User 2 feeling sad", "user_id": user2}
        )
        
        # Check histories are separate and incremented
        history1 = client.get(f"/wellbeing/history/{user1}").json()["history"]
        history2 = client.get(f"/wellbeing/history/{user2}").json()["history"]
        
        # Each should have at least 1 more interaction
        assert len(history1) >= count1_before + 1
        assert len(history2) >= count2_before + 1
        # Verify the users match
        assert all(h["user_id"] == user1 for h in history1)
        assert all(h["user_id"] == user2 for h in history2)

    def test_analyze_emotion_stores_all_fields(self, client: TestClient):
        """Test that emotion analysis stores all relevant fields."""
        response = client.post(
            "/wellbeing/analyze",
            json={"text": "I am feeling overwhelmed", "user_id": "test_fields_user"}
        )
        
        interaction_id = response.json()["interaction_id"]
        
        # Check in history
        history_response = client.get("/wellbeing/history/test_fields_user")
        interaction = history_response.json()["history"][0]
        
        assert interaction["user_id"] == "test_fields_user"
        assert interaction["user_input"] == "I am feeling overwhelmed"
        assert "mood" in interaction
        assert "intensity" in interaction
        assert "confidence" in interaction
        assert "activity" in interaction
        assert "message" in interaction
        assert "created_at" in interaction
