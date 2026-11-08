from fastapi import APIRouter, Depends, HTTPException
import logging

from app.models.feedback import Feedback
from ..services.feedback_service import FeedBackService
from ..services.service_factory import ServiceFactory

from ..config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


# @router.get("/")
# def get_feedback():
#     logger.info("Feedback status endpoint accessed")
#     return {"status": "Feedback endpoint"}

@router.post("/store")
def submit_feedback(
    user_input: Feedback,
    feedback_service: FeedBackService = Depends(ServiceFactory.get_feedback_service),
):
    logger.info(f"Storing feedback for interaction {user_input.interaction_id}")
    logger.debug(
        f"Feedback data: rating={user_input.rating}, "
        f"feedback='{user_input.feedback[:50] if user_input.feedback else 'None'}...', "
        f"comment='{user_input.comment[:50] if user_input.comment else 'None'}...'"
    )

    try:
        result = feedback_service.store_feedback(
            interaction_id=user_input.interaction_id,
            rating=user_input.rating,
            feedback=user_input.feedback,
            comment=user_input.comment,
        )
        logger.info(f"Successfully stored feedback for interaction {user_input.interaction_id} (rating={user_input.rating})")
        return result
    except ValueError as e:
        logger.error(f"Validation error storing feedback: {e}")
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store feedback for interaction {user_input.interaction_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to store feedback")


