from fastapi import APIRouter, Depends
from ..models.user_input import UserInput
from ..models.response import Response
from ..services.emotion_service import EmotionService
from ..services.recommendation_service import RecommendationService

router = APIRouter(prefix="/wellbeing", tags=["wellbeing"])


def get_emotion_service() -> EmotionService:
    return EmotionService()


def get_recommendation_service() -> RecommendationService:
    return RecommendationService()


@router.get("/")
def get_wellbeing_status():
    return {"status": "Wellbeing endpoint"}

@router.post("/analyze", response_model=Response)
def analyze_emotion(
    user_input: UserInput,
    emotion_service: EmotionService = Depends(get_emotion_service),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    emotion_result = emotion_service.analyze_emotion(user_input.text)
    recommendations = recommendation_service.get_recommendations(emotion_result.get("emotion"))

    return Response(
        emotion=emotion_result.get("emotion"),
        confidence=emotion_result.get("confidence"),
        message=f"Detected emotion: {emotion_result.get('emotion')}",
        recommendations=recommendations,
    )