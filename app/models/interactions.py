from typing import Any, Dict

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func

from app.config.database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    interaction_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    user_input = Column(Text, nullable=False)
    mood = Column(String, nullable=True)
    intensity = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    activity = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True, default=None)   # 1-5 scale, None if not rated
    feedback = Column(Text, nullable=True, default=None)    # General feedback text
    comment = Column(Text, nullable=True, default=None)     # User comment on interaction
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "user_id": self.user_id,
            "user_input": self.user_input,
            "mood": self.mood,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "activity": self.activity,
            "message": self.message,
            "rating": self.rating,
            "feedback": self.feedback,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
