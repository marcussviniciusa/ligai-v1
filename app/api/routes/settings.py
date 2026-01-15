"""
Settings API routes
"""

from typing import List, Optional
import aiohttp

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from db import crud
from config import settings as app_settings

router = APIRouter()


# === Pydantic Models ===

class SettingResponse(BaseModel):
    id: int
    key: str
    value: str  # masked if is_secret
    description: Optional[str]
    is_secret: bool
    is_configured: bool
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: str = Field(..., min_length=0)


class TestApiKeyRequest(BaseModel):
    key: str
    value: str


class TestApiKeyResponse(BaseModel):
    success: bool
    message: str


# === Routes ===

@router.get("", response_model=List[SettingResponse])
async def list_settings(db: AsyncSession = Depends(get_db)):
    """List all settings (values are masked for secrets)"""
    settings_list = await crud.get_all_settings(db)

    # If no settings, initialize defaults
    if not settings_list:
        await crud.init_default_settings(db)
        await db.commit()
        settings_list = await crud.get_all_settings(db)

    return [SettingResponse(**s.to_dict(hide_secrets=True)) for s in settings_list]


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Get a specific setting by key"""
    setting = await crud.get_setting(db, key)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )
    return SettingResponse(**setting.to_dict(hide_secrets=True))


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a setting value"""
    setting = await crud.upsert_setting(db, key, data.value)
    await db.commit()

    # Update runtime config
    await _update_runtime_config(key, data.value)

    return SettingResponse(**setting.to_dict(hide_secrets=True))


@router.post("/test", response_model=TestApiKeyResponse)
async def test_api_key(data: TestApiKeyRequest):
    """Test if an API key is valid"""
    key = data.key
    value = data.value

    if not value:
        return TestApiKeyResponse(success=False, message="API key vazia")

    try:
        if key == "DEEPGRAM_API_KEY":
            success, message = await _test_deepgram_key(value)
        elif key == "MURF_API_KEY":
            success, message = await _test_murf_key(value)
        elif key == "OPENAI_API_KEY":
            success, message = await _test_openai_key(value)
        else:
            return TestApiKeyResponse(success=False, message=f"Chave desconhecida: {key}")

        return TestApiKeyResponse(success=success, message=message)
    except Exception as e:
        return TestApiKeyResponse(success=False, message=f"Erro: {str(e)}")


@router.post("/reload")
async def reload_settings(db: AsyncSession = Depends(get_db)):
    """Reload settings from database into runtime config"""
    settings_list = await crud.get_all_settings(db)

    for setting in settings_list:
        if setting.value:
            await _update_runtime_config(setting.key, setting.value)

    return {"success": True, "message": "Configuracoes recarregadas"}


# === Helper Functions ===

async def _update_runtime_config(key: str, value: str) -> None:
    """Update the runtime config singleton"""
    if key == "DEEPGRAM_API_KEY":
        app_settings.DEEPGRAM_API_KEY = value
    elif key == "MURF_API_KEY":
        app_settings.MURF_API_KEY = value
    elif key == "OPENAI_API_KEY":
        app_settings.OPENAI_API_KEY = value


async def _test_deepgram_key(api_key: str) -> tuple[bool, str]:
    """Test Deepgram API key by checking account info"""
    url = "https://api.deepgram.com/v1/projects"
    headers = {"Authorization": f"Token {api_key}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                return True, "Deepgram: Conexao OK"
            elif response.status == 401:
                return False, "Deepgram: API key invalida"
            else:
                return False, f"Deepgram: Erro {response.status}"


async def _test_murf_key(api_key: str) -> tuple[bool, str]:
    """Test Murf API key by listing voices"""
    url = "https://api.murf.ai/v1/speech/voices"
    headers = {"api-key": api_key}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                return True, "Murf AI: Conexao OK"
            elif response.status == 401 or response.status == 403:
                return False, "Murf AI: API key invalida"
            else:
                return False, f"Murf AI: Erro {response.status}"


async def _test_openai_key(api_key: str) -> tuple[bool, str]:
    """Test OpenAI API key by listing models"""
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                return True, "OpenAI: Conexao OK"
            elif response.status == 401:
                return False, "OpenAI: API key invalida"
            else:
                return False, f"OpenAI: Erro {response.status}"
