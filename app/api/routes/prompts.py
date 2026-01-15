"""
Prompts API routes
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from db import crud

router = APIRouter()


# === Pydantic Models ===

class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=1)
    voice_id: str = Field(default="pt-BR-isadora")
    llm_model: str = Field(default="gpt-4.1-nano")
    temperature: float = Field(default=0.7, ge=0, le=2)


class PromptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    voice_id: Optional[str] = None
    llm_model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0, le=2)


class PromptResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    system_prompt: str
    voice_id: str
    llm_model: str
    temperature: float
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# === Routes ===

@router.get("", response_model=List[PromptResponse])
async def list_prompts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all prompts"""
    prompts = await crud.get_prompts(db, skip=skip, limit=limit)
    return [PromptResponse(**p.to_dict()) for p in prompts]


@router.post("", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_data: PromptCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new prompt"""
    # Check if name already exists
    existing = await crud.get_prompt_by_name(db, prompt_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt with name '{prompt_data.name}' already exists"
        )

    prompt = await crud.create_prompt(db, **prompt_data.model_dump())
    return PromptResponse(**prompt.to_dict())


@router.get("/active", response_model=Optional[PromptResponse])
async def get_active_prompt(db: AsyncSession = Depends(get_db)):
    """Get the currently active prompt"""
    prompt = await crud.get_active_prompt(db)
    if not prompt:
        return None
    return PromptResponse(**prompt.to_dict())


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific prompt"""
    prompt = await crud.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    return PromptResponse(**prompt.to_dict())


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: int,
    prompt_data: PromptUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a prompt"""
    # Check if new name already exists (if name is being changed)
    if prompt_data.name:
        existing = await crud.get_prompt_by_name(db, prompt_data.name)
        if existing and existing.id != prompt_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prompt with name '{prompt_data.name}' already exists"
            )

    prompt = await crud.update_prompt(
        db,
        prompt_id,
        **prompt_data.model_dump(exclude_unset=True)
    )
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    return PromptResponse(**prompt.to_dict())


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a prompt"""
    deleted = await crud.delete_prompt(db, prompt_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    return None


@router.post("/{prompt_id}/activate", response_model=PromptResponse)
async def activate_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Set a prompt as active (deactivates all others)"""
    prompt = await crud.set_active_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    return PromptResponse(**prompt.to_dict())
