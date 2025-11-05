from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import httpx
import os
import uuid
from pathlib import Path
from ..core.database import get_db
from ..core.schemas import CandidateResponse, CandidateCreate, CandidateUpdate
from ..core.dependencies import get_current_user
from ..core.config import settings
from ..models.candidate import Candidate
from ..models.admin import AdminUser

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.post("/sync-from-api")
async def sync_candidates_from_api(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Fetch candidates from external API and sync to database"""
    try:
        all_items = []

        async with httpx.AsyncClient() as client:
            headers = {}
            if settings.EXTERNAL_API_TOKEN:
                headers["Authorization"] = f"Bearer {settings.EXTERNAL_API_TOKEN}"

            # Fetch all pages with pagination
            page = 1
            limit = 100  # Increase limit to reduce API calls

            while True:
                # Add required 'type' parameter and pagination params
                params = {
                    "type": "teacher",
                    "page": page,
                    "limit": limit
                }

                response = await client.get(
                    settings.EXTERNAL_API_URL,
                    headers=headers,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()

                # Check if API response is successful
                if not result.get("success", False):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"External API error: {result.get('error', 'Unknown error')}"
                    )

                # Data is nested in result['data']['items']
                api_data = result.get("data", {})
                items = api_data.get("items", [])

                if not items:
                    # No more items, break the loop
                    break

                all_items.extend(items)

                # Check if we've fetched all items
                total = api_data.get("total", 0)
                if len(all_items) >= total:
                    break

                # Move to next page
                page += 1

        if not all_items:
            return {"message": "No candidates found in API", "count": 0}

        synced_count = 0
        for item in all_items:
            # Check if candidate already exists
            existing = db.query(Candidate).filter(
                Candidate.external_id == item.get("id")
            ).first()

            if existing:
                # Update existing candidate
                existing.full_name = item.get("full_name", existing.full_name)
                existing.image = item.get("image", existing.image)

                # Get position from staffPosition
                staff_position = item.get("staffPosition", {})
                if isinstance(staff_position, dict):
                    position_name = staff_position.get("name")
                    if position_name:
                        existing.which_position = position_name
                        # Maintain legacy column for compatibility
                        existing.position = position_name

                # Get degree from academicDegree
                academic_degree = item.get("academicDegree", {})
                if isinstance(academic_degree, dict):
                    existing.degree = academic_degree.get("name", existing.degree)

                # Convert timestamp to date
                if item.get("birth_date"):
                    try:
                        from datetime import datetime
                        timestamp = item.get("birth_date")
                        existing.birth_date = datetime.fromtimestamp(timestamp).date()
                    except:
                        pass
            else:
                # Create new candidate
                birth_date_obj = None
                if item.get("birth_date"):
                    try:
                        from datetime import datetime
                        timestamp = item.get("birth_date")
                        birth_date_obj = datetime.fromtimestamp(timestamp).date()
                    except:
                        pass

                # Extract position from staffPosition
                staff_position = item.get("staffPosition", {})
                position = staff_position.get("name", "") if isinstance(staff_position, dict) else ""

                # Extract degree from academicDegree
                academic_degree = item.get("academicDegree", {})
                degree = academic_degree.get("name", "") if isinstance(academic_degree, dict) else ""

                candidate = Candidate(
                    full_name=item.get("full_name", "Unknown"),
                    image=item.get("image"),
                    birth_date=birth_date_obj,
                    degree=degree,
                    which_position=position,
                    position=position,
                    from_api=True,
                    external_id=item.get("id")
                )
                db.add(candidate)

            synced_count += 1

        db.commit()
        return {"message": f"Synced {synced_count} candidates", "count": synced_count}

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch from external API: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing candidates: {str(e)}"
        )


@router.post("/manual", response_model=CandidateResponse)
def create_manual_candidate(
    candidate: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Manually add a candidate"""
    candidate_data = candidate.dict()
    which_position = candidate_data.get("which_position")
    if which_position:
        candidate_data["position"] = which_position
    db_candidate = Candidate(**candidate_data, from_api=False)
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate


@router.get("", response_model=List[CandidateResponse])
def get_candidates(db: Session = Depends(get_db)):
    """Get all candidates"""
    candidates = db.query(Candidate).all()
    return candidates


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Get a specific candidate"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: int,
    updates: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Update candidate fields (election_time, description)"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    update_data = updates.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "which_position":
            candidate.which_position = value
            candidate.position = value
        else:
            setattr(candidate, key, value)

    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/upload-image")
async def upload_candidate_image(
    file: UploadFile = File(...),
    current_user: AdminUser = Depends(get_current_user)
):
    """Upload candidate image"""
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    # Create uploads directory if it doesn't exist
    upload_dir = Path("./data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_extension = Path(file.filename or "image.jpg").suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / unique_filename

    # Save file
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # Return full URL path
        full_url = f"{settings.BACKEND_URL}/uploads/{unique_filename}"
        return {
            "image_url": full_url,
            "filename": unique_filename
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )


@router.delete("/{candidate_id}")
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Delete a manually added candidate"""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    # Only allow deletion of manually added candidates
    if candidate.from_api:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete candidates synced from API"
        )

    db.delete(candidate)
    db.commit()
    return {"message": "Candidate deleted successfully"}
