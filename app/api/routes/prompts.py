"""
Prompts API routes
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from db import crud
from services.greeting_service import (
    generate_prompt_greeting,
    delete_prompt_greeting,
    get_prompt_greeting_info,
)

router = APIRouter()


# === Pydantic Models ===

class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=1)
    voice_id: str = Field(default="pt-BR-isadora")
    llm_model: str = Field(default="gpt-4.1-nano")
    temperature: float = Field(default=0.7, ge=0, le=2)
    greeting_text: Optional[str] = Field(None, min_length=10, max_length=500)


class PromptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    voice_id: Optional[str] = None
    llm_model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0, le=2)
    greeting_text: Optional[str] = Field(None, min_length=10, max_length=500)


class PromptResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    system_prompt: str
    voice_id: str
    llm_model: str
    temperature: float
    greeting_text: Optional[str]
    greeting_duration_ms: Optional[float]
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class GreetingRegenerateRequest(BaseModel):
    text: Optional[str] = Field(None, min_length=10, max_length=500)
    voice_id: Optional[str] = None


class GreetingResponse(BaseModel):
    success: bool
    prompt_id: int
    text: Optional[str]
    duration_ms: float
    voice_id: Optional[str] = None
    message: str


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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new prompt.

    If greeting_text is provided, generates the greeting audio in the background.
    """
    # Check if name already exists
    existing = await crud.get_prompt_by_name(db, prompt_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt with name '{prompt_data.name}' already exists"
        )

    prompt = await crud.create_prompt(db, **prompt_data.model_dump())

    # Se greeting_text foi fornecido, gerar áudio em background
    if prompt_data.greeting_text:
        background_tasks.add_task(
            _generate_greeting_and_update,
            db,
            prompt.id,
            prompt_data.greeting_text,
            prompt_data.voice_id
        )

    return PromptResponse(**prompt.to_dict())


async def _generate_greeting_and_update(
    db: AsyncSession,
    prompt_id: int,
    text: str,
    voice_id: str
):
    """Gera greeting e atualiza duração no banco."""
    result = await generate_prompt_greeting(prompt_id, text, voice_id)
    if result["success"]:
        await crud.update_prompt(db, prompt_id, greeting_duration_ms=result["duration_ms"])


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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Update a prompt.

    If greeting_text is changed, regenerates the greeting audio in the background.
    """
    # Check if new name already exists (if name is being changed)
    if prompt_data.name:
        existing = await crud.get_prompt_by_name(db, prompt_data.name)
        if existing and existing.id != prompt_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prompt with name '{prompt_data.name}' already exists"
            )

    # Buscar prompt atual para verificar se greeting_text mudou
    current_prompt = await crud.get_prompt(db, prompt_id)
    if not current_prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    update_data = prompt_data.model_dump(exclude_unset=True)

    # Se greeting_text foi alterado, regenerar áudio
    greeting_text_changed = (
        "greeting_text" in update_data and
        update_data["greeting_text"] != current_prompt.greeting_text
    )

    # Se greeting_text foi removido (definido como None ou string vazia)
    greeting_text_removed = (
        "greeting_text" in update_data and
        not update_data.get("greeting_text") and
        current_prompt.greeting_text
    )

    if greeting_text_removed:
        # Remover arquivos de greeting e limpar duração
        delete_prompt_greeting(prompt_id)
        update_data["greeting_duration_ms"] = None

    prompt = await crud.update_prompt(db, prompt_id, **update_data)

    # Regenerar greeting em background se texto mudou
    if greeting_text_changed and update_data.get("greeting_text"):
        voice_id = update_data.get("voice_id") or current_prompt.voice_id
        background_tasks.add_task(
            _generate_greeting_and_update,
            db,
            prompt_id,
            update_data["greeting_text"],
            voice_id
        )

    return PromptResponse(**prompt.to_dict())


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a prompt and its greeting files"""
    # Remover arquivos de greeting primeiro
    delete_prompt_greeting(prompt_id)

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


@router.get("/{prompt_id}/greeting", response_model=GreetingResponse)
async def get_greeting(
    prompt_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get greeting info for a prompt"""
    prompt = await crud.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    info = get_prompt_greeting_info(prompt_id)

    return GreetingResponse(
        success=info["exists"],
        prompt_id=prompt_id,
        text=info.get("text") or prompt.greeting_text,
        duration_ms=info.get("duration_ms") or 0,
        voice_id=info.get("voice_id"),
        message="Greeting exists" if info["exists"] else "Greeting not generated yet"
    )


@router.post("/{prompt_id}/greeting", response_model=GreetingResponse)
async def regenerate_greeting(
    prompt_id: int,
    request: GreetingRegenerateRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """Regenerate greeting audio for a prompt.

    If text is not provided, uses the existing greeting_text from the prompt.
    If voice_id is not provided, uses the prompt's voice_id.
    """
    prompt = await crud.get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

    # Determinar texto a usar
    text = (request and request.text) or prompt.greeting_text
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No greeting_text available. Provide text in request or set greeting_text on the prompt."
        )

    # Determinar voice_id a usar
    voice_id = (request and request.voice_id) or prompt.voice_id

    # Gerar greeting
    result = await generate_prompt_greeting(prompt_id, text, voice_id)

    # Atualizar prompt no banco se sucesso
    if result["success"]:
        await crud.update_prompt(
            db,
            prompt_id,
            greeting_text=text,
            greeting_duration_ms=result["duration_ms"]
        )

    return GreetingResponse(
        success=result["success"],
        prompt_id=prompt_id,
        text=text,
        duration_ms=result.get("duration_ms", 0),
        voice_id=voice_id,
        message=result["message"]
    )
