from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Candidate Schemas
class CandidateBase(BaseModel):
    full_name: str
    image: Optional[str] = None
    birth_date: Optional[date] = None
    degree: Optional[str] = None
    which_position: Optional[str] = None
    election_time: Optional[str] = None
    description: Optional[str] = None


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    which_position: Optional[str] = None
    election_time: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None


class CandidateResponse(CandidateBase):
    id: int
    from_api: bool
    external_id: Optional[int] = None

    class Config:
        from_attributes = True


# Event Schemas
class EventStatus(str, Enum):
    pending = "pending"
    active = "active"
    finished = "finished"
    archived = "archived"


class EventCreate(BaseModel):
    name: str
    candidate_ids: List[int]
    duration_sec: int = 15


class EventResponse(BaseModel):
    id: int
    name: str
    link: str
    duration_sec: int
    status: EventStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventWithCandidates(EventResponse):
    candidates: List[CandidateResponse]


# Vote Schemas
class VoteRequest(BaseModel):
    type: str = "cast_vote"
    candidate_id: int
    nonce: str


class VoteTally(BaseModel):
    type: str = "tally"
    candidate_id: int
    votes: int
    percent: float


# Display Schemas
class DisplaySetCurrent(BaseModel):
    candidate_id: int
    countdown_sec: int = 15


class DisplayUpdate(BaseModel):
    type: str = "display_update"
    candidate: Optional[CandidateResponse] = None
    remaining_ms: Optional[int] = None


# Admin Schemas
class AdminEventDetail(EventResponse):
    total_votes: int
    candidates_tally: List[dict]
