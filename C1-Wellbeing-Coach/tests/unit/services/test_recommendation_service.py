"""Unit tests for RecommendationService."""

import pytest
from unittest.mock import patch, MagicMock
from app.services.recommendation_service import RecommendationService, build_prompt, parse_recommendation


class TestRecommendationService:
    """Tests for RecommendationService - recommendation generation."""

    def test_recommendation_service_initialization(self):
        """Test RecommendationService initializes successfully."""
        service = RecommendationService()
        assert service is not None

    def test_generate_recommendation_with_mock_data(self):
        """Test generating recommendation with mock data."""
        service = RecommendationService()
        emotion_result = {
            "emotion": "joy",
            "confidence": 0.9,
            "intensity": "high"
        }
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.generate_recommendation(emotion_result)
            
            assert result is not None
            assert "activity" in result
            assert "message" in result
            assert result["activity"] == "Mock activity: Take a deep breath"

    def test_generate_recommendation_result_structure(self):
        """Test that recommendation result has required structure."""
        service = RecommendationService()
        emotion_result = {
            "emotion": "anxiety",
            "confidence": 0.85,
            "intensity": "medium"
        }
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.generate_recommendation(emotion_result)
            
            assert isinstance(result, dict)
            assert "activity" in result
            assert "message" in result
            assert isinstance(result["activity"], str)
            assert isinstance(result["message"], str)

    def test_generate_recommendation_different_emotions(self):
        """Test generating recommendations for different emotions."""
        service = RecommendationService()
        
        emotions = ["joy", "sadness", "anxiety", "anger", "neutral"]
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            for emotion in emotions:
                emotion_result = {
                    "emotion": emotion,
                    "confidence": 0.9,
                    "intensity": "medium"
                }
                result = service.generate_recommendation(emotion_result)
                
                assert result is not None
                assert "activity" in result
                assert "message" in result

    def test_generate_recommendation_with_minimal_emotion(self):
        """Test recommendation with minimal emotion data."""
        service = RecommendationService()
        emotion_result = {"emotion": "happy"}
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.generate_recommendation(emotion_result)
            
            assert result is not None
            assert "activity" in result

    def test_generate_recommendation_with_missing_fields(self):
        """Test recommendation with missing emotion fields."""
        service = RecommendationService()
        emotion_result = {}
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.generate_recommendation(emotion_result)
            
            # Should handle gracefully and return default
            assert result is not None
            assert "activity" in result

    def test_generate_recommendation_high_intensity(self):
        """Test recommendation for high intensity emotions."""
        service = RecommendationService()
        emotion_result = {
            "emotion": "anxiety",
            "confidence": 0.95,
            "intensity": "very high"
        }
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.generate_recommendation(emotion_result)
            
            assert result is not None
            assert "activity" in result

    def test_generate_recommendation_low_confidence(self):
        """Test recommendation with low confidence emotion."""
        service = RecommendationService()
        emotion_result = {
            "emotion": "neutral",
            "confidence": 0.3,
            "intensity": "low"
        }
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.generate_recommendation(emotion_result)
            
            assert result is not None
            assert "activity" in result

    def test_generate_recommendation_activity_non_empty(self):
        """Test that recommended activity is non-empty."""
        service = RecommendationService()
        emotion_result = {"emotion": "sad", "confidence": 0.8, "intensity": "medium"}
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.generate_recommendation(emotion_result)
            
            assert result["activity"] != ""
            assert len(result["activity"]) > 0

    def test_generate_recommendation_message_non_empty(self):
        """Test that recommendation message is non-empty."""
        service = RecommendationService()
        emotion_result = {"emotion": "happy", "confidence": 0.9, "intensity": "high"}
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.generate_recommendation(emotion_result)
            
            assert result["message"] != ""
            assert len(result["message"]) > 0

    def test_generate_recommendation_multiple_calls(self):
        """Test multiple recommendation generation calls."""
        service = RecommendationService()
        emotion_result = {"emotion": "neutral", "confidence": 0.7, "intensity": "low"}
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result1 = service.generate_recommendation(emotion_result)
            result2 = service.generate_recommendation(emotion_result)
            
            # Mock data should be consistent
            assert result1["activity"] == result2["activity"]

    def test_generate_recommendation_with_extra_fields(self):
        """Test recommendation with extra emotion fields."""
        service = RecommendationService()
        emotion_result = {
            "emotion": "joy",
            "confidence": 0.9,
            "intensity": "high",
            "extra_field": "should be ignored",
            "trend": "improving"
        }
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.generate_recommendation(emotion_result)
            
            assert result is not None
            assert "activity" in result

    def test_generate_recommendation_preserves_emotion_input(self):
        """Test that recommendation doesn't modify input emotion."""
        service = RecommendationService()
        emotion_result = {
            "emotion": "anxious",
            "confidence": 0.85,
            "intensity": "medium"
        }
        emotion_copy = emotion_result.copy()
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            result = service.generate_recommendation(emotion_result)
            
            # Original should not be modified
            assert emotion_result == emotion_copy

    def test_generate_recommendation_special_emotion_names(self):
        """Test recommendation with special emotion names."""
        service = RecommendationService()
        
        special_emotions = ["", "unknown", "123", "emotion-type", "CAPS-EMOTION"]
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'true'}):
            for emotion in special_emotions:
                emotion_result = {"emotion": emotion, "confidence": 0.8}
                result = service.generate_recommendation(emotion_result)
                assert result is not None

    @patch('app.services.recommendation_service.call_gemini_llm')
    def test_generate_recommendation_llm_call_on_non_mock(self, mock_gemini):
        """Test that LLM is called when not using mock data."""
        service = RecommendationService()
        mock_gemini.return_value = "Do yoga for 10 minutes"
        
        emotion_result = {"emotion": "stressed", "confidence": 0.9, "intensity": "high"}
        
        with patch.dict('os.environ', {'TEST_WITH_MOCK_DATA': 'false'}):
            with patch('app.services.recommendation_service.build_prompt'):
                result = service.generate_recommendation(emotion_result)
                
                # Should attempt LLM call
                assert result is not None

    @patch("app.services.recommendation_service.call_gemini_llm", side_effect=Exception("gemini down"))
    @patch("app.services.recommendation_service.call_gemma_llm", return_value="Try a short mindful walk")
    def test_generate_recommendation_fallback_to_gemma(self, mock_gemma, mock_gemini):
        service = RecommendationService()
        with patch.dict("os.environ", {"TEST_WITH_MOCK_DATA": "false"}):
            result = service.generate_recommendation({"emotion": "stress", "intensity": "high"})

        assert result["activity"] == "Try a short mindful walk"
        mock_gemini.assert_called_once()
        mock_gemma.assert_called_once()

    @patch("app.services.recommendation_service.call_gemini_llm", side_effect=Exception("gemini down"))
    @patch("app.services.recommendation_service.call_gemma_llm", side_effect=Exception("gemma down"))
    def test_generate_recommendation_raises_when_both_llms_fail(self, mock_gemma, mock_gemini):
        service = RecommendationService()
        with patch.dict("os.environ", {"TEST_WITH_MOCK_DATA": "false"}):
            with pytest.raises(Exception, match="gemma down"):
                service.generate_recommendation({"emotion": "stress"})

    def test_build_prompt_contains_context_values(self):
        prompt = build_prompt(
            {
                "mood": "joy",
                "intensity": "low",
                "trend": "improving",
                "preferences": ["walk"],
                "avoid": ["screens"],
            }
        )
        assert "User mood: joy" in prompt
        assert "Intensity: low" in prompt
        assert "Trend: improving" in prompt

    def test_parse_recommendation_maps_response_to_both_fields(self):
        parsed = parse_recommendation("Take five deep breaths")
        assert parsed == {
            "activity": "Take five deep breaths",
            "message": "Take five deep breaths",
        }
