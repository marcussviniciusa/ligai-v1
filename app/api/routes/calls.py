"""
Calls API routes
"""

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from db import crud

router = APIRouter()


# === Pydantic Models ===

class CallMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    audio_duration_ms: Optional[int]
    timestamp: str

    class Config:
        from_attributes = True


class CallResponse(BaseModel):
    id: int
    call_id: str
    freeswitch_uuid: Optional[str]
    caller_number: Optional[str]
    called_number: Optional[str]
    prompt_id: Optional[int]
    status: str
    direction: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[float]
    summary: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class CallDetailResponse(CallResponse):
    messages: List[CallMessageResponse] = []


class CallsListResponse(BaseModel):
    items: List[CallResponse]
    total: int
    page: int
    per_page: int


class ActiveCallResponse(BaseModel):
    call_id: str
    freeswitch_uuid: Optional[str]
    caller_number: Optional[str]
    called_number: Optional[str]
    state: str
    duration: float
    message_count: int


class DialRequest(BaseModel):
    number: str = Field(..., min_length=10, max_length=15)
    prompt_id: Optional[int] = None


class DialResponse(BaseModel):
    success: bool
    call_id: Optional[str] = None
    message: str


# === Routes ===

@router.get("/active", response_model=List[ActiveCallResponse])
async def list_active_calls():
    """List all currently active calls"""
    import structlog
    from state import active_calls
    logger = structlog.get_logger(__name__)

    logger.info("Consultando chamadas ativas", total=len(active_calls), keys=list(active_calls.keys()))

    result = []
    for call_id, handler in active_calls.items():
        try:
            status_data = handler.get_status()
            logger.info("Status da chamada", call_id=call_id, status=status_data)
            result.append(ActiveCallResponse(
                call_id=call_id,
                freeswitch_uuid=status_data.get("freeswitch_uuid"),
                caller_number=status_data.get("caller_number"),
                called_number=status_data.get("called_number"),
                state=status_data.get("state", "unknown"),
                duration=status_data.get("duration", 0),
                message_count=status_data.get("message_count", 0),
            ))
        except Exception as e:
            logger.error("Erro ao obter status da chamada", call_id=call_id, error=str(e))

    return result


@router.get("/active/{call_id}", response_model=ActiveCallResponse)
async def get_active_call(call_id: str):
    """Get status of a specific active call"""
    from state import active_calls

    handler = active_calls.get(call_id)
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active call not found"
        )

    status_data = handler.get_status()
    return ActiveCallResponse(
        call_id=call_id,
        freeswitch_uuid=status_data.get("freeswitch_uuid"),
        caller_number=status_data.get("caller_number"),
        called_number=status_data.get("called_number"),
        state=status_data.get("state", "unknown"),
        duration=status_data.get("duration", 0),
        message_count=status_data.get("message_count", 0),
    )


@router.post("/{call_id}/hangup")
async def hangup_call(call_id: str):
    """Hang up an active call"""
    from state import active_calls
    from services.dialer_service import hangup_call as do_hangup

    handler = active_calls.get(call_id)
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active call not found"
        )

    freeswitch_uuid = handler.freeswitch_uuid
    if freeswitch_uuid:
        success = await do_hangup(freeswitch_uuid)
        if success:
            return {"success": True, "message": "Call hangup initiated"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to hangup call"
            )

    return {"success": False, "message": "No FreeSWITCH UUID available"}


@router.post("/dial", response_model=DialResponse)
async def dial_number(
    request: DialRequest,
    db: AsyncSession = Depends(get_db)
):
    """Initiate a new outbound call"""
    from services.dialer_service import initiate_call

    # Get prompt config if specified
    prompt = None
    if request.prompt_id:
        prompt = await crud.get_prompt(db, request.prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )
    else:
        # Use active prompt if no specific prompt specified
        prompt = await crud.get_active_prompt(db)

    prompt_config = prompt.to_dict() if prompt else None

    try:
        call_id = await initiate_call(request.number, prompt_config)
        if call_id:
            return DialResponse(
                success=True,
                call_id=call_id,
                message=f"Call initiated to {request.number}"
            )
        else:
            return DialResponse(
                success=False,
                message="Failed to initiate call"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("", response_model=CallsListResponse)
async def list_calls(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """List call history with pagination and filters"""
    skip = (page - 1) * per_page

    calls = await crud.get_calls(
        db,
        skip=skip,
        limit=per_page,
        status=status,
        from_date=from_date,
        to_date=to_date,
    )

    total = await crud.count_calls(
        db,
        status=status,
        from_date=from_date,
        to_date=to_date,
    )

    return CallsListResponse(
        items=[CallResponse(**c.to_dict()) for c in calls],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{call_id}", response_model=CallDetailResponse)
async def get_call_detail(
    call_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific call including transcript"""
    call = await crud.get_call(db, call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )

    return CallDetailResponse(**call.to_dict(include_messages=True))


@router.delete("/{call_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_call(
    call_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a call record"""
    deleted = await crud.delete_call(db, call_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    return None
