import logging
from .llm_service import call_gemini_llm, call_gemma_llm
from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class RecommendationService:
    def __init__(self):
        logger.info("RecommendationService initialized")

    def generate_recommendation(self, emotion_result: dict) -> dict:
        logger.debug(f"Generating recommendation for emotion: {emotion_result}")

        if settings.get_env("TEST_WITH_MOCK_DATA", "false").lower() == "true":
            logger.debug("Using mock recommendation data for testing")
            # Return mock data
            result = {
                "activity": "Mock activity: Take a deep breath",
                "message": "This is a mock recommendation for testing."
            }
            logger.debug(f"Mock recommendation result: {result}")
            return result

        # Build context from emotion result
        context = {
            "mood": emotion_result.get("emotion", "neutral"),
            "intensity": emotion_result.get("intensity", "medium"),
            "trend": "stable",  # Default, could be derived if available
            "preferences": [],  # Default empty
            "avoid": []  # Default empty
        }

        logger.debug(f"Recommendation context: {context}")

        prompt = build_prompt(context)
        logger.debug(f"Generated prompt for LLM: {prompt[:100]}...")

        try:
            logger.debug("Calling Gemini LLM for recommendation")
            llm_response = call_gemini_llm(prompt)
            logger.debug(f"Gemini LLM response: {llm_response[:100]}...")
        except Exception as e:
            logger.warning(f"Gemini LLM failed, falling back to Gemma: {e}")
            try:
                llm_response = call_gemma_llm(prompt)
                logger.debug(f"Gemma LLM response: {llm_response[:100]}...")
            except Exception as e2:
                logger.error(f"Both LLM calls failed: Gemini({e}), Gemma({e2})")
                raise e2

        result = parse_recommendation(llm_response)
        logger.debug(f"Parsed recommendation result: {result}")
        return result


def build_prompt(context: dict) -> str:
    logger.debug(f"Building prompt with context: {context}")
    prompt = f"""
    User mood: {context['mood']}
    Intensity: {context['intensity']}
    Trend: {context['trend']}
    Preferences: {context['preferences']}
    Avoid: {context['avoid']}

    Suggest a unique 5-minute wellbeing activity.
    Keep it practical and not repetitive.
    """
    return prompt


def parse_recommendation(response: str) -> dict:
    logger.debug(f"Parsing LLM response: {response[:100]}...")
    # ideally JSON parse
    result = {
        "activity": response,
        "message": response
    }
    logger.debug(f"Parsed recommendation: {result}")
    return result