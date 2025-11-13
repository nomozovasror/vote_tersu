from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel
from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.event import Event, EventCandidate, EventStatus
from ..models.candidate import Candidate
from ..models.display import DisplayState
from ..models.admin import AdminUser
from ..models.vote import Vote
from ..services.websocket_manager import manager

router = APIRouter(prefix="/event-management", tags=["Event Management"])


class CandidateOrderUpdate(BaseModel):
    candidate_id: int
    order: int


class ReorderCandidates(BaseModel):
    candidate_ids: List[int]


class StartTimerRequest(BaseModel):
    duration_sec: Optional[int] = None


@router.get("/{event_id}/candidates")
def get_event_candidates(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get ordered list of candidates for an event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Get candidates ordered with relationship loaded
    event_candidates = db.query(EventCandidate).options(
        joinedload(EventCandidate.candidate)
    ).filter(
        EventCandidate.event_id == event_id
    ).order_by(EventCandidate.order).all()

    return event_candidates


@router.post("/{event_id}/reorder-candidates")
def reorder_event_candidates(
    event_id: int,
    data: ReorderCandidates,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Reorder candidates in an event by providing ordered list of candidate IDs"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Update order based on position in list
    for new_order, candidate_id in enumerate(data.candidate_ids):
        event_candidate = db.query(EventCandidate).filter(
            EventCandidate.event_id == event_id,
            EventCandidate.candidate_id == candidate_id
        ).first()

        if event_candidate:
            event_candidate.order = new_order

    db.commit()
    return {"message": "Candidates reordered successfully"}


@router.post("/{event_id}/set-current-candidate/{candidate_index}")
async def set_current_candidate(
    event_id: int,
    candidate_index: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Set current candidate to a specific index (allows going back to previous candidates)"""
    from ..services.websocket_manager import manager
    from ..routes.websocket import get_current_voting_candidate, build_display_update_payload

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    event_candidates = db.query(EventCandidate).filter(
        EventCandidate.event_id == event_id
    ).order_by(EventCandidate.order).all()

    total_candidates = len(event_candidates)

    if total_candidates == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidates available for this event"
        )

    if candidate_index < 0 or candidate_index >= total_candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid candidate index. Must be between 0 and {total_candidates - 1}"
        )

    # Validate event status - only allow navigation in ACTIVE or FINISHED events
    if event.status not in [EventStatus.active, EventStatus.finished]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only navigate candidates in active or finished events"
        )

    # Set the new current candidate index
    event.current_candidate_index = candidate_index

    # Update event status if needed
    if event.status == EventStatus.finished:
        event.status = EventStatus.active

    # Reset display state until the timer is started again
    display_state = db.query(DisplayState).filter(DisplayState.event_id == event_id).first()
    if display_state:
        display_state.current_candidate_id = None
        display_state.countdown_until = None

    db.commit()
    db.refresh(event)

    # Broadcast new candidate to all connected vote clients
    current_candidate = get_current_voting_candidate(db, event_id)
    await manager.broadcast_vote(event.link, {
        "type": "current_candidate",
        "data": current_candidate
    })

    # Broadcast to display screens
    display_payload = build_display_update_payload(db, event)
    await manager.broadcast_display(event.link, display_payload)

    return {
        "current_index": event.current_candidate_index,
        "total": total_candidates,
        "message": "Current candidate set successfully"
    }


@router.post("/{event_id}/next-candidate")
async def move_to_next_candidate(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Move to next candidate in sequential voting"""
    from ..services.websocket_manager import manager
    from ..routes.websocket import get_current_voting_candidate, build_display_update_payload

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    event_candidates = db.query(EventCandidate).filter(
        EventCandidate.event_id == event_id
    ).order_by(EventCandidate.order).all()

    total_candidates = len(event_candidates)

    if total_candidates == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidates available for this event"
        )

    # Mark current candidate as completed when within bounds
    current_group = None
    if 0 <= event.current_candidate_index < total_candidates:
        current_ec = event_candidates[event.current_candidate_index]
        current_ec.status = "completed"

        # If current candidate is in a group, mark all group members as completed
        if current_ec.candidate_group:
            current_group = current_ec.candidate_group
            for ec in event_candidates:
                if ec.candidate_group == current_group:
                    ec.status = "completed"

    # Helper function to check if a candidate or group has votes
    def has_votes(candidate_id: int, group_name: str = None) -> bool:
        if group_name:
            # Check if any candidate in the group has votes
            group_candidate_ids = [
                ec.candidate_id for ec in event_candidates
                if ec.candidate_group == group_name
            ]
            vote_count = db.query(Vote).filter(
                Vote.event_id == event_id,
                Vote.candidate_id.in_(group_candidate_ids)
            ).count()
            return vote_count > 0
        else:
            # Check if this candidate has votes
            vote_count = db.query(Vote).filter(
                Vote.event_id == event_id,
                Vote.candidate_id == candidate_id
            ).count()
            return vote_count > 0

    # Advance to the next candidate or finish the event
    # Skip candidates that already have votes and candidates in the same group as current
    if event.current_candidate_index < total_candidates - 1:
        event.current_candidate_index += 1

        # Skip all candidates that are in the same group as current OR already have votes
        while event.current_candidate_index < total_candidates:
            next_ec = event_candidates[event.current_candidate_index]

            # If this candidate is in the same group as current, skip it
            if current_group and next_ec.candidate_group == current_group:
                next_ec.status = "completed"
                event.current_candidate_index += 1
                continue

            # Check if this candidate/group already has votes
            if next_ec.candidate_group:
                # Group candidate - check if group has votes
                if has_votes(next_ec.candidate_id, next_ec.candidate_group):
                    # Skip this group
                    for ec in event_candidates:
                        if ec.candidate_group == next_ec.candidate_group:
                            ec.status = "completed"
                    event.current_candidate_index += 1
                    continue
            else:
                # Single candidate - check if has votes
                if has_votes(next_ec.candidate_id):
                    next_ec.status = "completed"
                    event.current_candidate_index += 1
                    continue

            # Found a candidate/group without votes
            next_ec.status = "pending"
            next_ec.timer_started_at = None
            break

        # Check if we've reached the end after skipping
        if event.current_candidate_index >= total_candidates:
            event.status = EventStatus.finished
            event.current_candidate_index = total_candidates
    else:
        event.status = EventStatus.finished
        event.current_candidate_index = total_candidates  # prevent out-of-range lookups

    # Reset display state until the timer is started again
    display_state = db.query(DisplayState).filter(DisplayState.event_id == event_id).first()
    if display_state:
        display_state.current_candidate_id = None
        display_state.countdown_until = None

    db.commit()
    db.refresh(event)

    # Broadcast new candidate to all connected vote clients
    current_candidate = get_current_voting_candidate(db, event_id)
    await manager.broadcast_vote(event.link, {
        "type": "current_candidate",
        "data": current_candidate
    })

    # Broadcast to display screens
    display_payload = build_display_update_payload(db, event)
    await manager.broadcast_display(event.link, display_payload)

    return {
        "current_index": event.current_candidate_index,
        "total": total_candidates,
        "completed": event.current_candidate_index >= total_candidates - 1
    }


@router.post("/{event_id}/start-timer")
async def start_candidate_timer(
    event_id: int,
    data: Optional[StartTimerRequest] = None,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Start or restart the countdown for the current candidate"""
    from ..services.websocket_manager import manager
    from ..routes.websocket import (
        get_current_voting_candidate,
        get_candidate_vote_tally,
        build_display_update_payload,
    )

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if event.status != EventStatus.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event must be active to start the timer"
        )

    event_candidates = db.query(EventCandidate).filter(
        EventCandidate.event_id == event_id
    ).order_by(EventCandidate.order).all()

    if not event_candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event has no candidates"
        )

    if event.current_candidate_index >= len(event_candidates):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All candidates have already completed voting"
        )

    current_ec = event_candidates[event.current_candidate_index]

    request = data or StartTimerRequest()
    duration_sec = request.duration_sec or event.duration_sec
    if duration_sec <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duration must be positive"
        )

    now = datetime.now(timezone.utc)
    current_ec.timer_started_at = now
    current_ec.status = "active"

    # Ensure previous candidates are marked as completed
    for idx, ec in enumerate(event_candidates):
        if idx < event.current_candidate_index:
            ec.status = "completed"
        elif idx > event.current_candidate_index and ec.status != "pending":
            ec.status = "pending"

    # Update display state countdown
    display_state = db.query(DisplayState).filter(DisplayState.event_id == event_id).first()
    if not display_state:
        display_state = DisplayState(event_id=event_id)
        db.add(display_state)
    display_state.current_candidate_id = current_ec.candidate_id
    display_state.countdown_until = now + timedelta(seconds=duration_sec)

    db.commit()
    db.refresh(event)

    current_candidate = get_current_voting_candidate(db, event_id)
    await manager.broadcast_vote(event.link, {
        "type": "current_candidate",
        "data": current_candidate
    })

    if current_candidate and current_candidate.get("candidate"):
        tally = get_candidate_vote_tally(db, event.id, current_candidate["candidate"]["id"])
        await manager.broadcast_vote(event.link, {
            "type": "tally_update",
            "data": tally
        })

    display_payload = build_display_update_payload(db, event)
    await manager.broadcast_display(event.link, display_payload)

    return {
        "message": "Timer started",
        "duration_sec": duration_sec,
        "current_candidate": current_candidate
    }


@router.get("/{event_id}/current-candidate")
def get_current_candidate(event_id: int, db: Session = Depends(get_db)):
    """Get current candidate for sequential voting (public)"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    from ..routes.websocket import get_current_voting_candidate

    return get_current_voting_candidate(db, event_id)


@router.post("/{event_id}/add-candidate/{candidate_id}")
def add_candidate_to_event(
    event_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Add a candidate to event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Check if candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    # Check if already added
    existing = db.query(EventCandidate).filter(
        EventCandidate.event_id == event_id,
        EventCandidate.candidate_id == candidate_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate already added to this event"
        )

    # Get max order
    max_order = db.query(EventCandidate).filter(
        EventCandidate.event_id == event_id
    ).count()

    # Add candidate
    event_candidate = EventCandidate(
        event_id=event_id,
        candidate_id=candidate_id,
        order=max_order,
        status="pending"
    )
    db.add(event_candidate)
    db.commit()
    db.refresh(event_candidate)

    return {"message": "Candidate added successfully", "event_candidate": event_candidate}


@router.delete("/{event_id}/remove-candidate/{candidate_id}")
def remove_candidate_from_event(
    event_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Remove a candidate from event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Find event candidate
    event_candidate = db.query(EventCandidate).filter(
        EventCandidate.event_id == event_id,
        EventCandidate.candidate_id == candidate_id
    ).first()

    if not event_candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not in this event"
        )

    # Get the order of removed candidate
    removed_order = event_candidate.order

    # Delete
    db.delete(event_candidate)

    # Reorder remaining candidates
    remaining = db.query(EventCandidate).filter(
        EventCandidate.event_id == event_id,
        EventCandidate.order > removed_order
    ).all()

    for ec in remaining:
        ec.order -= 1

    db.commit()

    return {"message": "Candidate removed successfully"}


class SetGroupRequest(BaseModel):
    event_candidate_ids: List[int]
    group_name: str


@router.post("/{event_id}/set-group")
def set_candidate_group(
    event_id: int,
    request: SetGroupRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Assign a group to multiple candidates"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    if len(request.event_candidate_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group must have at least 2 candidates"
        )

    if len(request.event_candidate_ids) > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group can have maximum 4 candidates"
        )

    # Update group for all specified candidates
    for ec_id in request.event_candidate_ids:
        event_candidate = db.query(EventCandidate).filter(
            EventCandidate.id == ec_id,
            EventCandidate.event_id == event_id
        ).first()

        if not event_candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event candidate {ec_id} not found"
            )

        event_candidate.candidate_group = request.group_name

    db.commit()

    return {"message": f"Group '{request.group_name}' assigned to {len(request.event_candidate_ids)} candidates"}


@router.post("/{event_id}/unset-group")
def unset_candidate_group(
    event_id: int,
    event_candidate_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Remove group assignment from a candidate"""
    event_candidate = db.query(EventCandidate).filter(
        EventCandidate.id == event_candidate_id,
        EventCandidate.event_id == event_id
    ).first()

    if not event_candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event candidate not found"
        )

    event_candidate.candidate_group = None
    db.commit()

    return {"message": "Group assignment removed"}


@router.delete("/{event_id}/candidate/{candidate_id}/votes")
async def clear_candidate_votes(
    event_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Clear all votes for a specific candidate in an event"""
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Verify candidate exists in this event
    event_candidate = db.query(EventCandidate).filter(
        EventCandidate.event_id == event_id,
        EventCandidate.candidate_id == candidate_id
    ).first()

    if not event_candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found in this event"
        )

    # Delete all votes for this candidate in this event
    deleted_count = db.query(Vote).filter(
        Vote.event_id == event_id,
        Vote.candidate_id == candidate_id
    ).delete(synchronize_session=False)

    # Reset candidate status to pending and participant count
    event_candidate.status = "pending"
    event_candidate.timer_started_at = None
    event_candidate.participant_count = 0

    db.commit()

    # Broadcast votes cleared event to reset hasVoted state for this candidate
    await manager.broadcast_vote(event.link, {
        "type": "votes_cleared",
        "candidate_id": candidate_id
    })

    # Broadcast updated tally (now all zeros) to update vote counts in real-time
    from ..routes.websocket import get_candidate_vote_tally
    tally = get_candidate_vote_tally(db, event_id, candidate_id)
    await manager.broadcast_vote(event.link, {
        "type": "tally_update",
        "data": tally
    })

    return {
        "message": f"Cleared {deleted_count} votes for candidate",
        "deleted_count": deleted_count
    }


@router.delete("/{event_id}/group/{group_name}/votes")
async def clear_group_votes(
    event_id: int,
    group_name: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Clear all votes for all candidates in a group"""
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )

    # Get all candidates in this group
    group_candidates = db.query(EventCandidate).filter(
        EventCandidate.event_id == event_id,
        EventCandidate.candidate_group == group_name
    ).all()

    if not group_candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found in this event"
        )

    # Get all candidate IDs in the group
    candidate_ids = [ec.candidate_id for ec in group_candidates]

    # Delete all votes for these candidates in this event
    deleted_count = db.query(Vote).filter(
        Vote.event_id == event_id,
        Vote.candidate_id.in_(candidate_ids)
    ).delete(synchronize_session=False)

    # Reset all group candidates' status to pending and participant count
    for ec in group_candidates:
        ec.status = "pending"
        ec.timer_started_at = None
        ec.participant_count = 0

    db.commit()

    # Broadcast votes cleared event to reset hasVoted state for group candidates
    await manager.broadcast_vote(event.link, {
        "type": "votes_cleared",
        "candidate_ids": candidate_ids,
        "group_name": group_name
    })

    # Broadcast updated tally for each candidate in the group
    from ..routes.websocket import get_candidate_vote_tally
    for candidate_id in candidate_ids:
        tally = get_candidate_vote_tally(db, event_id, candidate_id)
        await manager.broadcast_vote(event.link, {
            "type": "tally_update",
            "data": tally
        })

    return {
        "message": f"Cleared {deleted_count} votes for group '{group_name}'",
        "deleted_count": deleted_count,
        "candidates_affected": len(candidate_ids)
    }
