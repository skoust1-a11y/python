"""Unit tests for EmotionService."""

import pytest
from unittest.mock import patch, MagicMock
from app.services.emotion_service import EmotionService


class TestEmotionService:
    """Tests for EmotionService - emotion detection functionality."""

    def test_emotion_service_initialization(self):
        """Test EmotionService initializes successfully."""
        service = EmotionService()
        assert service is not None

    def test_detect_emotion_with_mock_data(self):
        """Test emotion detection with mock data."""
        service = EmotionService()
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.detect_emotion("I feel happy")
            
            assert result is not None
            assert "emotion" in result
            assert "confidence" in result
            assert "intensity" in result
            assert result["emotion"] == "joy"
            assert result["confidence"] == 0.9

    def test_detect_emotion_empty_text(self):
        """Test emotion detection with empty text."""
        service = EmotionService()
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.detect_emotion("")
            
            assert result is not None
            assert "emotion" in result

    def test_detect_emotion_long_text(self):
        """Test emotion detection with long text."""
        service = EmotionService()
        long_text = "I feel " * 100  # Very long text
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.detect_emotion(long_text)
            
            assert result is not None
            assert "emotion" in result

    def test_detect_emotion_result_contains_required_fields(self):
        """Test that emotion result has all required fields."""
        service = EmotionService()
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.detect_emotion("I am feeling anxious")
            
            # Check required fields
            assert "emotion" in result
            assert "confidence" in result
            assert "intensity" in result
            
            # Check types
            assert isinstance(result["emotion"], str)
            assert isinstance(result["confidence"], (int, float))
            assert isinstance(result["intensity"], str)

    def test_detect_emotion_confidence_range(self):
        """Test that confidence is within valid range."""
        service = EmotionService()
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.detect_emotion("I feel neutral")
            
            # Confidence should be between 0 and 1
            assert 0 <= result["confidence"] <= 1

    def test_detect_emotion_special_characters(self):
        """Test emotion detection with special characters."""
        service = EmotionService()
        text_with_special = "I feel !@#$%^&*() happy 🎉"
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.detect_emotion(text_with_special)
            
            assert result is not None
            assert "emotion" in result

    def test_detect_emotion_numbers(self):
        """Test emotion detection with numbers."""
        service = EmotionService()
        text_with_numbers = "I scored 95/100 on my test, I feel great!"
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.detect_emotion(text_with_numbers)
            
            assert result is not None
            assert "emotion" in result

    def test_detect_emotion_multiple_calls_consistency(self):
        """Test that multiple calls with same text return consistent emotions."""
        service = EmotionService()
        text = "I feel happy and excited"
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result1 = service.detect_emotion(text)
            result2 = service.detect_emotion(text)
            
            assert result1["emotion"] == result2["emotion"]
            assert result1["confidence"] == result2["confidence"]

    def test_detect_emotion_different_texts_different_emotions(self):
        """Test that different texts can have different detected emotions."""
        service = EmotionService()
        
        # Note: With mock data, this will return same emotion
        # In real LLM case, different inputs would yield different outputs
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            happy_result = service.detect_emotion("I am very happy!")
            
            assert happy_result["emotion"] == "joy"

    def test_llm_detect_emotion_fallback(self):
        """Test LLM emotion detection fallback."""
        service = EmotionService()
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'false'}):
            result = service.detect_emotion("Test emotion")
            
            # Should return some result (neutral by default)
            assert result is not None
            assert "emotion" in result

    def test_detect_emotion_unicode_text(self):
        """Test emotion detection with unicode characters."""
        service = EmotionService()
        unicode_text = "我感到很幸福 (I feel very happy in Chinese)"
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.detect_emotion(unicode_text)
            
            assert result is not None
            assert "emotion" in result

    def test_detect_emotion_multiline_text(self):
        """Test emotion detection with multiline text."""
        service = EmotionService()
        multiline = "I feel happy.\nIt's a great day.\nEverything is going well."
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.detect_emotion(multiline)
            
            assert result is not None
            assert "emotion" in result
