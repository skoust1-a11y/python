from typing import Any, Dict, List

from sqlalchemy.exc import SQLAlchemyError

from ..config.database import SessionLocal
from ..config.logging_config import get_logger
from ..models.interactions import Interaction
from ..services.memory_service import MemoryService

logger = get_logger(__name__)


class FeedBackService:
    def __init__(self):
        self.memory_service = MemoryService()
        logger.info("FeedBackService initialized")
    
    def store_feedback(
        self,
        interaction_id: str,
        rating: int | None = None,
        feedback: str | None = None,
        comment: str | None = None,
    ) -> Dict[str, Any]:
        logger.info(f"Storing feedback for interaction_id: {interaction_id}, rating: {rating}")
        try:
            if rating is not None and not (1 <= rating <= 5):
                raise ValueError("Rating must be an integer between 1 and 5")

            if comment is not None and len(comment) > 500:
                raise ValueError("Comment must be 500 characters or less")

            if feedback is not None and len(feedback) > 500:
                raise ValueError("Feedback must be 500 characters or less")

            if rating is None and feedback is None and comment is None:
                raise ValueError("At least a rating, feedback, or comment must be provided")

            self.memory_service.update_feedback(interaction_id, rating, feedback, comment)
            result = {
                "message": "Feedback submitted successfully",
                "interaction_id": interaction_id,
                "rating": rating,
                "feedback_received": feedback is not None,
                "comment_received": comment is not None,
            }
            logger.debug(
                "Feedback stored - interaction_id: %s, rating: %s, feedback_present: %s, comment_present: %s",
                interaction_id,
                rating,
                feedback is not None,
                comment is not None,
            )
            return result
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error storing feedback for interaction_id {interaction_id}: {str(e)}")
            raise

    # Backward-compatible typo alias used by older tests/callers.
    def store_feeback(self, interaction_id: str, rating: int, comment: str = None):
        return self.store_feedback(interaction_id=interaction_id, rating=rating, comment=comment)
    
    def get_history(self, interaction_id: str) -> List[Dict[str, Any]]:
        logger.debug(f"Retrieving feedback history for interaction_id: {interaction_id}")
        try:
            with SessionLocal() as session:
                interaction = session.get(Interaction, int(interaction_id))
            if interaction is None:
                result = []
            else:
                result = [interaction.to_dict()]
            logger.debug(f"Retrieved {len(result)} feedback records for interaction_id: {interaction_id}")
            return result
        except ValueError:
            logger.error(f"Invalid interaction_id format: {interaction_id}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving feedback history for interaction_id {interaction_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving feedback history for interaction_id {interaction_id}: {str(e)}")
            raise