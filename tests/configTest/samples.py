"""Sample payload fixtures for tests."""

import pytest


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
        "message": "Try meditation for 10 minutes",
    }


@pytest.fixture
def sample_feedback_data():
    """Sample feedback data for testing."""
    return {
        "interaction_id": "1",
        "rating": 5,
        "comment": "This was very helpful!",
    }
