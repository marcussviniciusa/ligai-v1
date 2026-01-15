"""
Campaigns API routes
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from db import crud
from services import campaign_service

router = APIRouter()


# === Pydantic Models ===

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    prompt_id: Optional[int] = None
    max_concurrent: int = Field(default=5, ge=1, le=50)


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    prompt_id: Optional[int] = None
    max_concurrent: Optional[int] = Field(None, ge=1, le=50)


class ContactCreate(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15)
    name: Optional[str] = None


class ContactsImport(BaseModel):
    contacts: List[ContactCreate]


class CampaignResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    prompt_id: Optional[int]
    status: str
    max_concurrent: int
    total_contacts: int
    completed_contacts: int
    failed_contacts: int
    created_at: str
    updated_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class ContactResponse(BaseModel):
    id: int
    phone_number: str
    name: Optional[str]
    status: str
    call_id: Optional[str]
    attempts: int
    last_attempt_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class CampaignStats(BaseModel):
    total: int
    pending: int
    calling: int
    completed: int
    failed: int
    success_rate: float


# === Routes ===

@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all campaigns"""
    campaigns = await crud.get_campaigns(db, status=status)
    return [CampaignResponse(**c.to_dict()) for c in campaigns]


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new campaign"""
    # Validate prompt exists if provided
    if data.prompt_id:
        prompt = await crud.get_prompt(db, data.prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )

    campaign = await crud.create_campaign(
        db,
        name=data.name,
        description=data.description,
        prompt_id=data.prompt_id,
        max_concurrent=data.max_concurrent,
    )
    await db.commit()

    return CampaignResponse(**campaign.to_dict())


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get campaign details"""
    campaign = await crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    return CampaignResponse(**campaign.to_dict())


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update campaign settings"""
    campaign = await crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    if campaign.status not in ("pending", "paused"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update pending or paused campaigns"
        )

    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.prompt_id is not None:
        update_data["prompt_id"] = data.prompt_id
    if data.max_concurrent is not None:
        update_data["max_concurrent"] = data.max_concurrent

    campaign = await crud.update_campaign(db, campaign_id, **update_data)
    await db.commit()

    return CampaignResponse(**campaign.to_dict())


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a campaign (only if pending)"""
    campaign = await crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    if campaign.status not in ("pending", "completed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete pending or completed campaigns"
        )

    deleted = await crud.delete_campaign(db, campaign_id)
    await db.commit()

    return None


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Start or resume a campaign"""
    campaign = await crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    # Check if campaign has contacts
    total = await crud.count_campaign_contacts(db, campaign_id)
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start campaign with no contacts"
        )

    success = await campaign_service.start_campaign(campaign_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start campaign. It may already be running or have an invalid status."
        )

    return {"success": True, "message": "Campaign started"}


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Pause a running campaign"""
    campaign = await crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    success = await campaign_service.pause_campaign(campaign_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign is not running"
        )

    return {"success": True, "message": "Campaign paused"}


@router.get("/{campaign_id}/stats", response_model=CampaignStats)
async def get_campaign_stats(
    campaign_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get campaign statistics"""
    campaign = await crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    stats = await crud.get_campaign_contact_stats(db, campaign_id)
    return CampaignStats(**stats)


@router.get("/{campaign_id}/contacts", response_model=List[ContactResponse])
async def list_campaign_contacts(
    campaign_id: int,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """List contacts in a campaign"""
    campaign = await crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    skip = (page - 1) * per_page
    contacts = await crud.get_campaign_contacts(
        db, campaign_id,
        status=status,
        skip=skip,
        limit=per_page
    )

    return [ContactResponse(**c.to_dict()) for c in contacts]


@router.post("/{campaign_id}/contacts")
async def import_contacts_json(
    campaign_id: int,
    data: ContactsImport,
    db: AsyncSession = Depends(get_db)
):
    """Import contacts via JSON"""
    campaign = await crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    if campaign.status not in ("pending", "paused"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add contacts to pending or paused campaigns"
        )

    contacts = [{"phone_number": c.phone_number, "name": c.name} for c in data.contacts]
    count = await crud.create_campaign_contacts_bulk(db, campaign_id, contacts)

    # Update total
    await crud.update_campaign(
        db, campaign_id,
        total_contacts=campaign.total_contacts + count
    )
    await db.commit()

    return {"success": True, "imported": count}


@router.post("/{campaign_id}/contacts/csv")
async def import_contacts_csv(
    campaign_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Import contacts via CSV file"""
    campaign = await crud.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    if campaign.status not in ("pending", "paused"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only add contacts to pending or paused campaigns"
        )

    # Read and parse CSV
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )

    contacts = campaign_service.parse_csv_contacts(csv_content)

    if not contacts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid contacts found in CSV"
        )

    count = await crud.create_campaign_contacts_bulk(db, campaign_id, contacts)

    # Update total
    await crud.update_campaign(
        db, campaign_id,
        total_contacts=campaign.total_contacts + count
    )
    await db.commit()

    return {"success": True, "imported": count}
