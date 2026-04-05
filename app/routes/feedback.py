from fastapi import APIRouter

from app.models.feedback import Feedback
from ..services.feedback_service import FeedBackService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/feedback", tags=["feedback"])

def get_feedback_service() -> FeedBackService:
    return FeedBackService()


@router.get("/")
def get_feedback():
     return {"status": "Wellbeing endpoint"}

@router.post("/store")
def submit_feedback(
    user_input: Feedback,
    feedback_service: FeedBackService = Depends(get_feedback_service),
):
 feedback_service.store_feeback(user_input.interaction_id, user_input.rating, user_input.comment)
 return {"message": "Feedback submitted"}  


