"""
Webhooks API routes
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from db import crud
from services.webhook_service import SUPPORTED_EVENTS, send_test_webhook

router = APIRouter()


# === Pydantic Models ===

class WebhookConfigCreate(BaseModel):
    url: str = Field(..., min_length=10, max_length=500)
    events: List[str] = Field(..., min_items=1)
    secret: Optional[str] = Field(None, max_length=100)


class WebhookConfigUpdate(BaseModel):
    url: Optional[str] = Field(None, min_length=10, max_length=500)
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    secret: Optional[str] = Field(None, max_length=100)


class WebhookConfigResponse(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class WebhookLogResponse(BaseModel):
    id: int
    event_type: str
    status_code: Optional[int]
    success: bool
    attempt: int
    error_message: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


# === Routes ===

@router.get("/events")
async def list_supported_events():
    """List all supported webhook events"""
    return {"events": SUPPORTED_EVENTS}


@router.get("", response_model=List[WebhookConfigResponse])
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    """List all webhook configurations"""
    webhooks = await crud.get_webhook_configs(db)
    return [WebhookConfigResponse(**w.to_dict()) for w in webhooks]


@router.post("", response_model=WebhookConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: WebhookConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new webhook configuration"""
    # Validate events
    invalid_events = [e for e in data.events if e not in SUPPORTED_EVENTS]
    if invalid_events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid events: {invalid_events}. Supported: {SUPPORTED_EVENTS}"
        )

    webhook = await crud.create_webhook_config(
        db,
        url=data.url,
        events=json.dumps(data.events),
        secret=data.secret,
    )
    await db.commit()

    return WebhookConfigResponse(**webhook.to_dict())


@router.get("/{webhook_id}", response_model=WebhookConfigResponse)
async def get_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific webhook configuration"""
    webhook = await crud.get_webhook_config(db, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    return WebhookConfigResponse(**webhook.to_dict())


@router.put("/{webhook_id}", response_model=WebhookConfigResponse)
async def update_webhook(
    webhook_id: int,
    data: WebhookConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a webhook configuration"""
    webhook = await crud.get_webhook_config(db, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    update_data = {}

    if data.url is not None:
        update_data["url"] = data.url

    if data.events is not None:
        invalid_events = [e for e in data.events if e not in SUPPORTED_EVENTS]
        if invalid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid events: {invalid_events}"
            )
        update_data["events"] = json.dumps(data.events)

    if data.is_active is not None:
        update_data["is_active"] = data.is_active

    if data.secret is not None:
        update_data["secret"] = data.secret

    webhook = await crud.update_webhook_config(db, webhook_id, **update_data)
    await db.commit()

    return WebhookConfigResponse(**webhook.to_dict())


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a webhook configuration"""
    deleted = await crud.delete_webhook_config(db, webhook_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    await db.commit()
    return None


@router.get("/{webhook_id}/logs", response_model=List[WebhookLogResponse])
async def get_webhook_logs(
    webhook_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get delivery logs for a webhook"""
    webhook = await crud.get_webhook_config(db, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    logs = await crud.get_webhook_logs(db, webhook_id, limit)
    return [WebhookLogResponse(**log.to_dict()) for log in logs]


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Send a test event to the webhook"""
    webhook = await crud.get_webhook_config(db, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    result = await send_test_webhook(webhook_id)
    return result
