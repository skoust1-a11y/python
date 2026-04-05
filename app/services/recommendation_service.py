from .llm_service import call_gemini_llm, call_gemma_llm
from ..config import settings


class RecommendationService:
    def generate_recommendation(self, emotion_result: dict) -> dict:
        if settings.get_env("TEST_WITH_MOCK_DATA", "false").lower() == "true":
            # Return mock data
            return {
                "activity": "Mock activity: Take a deep breath",
                "message": "This is a mock recommendation for testing."
            }
        
        # Build context from emotion result
        context = {
            "mood": emotion_result.get("emotion", "neutral"),
            "intensity": emotion_result.get("intensity", "medium"),
            "trend": "stable",  # Default, could be derived if available
            "preferences": [],  # Default empty
            "avoid": []  # Default empty
        }
        
        prompt = build_prompt(context)
        try:
            llm_response = call_gemini_llm(prompt)
        except Exception as e:
            # Fallback to Gemma LLM
            llm_response = call_gemma_llm(prompt)
        return parse_recommendation(llm_response)


def build_prompt(context: dict) -> str:
    return f"""
    User mood: {context['mood']}
    Intensity: {context['intensity']}
    Trend: {context['trend']}
    Preferences: {context['preferences']}
    Avoid: {context['avoid']}

    Suggest a unique 5-minute wellbeing activity.
    Keep it practical and not repetitive.
    """


def parse_recommendation(response: str) -> dict:
    # ideally JSON parse
    return {
        "activity": response,
        "message": response
    }