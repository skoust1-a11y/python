from fastapi import APIRouter, Depends, HTTPException
import logging

from app.models.feedback import Feedback
from ..services.memory_service import MemoryService

from ..config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])

def get_memory_service() -> MemoryService:
    return MemoryService()


# @router.get("/")
# def get_feedback():
#     logger.info("Feedback status endpoint accessed")
#     return {"status": "Feedback endpoint"}

@router.post("/store")
def submit_feedback(
    user_input: Feedback,
    memory_service: MemoryService = Depends(get_memory_service),
):
    logger.info(f"Storing feedback for interaction {user_input.interaction_id}")
    logger.debug(
        f"Feedback data: rating={user_input.rating}, "
        f"feedback='{user_input.feedback[:50] if user_input.feedback else 'None'}...', "
        f"comment='{user_input.comment[:50] if user_input.comment else 'None'}...'"
    )

    # Validate input - both rating and comment are optional, but validate if provided
    if user_input.rating is not None and not (1 <= user_input.rating <= 5):
        logger.warning(f"Invalid rating {user_input.rating} for interaction {user_input.interaction_id}")
        raise HTTPException(
            status_code=400,
            detail="Rating must be an integer between 1 and 5"
        )
    
    if user_input.comment is not None and len(user_input.comment) > 500:
        logger.warning(f"Comment too long ({len(user_input.comment)} chars) for interaction {user_input.interaction_id}")
        raise HTTPException(
            status_code=400,
            detail="Comment must be 500 characters or less"
        )

    if user_input.feedback is not None and len(user_input.feedback) > 500:
        logger.warning(f"Feedback too long ({len(user_input.feedback)} chars) for interaction {user_input.interaction_id}")
        raise HTTPException(
            status_code=400,
            detail="Feedback must be 500 characters or less"
        )
    
    # At least one field (rating, feedback, or comment) should be provided
    if user_input.rating is None and user_input.feedback is None and user_input.comment is None:
        logger.warning(f"No feedback data provided for interaction {user_input.interaction_id}")
        raise HTTPException(
            status_code=400,
            detail="At least a rating, feedback, or comment must be provided"
        )

    try:
        memory_service.update_feedback(
            user_input.interaction_id,
            user_input.rating,
            user_input.feedback,
            user_input.comment
        )
        logger.info(f"Successfully stored feedback for interaction {user_input.interaction_id} (rating={user_input.rating})")
        return {
            "message": "Feedback submitted successfully",
            "interaction_id": user_input.interaction_id,
            "rating": user_input.rating,
            "feedback_received": user_input.feedback is not None,
            "comment_received": user_input.comment is not None
        }
    except ValueError as e:
        logger.error(f"Validation error storing feedback: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store feedback for interaction {user_input.interaction_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to store feedback")


