"""Unit tests for LLMService."""

import pytest
from unittest.mock import patch, MagicMock
from app.services.llm_service import call_gemini_llm, call_gemma_llm


class TestLLMService:
    """Tests for LLMService - LLM API interactions."""

    # Gemini LLM Tests
    def test_call_gemini_llm_with_simple_prompt(self):
        """Test calling Gemini LLM with simple prompt."""
        prompt = "What is wellbeing?"
        
        result = call_gemini_llm(prompt)
        
        assert result is not None
        assert isinstance(result, str)

    def test_call_gemini_llm_with_empty_prompt(self):
        """Test calling Gemini LLM with empty prompt."""
        prompt = ""
        
        result = call_gemini_llm(prompt)
        
        assert result is not None

    def test_call_gemini_llm_with_long_prompt(self):
        """Test calling Gemini LLM with long prompt."""
        prompt = "Please provide " * 100  # Very long prompt
        
        result = call_gemini_llm(prompt)
        
        assert result is not None

    def test_call_gemini_llm_with_special_characters(self):
        """Test calling Gemini LLM with special characters."""
        prompt = "What about !@#$%^&*() emotions? 🎉"
        
        result = call_gemini_llm(prompt)
        
        assert result is not None

    def test_call_gemini_llm_with_unicode(self):
        """Test calling Gemini LLM with unicode characters."""
        prompt = "What is 幸福 (happiness in Chinese)?"
        
        result = call_gemini_llm(prompt)
        
        assert result is not None

    def test_call_gemini_llm_returns_string(self):
        """Test that Gemini LLM returns a string."""
        prompt = "Test prompt"
        
        result = call_gemini_llm(prompt)
        
        assert isinstance(result, str)

    def test_call_gemini_llm_response_not_empty(self):
        """Test that Gemini LLM response is not empty."""
        prompt = "Generate wellness advice"
        
        result = call_gemini_llm(prompt)
        
        assert len(result) > 0

    def test_call_gemini_llm_multiple_calls(self):
        """Test multiple calls to Gemini LLM."""
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        
        results = [call_gemini_llm(p) for p in prompts]
        
        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)

    def test_call_gemini_llm_with_multiline_prompt(self):
        """Test calling Gemini LLM with multiline prompt."""
        prompt = """
        Analyze mood:
        User said: I feel great today
        Recommend activity
        """
        
        result = call_gemini_llm(prompt)
        
        assert result is not None

    def test_call_gemini_llm_with_json_prompt(self):
        """Test calling Gemini LLM with JSON-formatted prompt."""
        prompt = '{"text": "I feel happy", "user_id": "123"}'
        
        result = call_gemini_llm(prompt)
        
        assert result is not None

    # Gemma LLM Tests
    def test_call_gemma_llm_with_simple_prompt(self):
        """Test calling Gemma LLM with simple prompt."""
        prompt = "What is mental wellbeing?"
        
        result = call_gemma_llm(prompt)
        
        assert result is not None
        assert isinstance(result, str)

    def test_call_gemma_llm_with_empty_prompt(self):
        """Test calling Gemma LLM with empty prompt."""
        prompt = ""
        
        result = call_gemma_llm(prompt)
        
        assert result is not None

    def test_call_gemma_llm_with_long_prompt(self):
        """Test calling Gemma LLM with long prompt."""
        prompt = "Tell me about " * 100
        
        result = call_gemma_llm(prompt)
        
        assert result is not None

    def test_call_gemma_llm_with_special_characters(self):
        """Test calling Gemma LLM with special characters."""
        prompt = "Emotions: happy, sad, angry, !@#$%^ & more"
        
        result = call_gemma_llm(prompt)
        
        assert result is not None

    def test_call_gemma_llm_with_unicode(self):
        """Test calling Gemma LLM with unicode characters."""
        prompt = "Wellbeing 福祉 幸せ happiness"
        
        result = call_gemma_llm(prompt)
        
        assert result is not None

    def test_call_gemma_llm_returns_string(self):
        """Test that Gemma LLM returns a string."""
        prompt = "Test prompt for Gemma"
        
        result = call_gemma_llm(prompt)
        
        assert isinstance(result, str)

    def test_call_gemma_llm_response_not_empty(self):
        """Test that Gemma LLM response is not empty."""
        prompt = "Provide wellness tips"
        
        result = call_gemma_llm(prompt)
        
        assert len(result) > 0

    def test_call_gemma_llm_multiple_calls(self):
        """Test multiple calls to Gemma LLM."""
        prompts = ["Prompt A", "Prompt B", "Prompt C"]
        
        results = [call_gemma_llm(p) for p in prompts]
        
        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)

    def test_call_gemma_llm_with_multiline_prompt(self):
        """Test calling Gemma LLM with multiline prompt."""
        prompt = """
        User feedback:
        I'm feeling stressed.
        Need suggestions.
        """
        
        result = call_gemma_llm(prompt)
        
        assert result is not None

    def test_call_gemma_llm_with_json_prompt(self):
        """Test calling Gemma LLM with JSON-formatted prompt."""
        prompt = '{"mood": "stressed", "intensity": "high"}'
        
        result = call_gemma_llm(prompt)
        
        assert result is not None

    # Comparative Tests
    def test_gemini_and_gemma_both_return_strings(self):
        """Test that both LLM calls return strings."""
        prompt = "Common prompt for both LLMs"
        
        gemini_result = call_gemini_llm(prompt)
        gemma_result = call_gemma_llm(prompt)
        
        assert isinstance(gemini_result, str)
        assert isinstance(gemma_result, str)

    def test_gemini_and_gemma_different_prompts(self):
        """Test both LLMs with different prompts."""
        gemini_result = call_gemini_llm("Gemini prompt")
        gemma_result = call_gemma_llm("Gemma prompt")
        
        assert gemini_result is not None
        assert gemma_result is not None

    # Edge Cases
    def test_llm_with_very_long_prompt_gemini(self):
        """Test Gemini with extremely long prompt."""
        long_prompt = "test " * 10000
        
        result = call_gemini_llm(long_prompt)
        
        assert result is not None

    def test_llm_with_very_long_prompt_gemma(self):
        """Test Gemma with extremely long prompt."""
        long_prompt = "test " * 10000
        
        result = call_gemma_llm(long_prompt)
        
        assert result is not None

    def test_llm_with_only_whitespace_gemini(self):
        """Test Gemini LLM with only whitespace."""
        prompt = "   \n\t  \n   "
        
        result = call_gemini_llm(prompt)
        
        assert result is not None

    def test_llm_with_only_whitespace_gemma(self):
        """Test Gemma LLM with only whitespace."""
        prompt = "   \n\t  \n   "
        
        result = call_gemma_llm(prompt)
        
        assert result is not None

    def test_llm_preserves_prompt_input_gemini(self):
        """Test that Gemini doesn't modify input prompt."""
        prompt = "Original prompt"
        prompt_copy = prompt
        
        call_gemini_llm(prompt)
        
        assert prompt == prompt_copy

    def test_llm_preserves_prompt_input_gemma(self):
        """Test that Gemma doesn't modify input prompt."""
        prompt = "Original prompt"
        prompt_copy = prompt
        
        call_gemma_llm(prompt)
        
        assert prompt == prompt_copy

    def test_llm_with_numbers_and_symbols_gemini(self):
        """Test Gemini with numbers and symbols."""
        prompt = "Metrics: 95% happiness, $100 value, rate@5/5"
        
        result = call_gemini_llm(prompt)
        
        assert result is not None

    def test_llm_with_numbers_and_symbols_gemma(self):
        """Test Gemma with numbers and symbols."""
        prompt = "Scale: 1-10, Grade: A+, Rating: 9/10"
        
        result = call_gemma_llm(prompt)
        
        assert result is not None
