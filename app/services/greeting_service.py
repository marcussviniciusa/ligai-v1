"""
Serviço de Greeting por Prompt

Gerencia áudios de greeting personalizados para cada prompt.
Cada prompt pode ter seu próprio greeting pré-gravado.
"""

import json
import os
import wave
from datetime import datetime
from typing import Optional, Tuple

import structlog

from murf_client import MurfClient

logger = structlog.get_logger(__name__)

# Diretórios para greetings de prompts
GREETINGS_DIR_APP = "/audio/greetings"
GREETINGS_DIR_FS = "/var/lib/freeswitch/sounds/custom/greetings"

# Greeting global (fallback)
GLOBAL_GREETING_FILE_APP = "/audio/greeting.wav"
GLOBAL_GREETING_FILE_FS = "/var/lib/freeswitch/sounds/custom/greeting.wav"
GLOBAL_GREETING_TEXT = "Olá! Bem-vindo ao atendimento. Como posso ajudar você hoje?"


def get_prompt_greeting_paths(prompt_id: int) -> Tuple[str, str, str]:
    """Retorna os paths do greeting de um prompt.

    Args:
        prompt_id: ID do prompt

    Returns:
        Tuple de (path_app_wav, path_fs_wav, path_json)
    """
    wav_filename = f"prompt_{prompt_id}.wav"
    json_filename = f"prompt_{prompt_id}.json"

    path_app = os.path.join(GREETINGS_DIR_APP, wav_filename)
    path_fs = os.path.join(GREETINGS_DIR_FS, wav_filename)
    path_json = os.path.join(GREETINGS_DIR_APP, json_filename)

    return path_app, path_fs, path_json


def get_prompt_greeting_info(prompt_id: int) -> dict:
    """Retorna informações do greeting de um prompt.

    Args:
        prompt_id: ID do prompt

    Returns:
        Dict com info do greeting ou None se não existir
    """
    path_app, path_fs, path_json = get_prompt_greeting_paths(prompt_id)

    if not os.path.exists(path_app):
        return {
            "prompt_id": prompt_id,
            "exists": False,
            "text": None,
            "duration_ms": None,
            "created_at": None
        }

    # Ler metadados do JSON
    text = None
    duration_ms = None
    voice_id = None

    if os.path.exists(path_json):
        try:
            with open(path_json, 'r') as f:
                data = json.load(f)
                text = data.get('text')
                duration_ms = data.get('duration_ms')
                voice_id = data.get('voice_id')
        except Exception as e:
            logger.warning(f"Erro ao ler JSON do greeting: {e}")

    # Se não tiver duração no JSON, calcular do arquivo
    if duration_ms is None:
        file_size = os.path.getsize(path_app)
        duration_ms = (file_size - 44) / 16  # WAV header = 44 bytes, 8kHz 16-bit

    created_at = None
    mtime = os.path.getmtime(path_app)
    created_at = datetime.fromtimestamp(mtime).isoformat()

    return {
        "prompt_id": prompt_id,
        "exists": True,
        "text": text,
        "duration_ms": duration_ms,
        "voice_id": voice_id,
        "audio_file": path_app,
        "created_at": created_at
    }


async def generate_prompt_greeting(
    prompt_id: int,
    text: str,
    voice_id: str = None
) -> dict:
    """Gera áudio de greeting para um prompt.

    Args:
        prompt_id: ID do prompt
        text: Texto do greeting
        voice_id: ID da voz (opcional, usa padrão se não fornecido)

    Returns:
        Dict com resultado da geração
    """
    # Criar diretório se não existir
    os.makedirs(GREETINGS_DIR_APP, exist_ok=True)

    path_app, path_fs, path_json = get_prompt_greeting_paths(prompt_id)

    try:
        murf = MurfClient()

        # Se voice_id fornecido, sobrescrever temporariamente
        if voice_id:
            murf.voice_id = voice_id

        logger.info(f"Gerando greeting para prompt {prompt_id}", text=text[:50])

        audio_data = await murf.text_to_speech(text)

        if not audio_data:
            return {
                "success": False,
                "prompt_id": prompt_id,
                "text": text,
                "duration_ms": 0,
                "message": "Falha ao gerar áudio TTS"
            }

        # Salvar WAV
        with wave.open(path_app, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            wav_file.writeframes(audio_data)

        # Calcular duração
        duration_ms = len(audio_data) / 16  # 8kHz 16-bit = 16 bytes/ms

        # Salvar metadados JSON
        metadata = {
            "text": text,
            "duration_ms": duration_ms,
            "voice_id": voice_id or murf.voice_id,
            "generated_at": datetime.utcnow().isoformat()
        }

        with open(path_json, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(
            f"Greeting gerado para prompt {prompt_id}",
            duration_ms=duration_ms,
            bytes=len(audio_data)
        )

        return {
            "success": True,
            "prompt_id": prompt_id,
            "text": text,
            "duration_ms": duration_ms,
            "voice_id": voice_id or murf.voice_id,
            "message": "Greeting gerado com sucesso"
        }

    except Exception as e:
        logger.exception(f"Erro ao gerar greeting para prompt {prompt_id}", error=str(e))
        return {
            "success": False,
            "prompt_id": prompt_id,
            "text": text,
            "duration_ms": 0,
            "message": f"Erro: {str(e)}"
        }


def delete_prompt_greeting(prompt_id: int) -> bool:
    """Remove arquivos de greeting de um prompt.

    Args:
        prompt_id: ID do prompt

    Returns:
        True se removido com sucesso, False caso contrário
    """
    path_app, path_fs, path_json = get_prompt_greeting_paths(prompt_id)

    deleted = False

    for path in [path_app, path_json]:
        if os.path.exists(path):
            try:
                os.remove(path)
                deleted = True
                logger.info(f"Arquivo de greeting removido: {path}")
            except Exception as e:
                logger.warning(f"Erro ao remover {path}: {e}")

    return deleted


def get_greeting_for_call(prompt_config: Optional[dict]) -> Tuple[str, float, str]:
    """Retorna o greeting apropriado para uma chamada.

    Lógica:
    1. Se prompt tem greeting_text -> usa greeting do prompt
    2. Senão -> usa greeting global

    Args:
        prompt_config: Configuração do prompt (pode ser None)

    Returns:
        Tuple de (path_fs, duration_ms, greeting_text)
    """
    # Se tem prompt com greeting configurado
    if prompt_config and prompt_config.get("greeting_text"):
        prompt_id = prompt_config.get("id")
        if prompt_id:
            path_app, path_fs, _ = get_prompt_greeting_paths(prompt_id)

            # Verificar se o arquivo existe
            if os.path.exists(path_app):
                duration_ms = prompt_config.get("greeting_duration_ms", 0)

                # Se não tiver duração, calcular do arquivo
                if not duration_ms:
                    file_size = os.path.getsize(path_app)
                    duration_ms = (file_size - 44) / 16

                logger.debug(
                    f"Usando greeting do prompt {prompt_id}",
                    duration_ms=duration_ms
                )

                return path_fs, duration_ms, prompt_config["greeting_text"]

    # Fallback: usar greeting global
    global_duration_ms = 0
    global_text = GLOBAL_GREETING_TEXT

    if os.path.exists(GLOBAL_GREETING_FILE_APP):
        file_size = os.path.getsize(GLOBAL_GREETING_FILE_APP)
        global_duration_ms = (file_size - 44) / 16

        # Tentar ler texto do JSON global
        json_file = GLOBAL_GREETING_FILE_APP.replace('.wav', '.json')
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    global_text = data.get('text', GLOBAL_GREETING_TEXT)
            except Exception:
                pass

    logger.debug("Usando greeting global", duration_ms=global_duration_ms)

    return GLOBAL_GREETING_FILE_FS, global_duration_ms, global_text
