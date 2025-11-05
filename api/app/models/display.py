from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base


class DisplayState(Base):
    __tablename__ = "display_states"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, unique=True)
    current_candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=True)
    countdown_until = Column(DateTime, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="display_state")
    candidate = relationship("Candidate")
