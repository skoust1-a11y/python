from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..models.user_input import UserInput
from ..models.response import Response
from ..services.emotion_service import EmotionService
from ..services.recommendation_service import RecommendationService
from ..services.memory_service import MemoryService
from ..services.service_factory import ServiceFactory
from ..config.settings import settings

router = APIRouter(prefix="/wellbeing", tags=["wellbeing"])

limiter = Limiter(key_func=get_remote_address)


# @router.get("/")
# def get_wellbeing_status():
#     return {"status": "Wellbeing endpoint"}

@router.post("/analyze", response_model=Response)
@limiter.limit(lambda: f"{settings.get_env('RATE_LIMIT_PER_MINUTE', '10')}/minute")
def analyze_emotion(
    request: Request,
    user_input: UserInput,
    emotion_service: EmotionService = Depends(ServiceFactory.get_emotion_service),
    recommendation_service: RecommendationService = Depends(ServiceFactory.get_recommendation_service),
    memory_service: MemoryService = Depends(ServiceFactory.get_memory_service),
):
    emotion_result = emotion_service.detect_emotion(user_input.text)

    # Fetch last 10 interactions, reverse to chronological order, extract distinct moods
    recent_history = memory_service.get_history(user_input.user_id)
    last_10 = recent_history[:10][::-1]
    mood_trend = list(dict.fromkeys(
        entry["mood"] for entry in last_10 if entry.get("mood")
    ))

    recommendations = recommendation_service.generate_recommendation(
        emotion_result,
        mood_trend=mood_trend,
        history=recent_history,
    )

    interaction_id = memory_service.store_interaction(
        {
            "user_id": user_input.user_id,
            "user_input": user_input.text,
            "mood": emotion_result.get("emotion"),
            "intensity": _safe_float(emotion_result.get("intensity")),
            "confidence": _safe_float(emotion_result.get("confidence")),
            "activity": recommendations.get("activity"),
            "message": recommendations.get("message"),
        }
    )

    return Response(
        interaction_id=interaction_id,
        emotion=emotion_result.get("emotion"),
        confidence=emotion_result.get("confidence"),
        message=f"Detected emotion: {emotion_result.get('emotion')}",
        recommendations=recommendations,
    )


@router.get("/history/{user_id}")
@limiter.limit("30/minute")
def get_user_history(
    request: Request,
    user_id: str,
    memory_service: MemoryService = Depends(ServiceFactory.get_memory_service),
):
    history = memory_service.get_history(user_id)
    return {"user_id": user_id, "history": history}


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

#----------------JUST TO TEST THE MOHIT'S WORK< LATER ON U CAN REMOVE IT-----------------

# @router.post('/mohit')
# def mohit_soln(
#     user_input : UserInput,
#      emotion_service: EmotionService = Depends(get_emotion_service)
# ):
#     emotion = emotion_service.detect_emotion(user_input.text)
#     return {
#         'emotion_call' : emotion.get('emotion'),
#         'emotion':emotion
#     }