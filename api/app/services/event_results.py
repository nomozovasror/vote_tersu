from typing import List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case

from ..models.event import EventCandidate
from ..models.vote import Vote


def calculate_event_results(db: Session, event_id: int) -> Tuple[List[dict], int]:
    """Aggregate total votes per candidate for an event with yes/no/neutral breakdown."""
    # Load all candidates participating in the event
    event_candidates = db.query(EventCandidate).options(
        joinedload(EventCandidate.candidate)
    ).filter(
        EventCandidate.event_id == event_id
    ).order_by(EventCandidate.order).all()

    # Get vote breakdown by type
    vote_breakdown = db.query(
        Vote.candidate_id,
        func.sum(case((Vote.vote_type == 'yes', 1), else_=0)).label("yes_votes"),
        func.sum(case((Vote.vote_type == 'no', 1), else_=0)).label("no_votes"),
        func.sum(case((Vote.vote_type == 'neutral', 1), else_=0)).label("neutral_votes"),
        func.count(Vote.id).label("total_votes")
    ).filter(
        Vote.event_id == event_id
    ).group_by(
        Vote.candidate_id
    ).all()

    # Create a map for easy lookup
    vote_map = {
        row.candidate_id: {
            "yes": row.yes_votes or 0,
            "no": row.no_votes or 0,
            "neutral": row.neutral_votes or 0,
            "total": row.total_votes or 0
        }
        for row in vote_breakdown
    }

    # Get unique voters count (by IP + device_id combination)
    # Count distinct (ip_address, device_id) pairs
    # For votes without device_id, we still count them by IP
    unique_voters_subquery = db.query(
        Vote.ip_address,
        Vote.device_id
    ).filter(
        Vote.event_id == event_id
    ).distinct().subquery()

    unique_voters = db.query(func.count()).select_from(unique_voters_subquery).scalar() or 0

    results = []
    for idx, event_candidate in enumerate(event_candidates, start=1):
        candidate = event_candidate.candidate
        if not candidate:
            continue

        vote_data = vote_map.get(candidate.id, {"yes": 0, "no": 0, "neutral": 0, "total": 0})

        yes_votes = vote_data["yes"]
        no_votes = vote_data["no"]
        neutral_votes = vote_data["neutral"]
        total_votes = vote_data["total"]

        # Calculate percentages based on total votes for THIS candidate
        # Example: 4 total votes: 2 yes (50%), 1 no (25%), 1 neutral (25%)
        yes_percent = (yes_votes / total_votes * 100) if total_votes > 0 else 0
        no_percent = (no_votes / total_votes * 100) if total_votes > 0 else 0
        neutral_percent = (neutral_votes / total_votes * 100) if total_votes > 0 else 0

        # Determine result - passes if yes votes > 50% of THIS candidate's votes
        result = "O'tdi" if yes_percent > 50 else "O'tmadi"

        results.append({
            "row_number": idx,
            "candidate_id": candidate.id,
            "full_name": candidate.full_name,
            "image": candidate.image,
            "which_position": candidate.which_position or candidate.position or "",
            "description": candidate.description,
            "election_time": candidate.election_time,
            "yes_votes": yes_votes,
            "yes_percent": round(yes_percent, 1),
            "no_votes": no_votes,
            "no_percent": round(no_percent, 1),
            "neutral_votes": neutral_votes,
            "neutral_percent": round(neutral_percent, 1),
            "total_votes": total_votes,
            "result": result,
            # For frontend compatibility (VoteTally interface)
            "votes": total_votes,
            "percent": round(yes_percent, 1)
        })

    return results, unique_voters
