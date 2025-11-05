from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    event_candidate_id = Column(Integer, ForeignKey("event_candidates.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    ip_address = Column(String, nullable=False)
    nonce = Column(String, nullable=False)
    vote_type = Column(String, nullable=False)  # 'yes', 'no', 'neutral'
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="votes")
    event_candidate = relationship("EventCandidate", back_populates="votes")
    candidate = relationship("Candidate")
