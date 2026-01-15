"""
Scheduled calls API routes
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from db import crud

router = APIRouter()


# === Pydantic Models ===

class ScheduledCallCreate(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15)
    scheduled_time: datetime
    prompt_id: Optional[int] = None
    notes: Optional[str] = None


class ScheduledCallResponse(BaseModel):
    id: int
    phone_number: str
    prompt_id: Optional[int]
    scheduled_time: str
    status: str
    call_id: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# === Routes ===

@router.get("", response_model=List[ScheduledCallResponse])
async def list_scheduled_calls(
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """List scheduled calls with optional filters"""
    scheduled_calls = await crud.get_scheduled_calls(
        db,
        status=status,
        from_date=from_date,
        to_date=to_date,
    )
    return [ScheduledCallResponse(**s.to_dict()) for s in scheduled_calls]


@router.post("", response_model=ScheduledCallResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_call(
    data: ScheduledCallCreate,
    db: AsyncSession = Depends(get_db)
):
    """Schedule a new call"""
    # Validate scheduled_time is in the future
    if data.scheduled_time <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must be in the future"
        )

    # Validate prompt exists if provided
    if data.prompt_id:
        prompt = await crud.get_prompt(db, data.prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )

    scheduled = await crud.create_scheduled_call(
        db,
        phone_number=data.phone_number,
        scheduled_time=data.scheduled_time,
        prompt_id=data.prompt_id,
        notes=data.notes,
    )
    await db.commit()

    return ScheduledCallResponse(**scheduled.to_dict())


@router.get("/{schedule_id}", response_model=ScheduledCallResponse)
async def get_scheduled_call(
    schedule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific scheduled call"""
    scheduled = await crud.get_scheduled_call(db, schedule_id)
    if not scheduled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled call not found"
        )

    return ScheduledCallResponse(**scheduled.to_dict())


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_scheduled_call(
    schedule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a scheduled call (only if pending)"""
    scheduled = await crud.get_scheduled_call(db, schedule_id)
    if not scheduled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled call not found"
        )

    if scheduled.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a call with status '{scheduled.status}'"
        )

    await crud.update_scheduled_call(db, schedule_id, status="cancelled")
    await db.commit()

    return None
