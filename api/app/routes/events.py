from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
from ..core.database import get_db
from ..core.schemas import EventCreate, EventResponse, EventWithCandidates
from ..core.dependencies import get_current_user
from ..models.event import Event, EventCandidate, EventStatus
from ..models.candidate import Candidate
from ..models.display import DisplayState
from ..models.vote import Vote
from ..models.admin import AdminUser
from ..services.event_results import calculate_event_results
from ..services.word_export import generate_results_word

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventResponse)
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Create a new voting event"""
    # Generate unique link
    link = str(uuid.uuid4())[:8]

    # Create event
    db_event = Event(
        name=event.name,
        link=link,
        duration_sec=event.duration_sec,
        status=EventStatus.pending
    )
    db.add(db_event)
    db.flush()

    # Add candidates to event with ordering
    for idx, candidate_id in enumerate(event.candidate_ids):
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found"
            )

        event_candidate = EventCandidate(
            event_id=db_event.id,
            candidate_id=candidate_id,
            order=idx  # Set order based on array position
        )
        db.add(event_candidate)

    # Create display state
    display_state = DisplayState(event_id=db_event.id)
    db.add(display_state)

    db.commit()
    db.refresh(db_event)
    return db_event


@router.post("/{event_id}/start", response_model=EventResponse)
def start_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Start a voting event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if event.status != EventStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event is already {event.status}"
        )

    # Ensure each candidate has required metadata before starting
    event_candidates = db.query(EventCandidate).filter(
        EventCandidate.event_id == event_id
    ).all()

    if not event_candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event has no candidates"
        )

    missing_position = []
    for ec in event_candidates:
        candidate = db.query(Candidate).filter(Candidate.id == ec.candidate_id).first()
        position_value = None
        if candidate:
            position_value = candidate.which_position or candidate.position
        if not candidate or not position_value or not position_value.strip():
            name = candidate.full_name if candidate and candidate.full_name else f"ID {ec.candidate_id}"
            missing_position.append(name)

    if missing_position:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All candidates must have a position before starting. Missing for: " + ", ".join(missing_position)
        )

    event.status = EventStatus.active
    event.start_time = datetime.utcnow()
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/stop", response_model=EventResponse)
def stop_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Stop a voting event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if event.status != EventStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event is not active"
        )

    event.status = EventStatus.finished
    event.end_time = datetime.utcnow()
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/archive", response_model=EventResponse)
def archive_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Archive an event (admin only)"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if event.status == EventStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stop the event before archiving"
        )

    event.status = EventStatus.archived
    if not event.end_time:
        event.end_time = datetime.utcnow()

    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}/results")
def get_event_results(event_id: int, db: Session = Depends(get_db)):
    """Get voting results for an event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    results, total_votes = calculate_event_results(db, event_id)
    return {
        "event_id": event_id,
        "event_name": event.name,
        "status": event.status,
        "total_votes": total_votes,
        "results": results
    }


@router.get("/by-link/{link}/results")
def get_event_results_by_link(link: str, db: Session = Depends(get_db)):
    """Get voting results for an event by its public link"""
    event = db.query(Event).filter(Event.link == link).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    results, total_votes = calculate_event_results(db, event.id)
    return {
        "event_id": event.id,
        "event_name": event.name,
        "status": event.status,
        "total_votes": total_votes,
        "results": results
    }


@router.get("/by-link/{link}", response_model=EventWithCandidates)
def get_event_by_link(link: str, db: Session = Depends(get_db)):
    """Get event by link (public endpoint)"""
    event = db.query(Event).filter(Event.link == link).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Get event candidates
    candidates = db.query(Candidate).join(
        EventCandidate, EventCandidate.candidate_id == Candidate.id
    ).filter(
        EventCandidate.event_id == event.id
    ).all()

    return {
        **event.__dict__,
        "candidates": candidates
    }


@router.get("", response_model=List[EventResponse])
def get_events(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get all events (admin only)"""
    events = db.query(Event).order_by(Event.id.desc()).all()
    return events


@router.get("/{event_id}", response_model=EventWithCandidates)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get event details (admin only)"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Get event candidates
    candidates = db.query(Candidate).join(
        EventCandidate, EventCandidate.candidate_id == Candidate.id
    ).filter(
        EventCandidate.event_id == event.id
    ).all()

    return {
        **event.__dict__,
        "candidates": candidates
    }


@router.get("/{event_id}/results/download")
def download_event_results(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Download voting results as Word document (admin only)"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    results, total_participants = calculate_event_results(db, event_id)

    if not results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No results available for this event"
        )

    # Generate Word document
    buffer = generate_results_word(event.name, results, total_participants)

    # Create filename
    filename = f"{event.name.replace(' ', '_')}_natijalar.docx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/by-link/{link}/results/download")
def download_event_results_by_link(link: str, db: Session = Depends(get_db)):
    """Download voting results as Word document by link (public)"""
    event = db.query(Event).filter(Event.link == link).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    results, total_participants = calculate_event_results(db, event.id)

    if not results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No results available for this event"
        )

    # Generate Word document
    buffer = generate_results_word(event.name, results, total_participants)

    # Create filename
    filename = f"{event.name.replace(' ', '_')}_natijalar.docx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Delete an event and all related data (admin only)"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Remove votes, event candidates, display state
    db.query(Vote).filter(Vote.event_id == event_id).delete(synchronize_session=False)
    db.query(EventCandidate).filter(EventCandidate.event_id == event_id).delete(synchronize_session=False)
    db.query(DisplayState).filter(DisplayState.event_id == event_id).delete(synchronize_session=False)

    db.delete(event)
    db.commit()

    return {"message": "Event deleted successfully"}
