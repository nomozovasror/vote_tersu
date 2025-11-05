from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from ..core.database import get_db
from ..core.schemas import DisplaySetCurrent
from ..core.dependencies import get_current_user
from ..models.event import Event
from ..models.candidate import Candidate
from ..models.display import DisplayState
from ..models.admin import AdminUser

router = APIRouter(prefix="/display", tags=["Display"])


def ensure_utc(dt: datetime | None):
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.post("/{event_id}/set-current")
def set_current_display(
    event_id: int,
    data: DisplaySetCurrent,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Set the current candidate and countdown for display screen (admin only)"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    candidate = db.query(Candidate).filter(Candidate.id == data.candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    # Get or create display state
    display_state = db.query(DisplayState).filter(
        DisplayState.event_id == event_id
    ).first()

    if not display_state:
        display_state = DisplayState(event_id=event_id)
        db.add(display_state)

    now = datetime.now(timezone.utc)

    # Update display state
    display_state.current_candidate_id = data.candidate_id
    display_state.countdown_until = now + timedelta(seconds=data.countdown_sec)

    db.commit()
    db.refresh(display_state)

    return {
        "message": "Display updated",
        "candidate_id": data.candidate_id,
        "countdown_until": display_state.countdown_until
    }


@router.get("/{event_id}/current")
def get_current_display(event_id: int, db: Session = Depends(get_db)):
    """Get current display state (public endpoint)"""
    display_state = db.query(DisplayState).filter(
        DisplayState.event_id == event_id
    ).first()

    if not display_state:
        return {
            "event_id": event_id,
            "current_candidate": None,
            "remaining_ms": 0
        }

    candidate = None
    remaining_ms = 0

    if display_state.current_candidate_id:
        candidate = db.query(Candidate).filter(
            Candidate.id == display_state.current_candidate_id
        ).first()

    if display_state.countdown_until:
        target = ensure_utc(display_state.countdown_until)
        now = datetime.now(timezone.utc)
        remaining = target - now
        remaining_ms = max(0, int(remaining.total_seconds() * 1000))

    return {
        "event_id": event_id,
        "current_candidate": candidate,
        "remaining_ms": remaining_ms
    }


