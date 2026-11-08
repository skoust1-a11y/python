from .emotion_service import EmotionService
from .recommendation_service import RecommendationService
from .memory_service import MemoryService
from .feedback_service import FeedBackService


class ServiceFactory:
    """Centralised factory for all application services.

    Each method is a zero-argument callable so it can be passed directly to
    FastAPI's ``Depends()``::

        emotion_service: EmotionService = Depends(ServiceFactory.get_emotion_service)
    """

    @staticmethod
    def get_emotion_service() -> EmotionService:
        return EmotionService()

    @staticmethod
    def get_recommendation_service() -> RecommendationService:
        return RecommendationService()

    @staticmethod
    def get_memory_service() -> MemoryService:
        return MemoryService()

    @staticmethod
    def get_feedback_service() -> FeedBackService:
        return FeedBackService()
