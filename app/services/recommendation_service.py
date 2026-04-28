import json
import logging
import re

from .llm_service import call_gemini_llm, call_gemma_llm
from ..config.settings import settings
from ..config.logging_config import get_logger
from ..utils.prompts import RECOMMENDATION_PROMPT

logger = get_logger(__name__)


class RecommendationService:
    def __init__(self):
        logger.info("RecommendationService initialized")

    def generate_recommendation(self, emotion_result: dict, mood_trend: list = None, history: list = None) -> dict:
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

        preferences, avoid = self._extract_feedback_preferences(history or [])

        # Build context from emotion result and prior feedback
        context = {
            "mood": emotion_result.get("emotion", "neutral"),
            "intensity": emotion_result.get("intensity", "medium"),
            "trend": mood_trend or [],
            "preferences": preferences,
            "avoid": avoid,
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

    def _extract_feedback_preferences(self, history: list) -> tuple[list, list]:
        liked: list[str] = []
        disliked: list[str] = []

        for item in history:
            activity = item.get("activity")
            if not activity:
                continue

            try:
                rating = int(item.get("rating"))
            except (TypeError, ValueError):
                continue

            if rating >= 4:
                liked.append(activity)
            elif rating <= 2:
                disliked.append(activity)

        # Keep insertion order while de-duplicating and cap size to avoid prompt bloat.
        liked = list(dict.fromkeys(liked))[-5:]
        disliked = list(dict.fromkeys(disliked))[-5:]
        return liked, disliked


def build_prompt(context: dict) -> str:
    logger.debug(f"Building prompt with context: {context}")
    trend = context['trend']
    trend_display = ", ".join(trend) if trend else "no prior mood history"
    preferences_display = ", ".join(context.get("preferences", [])) or "none"
    avoid_display = ", ".join(context.get("avoid", [])) or "none"
    prompt = f"""
    User mood: {context['mood']}
    Intensity: {context['intensity']}
    Recent mood history (oldest to newest): {trend_display}
    Activities user liked before: {preferences_display}
    Activities to avoid (poor feedback): {avoid_display}
    {RECOMMENDATION_PROMPT}
    """
    return prompt


def parse_recommendation(response: str) -> dict:
    logger.debug(f"Parsing LLM response: {response[:100]}...")
    try:
        cleaned = re.sub(r"```json|```", "", response).strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON found")

        data = json.loads(match.group())
        result = {
            "activity": data.get("activity", ""),
            "message": data.get("message", ""),
        }
    except Exception:
        result = {
            "activity": "Unable to parse activity",
            "message": response,
        }

    logger.debug(f"Parsed recommendation: {result}")
    return result
