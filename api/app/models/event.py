from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from ..core.database import Base


class EventStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    finished = "finished"
    archived = "archived"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    link = Column(String, unique=True, index=True, nullable=False)
    duration_sec = Column(Integer, default=15)
    status = Column(Enum(EventStatus), default=EventStatus.pending)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    current_candidate_index = Column(Integer, default=0)  # For sequential voting

    # Relationships
    event_candidates = relationship("EventCandidate", back_populates="event")
    votes = relationship("Vote", back_populates="event")
    display_state = relationship("DisplayState", back_populates="event", uselist=False)


class EventCandidate(Base):
    __tablename__ = "event_candidates"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    order = Column(Integer, default=0)  # Order for sequential voting
    status = Column(String, default="pending")  # pending, active, completed
    timer_started_at = Column(DateTime, nullable=True)  # When timer was started for this candidate
    candidate_group = Column(String, nullable=True)  # Group identifier for grouped voting

    # Relationships
    event = relationship("Event", back_populates="event_candidates")
    candidate = relationship("Candidate")
    votes = relationship("Vote", back_populates="event_candidate")
