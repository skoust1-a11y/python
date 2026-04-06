import logging
from typing import Dict, Any, List

from sqlalchemy.exc import SQLAlchemyError

from ..models.interactions import Interaction
from ..config.database import SessionLocal, initialize_database
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class MemoryService:
    def __init__(self):
        logger.info("Initializing MemoryService")
        initialize_database()

    def store_interaction(self, interaction_data: Dict[str, Any]) -> str:
        """Store a complete wellbeing interaction."""
        user_id = interaction_data["user_id"]
        user_input = interaction_data.get("user_input", "")
        mood = interaction_data.get("mood")
        intensity = interaction_data.get("intensity")
        confidence = interaction_data.get("confidence")
        activity = interaction_data.get("activity")
        message = interaction_data.get("message")
        rating = interaction_data.get("rating")
        feedback = interaction_data.get("feedback")
        comment = interaction_data.get("comment")

        logger.info(f"Storing interaction for user {user_id}")
        logger.debug(
            f"Interaction data: user_input='{user_input[:50]}...', mood={mood}, intensity={intensity}"
        )

        try:
            with SessionLocal() as session:
                interaction = Interaction(
                    user_id=user_id,
                    user_input=user_input,
                    mood=mood,
                    intensity=intensity,
                    confidence=confidence,
                    activity=activity,
                    message=message,
                    rating=rating,
                    feedback=feedback,
                    comment=comment,
                )
                session.add(interaction)
                session.commit()
                session.refresh(interaction)
                interaction_id = interaction.interaction_id

            logger.info(f"Successfully stored interaction {interaction_id} for user {user_id}")
            return str(interaction_id)
        except SQLAlchemyError as e:
            logger.error(f"Failed to store interaction for user {user_id}: {e}")
            raise

    def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Return the latest interaction history for a user."""
        logger.info(f"Retrieving interaction history for user {user_id}")
        try:
            with SessionLocal() as session:
                results = (
                    session.query(Interaction)
                    .filter(Interaction.user_id == user_id)
                    .order_by(Interaction.created_at.desc())
                    .limit(50)
                    .all()
                )

            history = [interaction.to_dict() for interaction in results]
            logger.info(f"Retrieved {len(history)} interactions for user {user_id}")
            return history
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve history for user {user_id}: {e}")
            raise

    def has_feedback(self, interaction_id: str) -> bool:
        """Check if an interaction has feedback submitted."""
        try:
            with SessionLocal() as session:
                interaction = session.get(Interaction, int(interaction_id))
                if interaction is None:
                    return False
                has_rating = interaction.rating is not None
                logger.debug(f"Interaction {interaction_id} has_feedback={has_rating}")
                return has_rating
        except SQLAlchemyError as e:
            logger.error(f"Failed to check feedback status for interaction {interaction_id}: {e}")
            return False

    def update_feedback(
        self,
        interaction_id: str,
        rating: int = None,
        feedback: str = None,
        comment: str = None,
    ):
        """Update feedback for an existing interaction. Rating and comment are optional."""
        logger.info(f"Updating feedback for interaction {interaction_id}")
        # Validate rating range if provided
        if rating is not None and not (1 <= rating <= 5):
            logger.error(f"Invalid rating {rating}. Must be between 1 and 5.")
            raise ValueError("Rating must be between 1 and 5")
        
        if rating is None and comment is None and feedback is None:
            logger.error(f"No feedback provided for interaction {interaction_id}")
            raise ValueError("At least one feedback field must be provided")
        
        try:
            with SessionLocal() as session:
                interaction = session.get(Interaction, int(interaction_id))
                if interaction is None:
                    logger.error(f"Interaction {interaction_id} not found")
                    raise ValueError(f"Interaction {interaction_id} not found")

                interaction.rating = rating
                interaction.feedback = feedback
                interaction.comment = comment
                session.commit()

            logger.info(f"Successfully updated feedback for interaction {interaction_id} with rating={rating}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to update feedback for interaction {interaction_id}: {e}")
            raise
