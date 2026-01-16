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


class GreetingResponse(BaseModel):
    """Informacoes do audio de saudacao pre-gravado"""
    text: str = Field(..., description="Texto da saudacao atual", example="Ola! Sou a assistente virtual da LigAI. Como posso ajudar?")
    audio_file: str = Field(..., description="Caminho do arquivo de audio WAV", example="/audio/greeting.wav")
    duration_ms: float = Field(..., description="Duracao do audio em milissegundos", example=4500.0)
    file_exists: bool = Field(..., description="Se o arquivo de audio existe no sistema", example=True)
    created_at: Optional[str] = Field(None, description="Data/hora de criacao do audio (ISO 8601)", example="2026-01-16T10:30:00")

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Ola! Sou a assistente virtual da LigAI. Como posso ajudar?",
                "audio_file": "/audio/greeting.wav",
                "duration_ms": 4500.0,
                "file_exists": True,
                "created_at": "2026-01-16T10:30:00"
            }
        }
    }


class GreetingRequest(BaseModel):
    """Requisicao para gerar novo audio de saudacao"""
    text: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Texto da nova saudacao (10-500 caracteres)",
        example="Ola! Sou a Julia, assistente virtual da LigAI. Em que posso ajudar voce hoje?"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Ola! Sou a Julia, assistente virtual da LigAI. Em que posso ajudar voce hoje?"
            }
        }
    }


class GreetingGenerateResponse(BaseModel):
    """Resposta da geracao de novo audio de saudacao"""
    success: bool = Field(..., description="Se a geracao foi bem sucedida", example=True)
    text: str = Field(..., description="Texto usado para gerar o audio", example="Ola! Sou a Julia...")
    duration_ms: float = Field(..., description="Duracao do audio gerado em milissegundos", example=5200.0)
    message: str = Field(..., description="Mensagem de status", example="Greeting gerado com sucesso")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "text": "Ola! Sou a Julia, assistente virtual da LigAI.",
                    "duration_ms": 5200.0,
                    "message": "Greeting gerado com sucesso"
                },
                {
                    "success": False,
                    "text": "Texto invalido",
                    "duration_ms": 0,
                    "message": "Falha ao gerar audio TTS"
                }
            ]
        }
    }


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


@router.get(
    "/greeting",
    response_model=GreetingResponse,
    summary="Obter saudacao atual",
    description="""
Retorna informacoes sobre o audio de saudacao pre-gravado que e reproduzido
automaticamente quando o cliente atende a ligacao.

**Informacoes retornadas:**
- Texto da saudacao
- Caminho do arquivo de audio
- Duracao em milissegundos
- Se o arquivo existe
- Data de criacao
"""
)
async def get_greeting():
    """Retorna informacoes do greeting atual"""
    from call_handler import get_greeting_info
    return get_greeting_info()


@router.post(
    "/greeting",
    response_model=GreetingGenerateResponse,
    summary="Gerar nova saudacao",
    description="""
Gera um novo audio de saudacao usando TTS (Text-to-Speech) da Murf AI.

**O que acontece:**
1. O texto enviado e convertido em audio via Murf AI
2. O audio e salvo em formato WAV (8kHz mono, 16-bit PCM)
3. O arquivo antigo e substituido
4. Proximas chamadas usarao a nova saudacao automaticamente

**Restricoes:**
- Texto deve ter entre 10 e 500 caracteres
- Requer API key da Murf AI configurada
"""
)
async def update_greeting(data: GreetingRequest):
    """Gera novo audio de greeting via TTS"""
    from call_handler import generate_new_greeting
    result = await generate_new_greeting(data.text)
    return result


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
