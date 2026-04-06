"""Unit tests for data models."""

import pytest
from app.models.feedback import Feedback


class TestFeedbackModel:
    """Tests for Feedback Pydantic model."""

    def test_feedback_with_rating_only(self):
        """Test creating feedback with only rating (no comment)."""
        feedback = Feedback(interaction_id="1", rating=5)
        assert feedback.interaction_id == "1"
        assert feedback.rating == 5
        assert feedback.comment is None

    def test_feedback_with_comment_only(self):
        """Test creating feedback with only comment (no rating)."""
        feedback = Feedback(interaction_id="1", comment="Great interaction!")
        assert feedback.interaction_id == "1"
        assert feedback.rating is None
        assert feedback.comment == "Great interaction!"

    def test_feedback_with_both_rating_and_comment(self):
        """Test creating feedback with both rating and comment."""
        feedback = Feedback(
            interaction_id="1",
            rating=4,
            comment="Very helpful"
        )
        assert feedback.interaction_id == "1"
        assert feedback.rating == 4
        assert feedback.comment == "Very helpful"

    def test_feedback_with_neither_rating_nor_comment(self):
        """Test creating feedback with neither rating nor comment (should work in model)."""
        feedback = Feedback(interaction_id="1")
        assert feedback.interaction_id == "1"
        assert feedback.rating is None
        assert feedback.comment is None

    def test_feedback_missing_interaction_id(self):
        """Test that interaction_id is required."""
        with pytest.raises(ValueError):
            Feedback(rating=5)

    def test_feedback_invalid_rating_type(self):
        """Test that rating must be an integer."""
        with pytest.raises(ValueError):
            Feedback(interaction_id="1", rating="five")

    def test_feedback_very_long_comment(self):
        """Test that comment with 500+ chars can be created (validation happens at route level)."""
        long_comment = "a" * 600
        feedback = Feedback(interaction_id="1", comment=long_comment)
        assert len(feedback.comment) == 600

    def test_feedback_empty_comment(self):
        """Test that empty string is allowed for comment."""
        feedback = Feedback(interaction_id="1", comment="")
        assert feedback.comment == ""

    def test_feedback_zero_rating(self):
        """Test that rating of 0 can be created (validation at route level)."""
        feedback = Feedback(interaction_id="1", rating=0)
        assert feedback.rating == 0

    def test_feedback_out_of_range_rating(self):
        """Test that out-of-range rating can be created (validation at route level)."""
        feedback = Feedback(interaction_id="1", rating=10)
        assert feedback.rating == 10
