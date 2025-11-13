from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from ..core.database import get_db
from ..models.event import Event, EventCandidate, EventStatus
from ..models.vote import Vote
from ..models.candidate import Candidate
from ..services.websocket_manager import manager
from ..services.event_results import calculate_event_results

router = APIRouter(tags=["WebSocket"])


def ensure_utc(dt: datetime | None):
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso_utc(dt: datetime | None):
    dt = ensure_utc(dt)
    if not dt:
        return None
    return dt.isoformat().replace("+00:00", "Z")


def candidate_position_value(candidate: Candidate | None) -> str | None:
    """Return the effective position for a candidate."""
    if not candidate:
        return None
    return candidate.which_position or candidate.position


def build_related_candidates(event_candidates: list[EventCandidate], target: Candidate | None, target_event_candidate: EventCandidate | None):
    """Collect candidates that are in the same group (candidate_group)."""
    related = []

    # Only group-based voting is supported
    if target_event_candidate and target_event_candidate.candidate_group:
        for ec in event_candidates:
            if ec.candidate_group == target_event_candidate.candidate_group:
                candidate = ec.candidate
                if not candidate:
                    continue

                related.append({
                    "id": candidate.id,
                    "full_name": candidate.full_name,
                    "image": candidate.image,
                    "which_position": candidate_position_value(candidate),
                    "degree": candidate.degree,
                })
        return related

    # No group = single candidate voting (no position-based fallback)
    return []


def compute_timer_info(event: Event, event_candidate: EventCandidate):
    """Calculate timer metadata for the current candidate."""
    duration_sec = event.duration_sec or 0
    timer_started_at = ensure_utc(event_candidate.timer_started_at)
    ends_at = None
    remaining_ms = 0
    timer_running = False

    if timer_started_at:
        ends_at = timer_started_at + timedelta(seconds=duration_sec)
        now = datetime.now(timezone.utc)
        remaining = (ends_at - now).total_seconds()
        if remaining > 0:
            timer_running = True
            remaining_ms = int(remaining * 1000)
        else:
            remaining_ms = 0

    return {
        "running": timer_running,
        "remaining_ms": remaining_ms,
        "duration_sec": duration_sec,
        "started_at": iso_utc(timer_started_at),
        "ends_at": iso_utc(ends_at),
        "ends_at_ts": int(ends_at.timestamp() * 1000) if ends_at else None,
    }


def build_display_update_payload(db: Session, event: Event):
    """Aggregate display payload so it can be reused across HTTP + WS contexts."""
    base_payload = {
        "type": "display_update",
        "candidate": None,
        "current_candidate": None,
        "related_candidates": [],
        "remaining_ms": 0,
        "timer_running": False,
        "timer": {
            "running": False,
            "remaining_ms": 0,
            "duration_sec": event.duration_sec if event else 0,
            "started_at": None,
            "ends_at": None,
            "ends_at_ts": None,
        },
        "vote_results": {"yes": 0, "no": 0, "neutral": 0, "total": 0},
        "event_status": event.status.value if event else None,
        "event_completed": False,
        "final_results": [],
        "total_votes": 0,
    }

    if not event:
        return base_payload

    event_candidates = db.query(EventCandidate).options(
        joinedload(EventCandidate.candidate)
    ).filter(
        EventCandidate.event_id == event.id
    ).order_by(EventCandidate.order).all()

    total_candidates = len(event_candidates)
    if total_candidates == 0:
        base_payload["event_completed"] = True
        base_payload["final_results"], base_payload["total_votes"] = calculate_event_results(db, event.id)
        return base_payload

    if 0 <= event.current_candidate_index < total_candidates:
        current_ec = event_candidates[event.current_candidate_index]
        candidate = current_ec.candidate
        timer = compute_timer_info(event, current_ec)
        vote_results = get_candidate_vote_tally(db, event.id, candidate.id) if candidate else {"yes": 0, "no": 0, "neutral": 0, "total": 0}

        candidate_payload = {
            "id": candidate.id,
            "full_name": candidate.full_name,
            "image": candidate.image,
            "which_position": candidate_position_value(candidate),
            "degree": candidate.degree,
        } if candidate else None

        related_candidates = build_related_candidates(event_candidates, candidate, current_ec)

        # If grouped, get vote results for each candidate in the group
        group_results = []
        if current_ec.candidate_group and len(related_candidates) > 1:
            for rc in related_candidates:
                rc_votes = get_candidate_vote_tally(db, event.id, rc["id"])
                group_results.append({
                    "candidate": rc,
                    "votes": rc_votes
                })

        base_payload.update({
            "candidate": candidate_payload,
            "current_candidate": candidate_payload,
            "related_candidates": related_candidates,
            "group_results": group_results,
            "remaining_ms": timer["remaining_ms"],
            "timer_running": timer["running"],
            "timer": timer,
            "vote_results": vote_results,
        })

    completed = (
        event.status in (EventStatus.finished, EventStatus.archived)
        or event.current_candidate_index >= total_candidates
    )

    if completed:
        results, total_votes = calculate_event_results(db, event.id)

        # Format results for DisplayPage (uses 'votes' and 'percent' fields)
        display_results = []
        for result in results:
            display_results.append({
                "candidate_id": result["candidate_id"],
                "full_name": result["full_name"],
                "image": result["image"],
                "which_position": result["which_position"],
                "election_time": result["election_time"],
                "description": result["description"],
                "votes": result["yes_votes"],
                "percent": result["yes_percent"]
            })

        base_payload["event_completed"] = True
        base_payload["final_results"] = display_results
        base_payload["total_votes"] = total_votes

    return base_payload


@router.websocket("/ws/vote/{link}")
async def websocket_vote_endpoint(websocket: WebSocket, link: str):
    """WebSocket for sequential yes/no/neutral voting"""
    db = next(get_db())

    try:
        db.expire_all()
        # Verify event exists
        event = db.query(Event).filter(Event.link == link).first()
        if not event:
            await websocket.close(code=4004, reason="Event not found")
            return

        # Allow connections for active and finished events
        # (finished events need WebSocket for completion notifications)
        if event.status not in (EventStatus.active, EventStatus.finished):
            await websocket.close(code=4003, reason="Event is not available")
            return

        await manager.connect_vote(websocket, link)

        # Send current candidate info
        db.expire_all()
        current_candidate = get_current_voting_candidate(db, event.id)
        await websocket.send_json({
            "type": "current_candidate",
            "data": current_candidate
        })

        # Send initial tally
        if current_candidate and current_candidate.get("candidate"):
            tally = get_candidate_vote_tally(db, event.id, current_candidate["candidate"]["id"])
            await websocket.send_json({
                "type": "tally_update",
                "data": tally
            })

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "cast_vote":
                db.expire_all()
                vote_type = data.get("vote_type")  # 'yes', 'no', 'neutral'
                nonce = data.get("nonce")
                device_id = data.get("device_id")  # Device fingerprint for multi-device voting

                if not vote_type or not nonce:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing vote_type or nonce"
                    })
                    continue

                if vote_type not in ['yes', 'no', 'neutral']:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid vote_type. Must be 'yes', 'no', or 'neutral'"
                    })
                    continue

                # Get client IP
                client_ip = websocket.client.host if websocket.client else "unknown"

                # Get current candidate
                current_cand = get_current_voting_candidate(db, event.id)
                if not current_cand or not current_cand.get("candidate"):
                    await websocket.send_json({
                        "type": "error",
                        "message": "No active candidate for voting"
                    })
                    continue

                timer_info = current_cand.get("timer") or {}
                if not timer_info.get("running"):
                    await websocket.send_json({
                        "type": "error",
                        "message": "Voting has not started for this candidate yet"
                    })
                    continue

                if timer_info.get("remaining_ms", 0) <= 0:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Voting time has ended for this candidate"
                    })
                    continue

                # Get candidate_id from data (for grouped voting) or default to current candidate
                candidate_id = data.get("candidate_id", current_cand["candidate"]["id"])

                # For grouped voting, find the event_candidate_id for the selected candidate
                event_candidate = db.query(EventCandidate).filter(
                    EventCandidate.event_id == event.id,
                    EventCandidate.candidate_id == candidate_id
                ).first()

                if not event_candidate:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Selected candidate not found in this event"
                    })
                    continue

                event_candidate_id = event_candidate.id

                # Check if already voted for this candidate
                # Use both IP address AND device_id for better duplicate detection
                if device_id:
                    # If device_id is provided, check by IP + device_id combination
                    existing_vote = db.query(Vote).filter(
                        Vote.event_id == event.id,
                        Vote.candidate_id == candidate_id,
                        Vote.ip_address == client_ip,
                        Vote.device_id == device_id
                    ).first()
                else:
                    # Fallback to IP-only check (legacy behavior)
                    existing_vote = db.query(Vote).filter(
                        Vote.event_id == event.id,
                        Vote.candidate_id == candidate_id,
                        Vote.ip_address == client_ip
                    ).first()

                if existing_vote:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Siz allaqachon ovoz bergansiz (bu qurilmadan)"
                    })
                    continue

                candidate_record = db.query(Candidate).filter(Candidate.id == candidate_id).first()

                # Record vote
                vote = Vote(
                    event_id=event.id,
                    event_candidate_id=event_candidate_id,
                    candidate_id=candidate_id,
                    ip_address=client_ip,
                    device_id=device_id,
                    nonce=nonce,
                    vote_type=vote_type,
                    timestamp=datetime.utcnow()
                )
                db.add(vote)

                # Update participant count for this candidate
                # Count unique participants (by IP+device_id combination)
                participant_event_candidate = db.query(EventCandidate).filter(
                    EventCandidate.event_id == event.id,
                    EventCandidate.candidate_id == candidate_id
                ).first()

                if participant_event_candidate:
                    # Count unique participants for this candidate
                    # Use func.count(func.distinct()) for accurate counting
                    from sqlalchemy import func
                    if device_id:
                        # Count unique (ip_address, device_id) pairs
                        unique_participants = db.query(
                            func.count(func.distinct(Vote.ip_address + '_' + func.coalesce(Vote.device_id, '')))
                        ).filter(
                            Vote.event_id == event.id,
                            Vote.candidate_id == candidate_id
                        ).scalar() or 0
                    else:
                        # Count unique ip_address
                        unique_participants = db.query(
                            func.count(func.distinct(Vote.ip_address))
                        ).filter(
                            Vote.event_id == event.id,
                            Vote.candidate_id == candidate_id
                        ).scalar() or 0

                    participant_event_candidate.participant_count = unique_participants

                auto_voted_candidate_ids: list[int] = []

                # Auto-vote logic for grouped candidates
                if candidate_record:
                    # Get current event_candidate to check for group
                    current_event_candidate = db.query(EventCandidate).filter(
                        EventCandidate.event_id == event.id,
                        EventCandidate.candidate_id == candidate_id
                    ).first()

                    # Only auto-vote for grouped candidates
                    if current_event_candidate and current_event_candidate.candidate_group:
                        # Get all candidates in the same group
                        related_event_candidates = db.query(EventCandidate).options(
                            joinedload(EventCandidate.candidate)
                        ).filter(
                            EventCandidate.event_id == event.id,
                            EventCandidate.candidate_group == current_event_candidate.candidate_group
                        ).all()

                        # Determine auto-vote type based on user's vote
                        if vote_type == "yes":
                            # If "yes" for one candidate, others get "no"
                            auto_vote_type = "no"
                        elif vote_type == "neutral":
                            # If "neutral", all other candidates also get "neutral"
                            auto_vote_type = "neutral"
                        else:
                            # If "no", no auto-voting needed
                            auto_vote_type = None

                        # Auto-vote for other candidates in the group
                        if auto_vote_type:
                            for related in related_event_candidates:
                                related_candidate = related.candidate
                                if not related_candidate or related_candidate.id == candidate_id:
                                    continue

                                # Check with device_id if available
                                if device_id:
                                    existing_related_vote = db.query(Vote).filter(
                                        Vote.event_id == event.id,
                                        Vote.candidate_id == related_candidate.id,
                                        Vote.ip_address == client_ip,
                                        Vote.device_id == device_id
                                    ).first()
                                else:
                                    existing_related_vote = db.query(Vote).filter(
                                        Vote.event_id == event.id,
                                        Vote.candidate_id == related_candidate.id,
                                        Vote.ip_address == client_ip
                                    ).first()

                                if existing_related_vote:
                                    continue

                                auto_vote = Vote(
                                    event_id=event.id,
                                    event_candidate_id=related.id,
                                    candidate_id=related.candidate_id,
                                    ip_address=client_ip,
                                    device_id=device_id,
                                    nonce=f"{nonce}-{auto_vote_type}-{related.candidate_id}",
                                    vote_type=auto_vote_type,
                                    timestamp=datetime.utcnow()
                                )
                                db.add(auto_vote)
                                auto_voted_candidate_ids.append(related.candidate_id)

                                # Update participant count for auto-voted candidates
                                from sqlalchemy import func
                                if device_id:
                                    unique_participants = db.query(
                                        func.count(func.distinct(Vote.ip_address + '_' + func.coalesce(Vote.device_id, '')))
                                    ).filter(
                                        Vote.event_id == event.id,
                                        Vote.candidate_id == related.candidate_id
                                    ).scalar() or 0
                                else:
                                    unique_participants = db.query(
                                        func.count(func.distinct(Vote.ip_address))
                                    ).filter(
                                        Vote.event_id == event.id,
                                        Vote.candidate_id == related.candidate_id
                                    ).scalar() or 0

                                related.participant_count = unique_participants

                db.commit()

                db.expire_all()

                # Send confirmation
                await websocket.send_json({
                    "type": "vote_confirmed",
                    "vote_type": vote_type,
                    "candidate_id": candidate_id,
                    "which_position": candidate_position_value(candidate_record) if candidate_record else None,
                    "auto_voted_candidates": auto_voted_candidate_ids
                })

                # Broadcast updated tally for current candidate
                tally = get_candidate_vote_tally(db, event.id, candidate_id)
                await manager.broadcast_vote(link, {
                    "type": "tally_update",
                    "data": tally
                })

                # Broadcast current candidate state to all voters
                current_candidate = get_current_voting_candidate(db, event.id)
                await manager.broadcast_vote(link, {
                    "type": "current_candidate",
                    "data": current_candidate
                })

                display_payload = build_display_update_payload(db, event)
                if display_payload:
                    await manager.broadcast_display(link, display_payload)

    except WebSocketDisconnect:
        manager.disconnect_vote(websocket, link)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect_vote(websocket, link)
    finally:
        db.close()


@router.websocket("/ws/display/{link}")
async def websocket_display_endpoint(websocket: WebSocket, link: str):
    """WebSocket for display screen with pie chart results"""
    db = next(get_db())

    try:
        event = db.query(Event).filter(Event.link == link).first()
        if not event:
            await websocket.close(code=4004, reason="Event not found")
            return

        await manager.connect_display(websocket, link)
        event_id = event.id

        # Send initial state
        await send_display_update(websocket, db, event_id)

        while True:
            # Wait for client message (keep-alive)
            try:
                message = await websocket.receive_text()
                # Client requested update
                if message == "update":
                    await send_display_update(websocket, db, event_id)
            except:
                break

    except WebSocketDisconnect:
        manager.disconnect_display(websocket, link)
    except Exception as e:
        print(f"Display WebSocket error: {e}")
        manager.disconnect_display(websocket, link)
    finally:
        db.close()


async def send_display_update(websocket: WebSocket, db: Session, event_id: int):
    """Send current display state to display screen"""
    db.expire_all()
    event = db.query(Event).filter(Event.id == event_id).first()
    payload = build_display_update_payload(db, event)
    if payload:
        await websocket.send_json(payload)


def get_current_voting_candidate(db: Session, event_id: int):
    """Get current candidate for sequential voting"""
    db.expire_all()
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return None

    timer_stub = {
        "running": False,
        "remaining_ms": 0,
        "duration_sec": event.duration_sec,
        "started_at": None,
        "ends_at": None,
        "ends_at_ts": None,
    }

    # Get all event candidates ordered
    event_candidates = db.query(EventCandidate).options(
        joinedload(EventCandidate.candidate)
    ).filter(
        EventCandidate.event_id == event_id
    ).order_by(EventCandidate.order).all()

    if not event_candidates:
        return {
            "candidate": None,
            "event_candidate_id": None,
            "index": 0,
            "total": 0,
            "timer": timer_stub,
            "related_candidates": []
        }

    if event.current_candidate_index >= len(event_candidates):
        return {
            "candidate": None,
            "event_candidate_id": None,
            "index": event.current_candidate_index,
            "total": len(event_candidates),
            "timer": timer_stub,
            "related_candidates": []
        }

    current_ec = event_candidates[event.current_candidate_index]
    timer_info = compute_timer_info(event, current_ec)

    return {
        "candidate": {
            "id": current_ec.candidate.id,
            "full_name": current_ec.candidate.full_name,
            "image": current_ec.candidate.image,
            "which_position": candidate_position_value(current_ec.candidate),
            "degree": current_ec.candidate.degree
        },
        "event_candidate_id": current_ec.id,
        "index": event.current_candidate_index,
        "total": len(event_candidates),
        "timer": timer_info,
        "related_candidates": build_related_candidates(event_candidates, current_ec.candidate, current_ec),
    }


def get_candidate_vote_tally(db: Session, event_id: int, candidate_id: int):
    """Get vote tally for a candidate (yes/no/neutral)"""
    votes = db.query(
        Vote.vote_type,
        func.count(Vote.id).label('count')
    ).filter(
        Vote.event_id == event_id,
        Vote.candidate_id == candidate_id
    ).group_by(Vote.vote_type).all()

    result = {"yes": 0, "no": 0, "neutral": 0, "total": 0}

    for vote_type, count in votes:
        result[vote_type] = count
        result["total"] += count

    return result
