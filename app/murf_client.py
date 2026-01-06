"""
Cliente Murf AI para Text-to-Speech
"""

import asyncio
import io
from typing import Optional

import aiohttp
import structlog
from pydub import AudioSegment

from config import settings

logger = structlog.get_logger(__name__)

# Endpoint da API Murf
MURF_API_BASE = "https://api.murf.ai/v1"


class MurfClient:
    """
    Cliente para conversão de texto em fala usando Murf AI

    Gera áudio natural em português brasileiro e converte
    para formato compatível com telefonia (8kHz, mono, 16-bit PCM)
    """

    def __init__(self):
        self.api_key = settings.MURF_API_KEY
        self.voice_id = settings.MURF_VOICE_ID
        self.style = settings.MURF_STYLE
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Retorna sessão HTTP, criando se necessário"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
        return self.session

    async def close(self):
        """Fecha a sessão HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """
        Converte texto em áudio

        Args:
            text: Texto para converter

        Returns:
            Bytes de áudio em formato PCM 8kHz mono 16-bit
        """
        if not text.strip():
            return None

        try:
            session = await self._get_session()

            # Preparar payload para Murf API
            payload = {
                "text": text,
                "voiceId": self.voice_id,
                "style": self.style,
                "format": "WAV",
                "sampleRate": 24000,  # Murf gera em 24kHz, vamos converter
                "channelType": "MONO",
                "speed": 0.9,  # Velocidade um pouco mais lenta (0.5 a 2.0, 1.0 é normal)
                "pronunciationDictionary": {},
                "encodeAsBase64": False,
                "modelVersion": "GEN2"  # Usar modelo mais recente
            }

            logger.debug("Gerando áudio com Murf", text_length=len(text))

            # Chamar API
            async with session.post(
                f"{MURF_API_BASE}/speech/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        "Erro na API Murf",
                        status=response.status,
                        error=error_text
                    )
                    return None

                result = await response.json()

                # Obter URL do áudio gerado
                audio_url = result.get("audioFile")
                if not audio_url:
                    logger.error("URL de áudio não retornada pela Murf")
                    return None

                # Baixar o áudio
                audio_data = await self._download_audio(audio_url)
                if not audio_data:
                    return None

                # Converter para formato de telefonia
                converted_audio = await self._convert_to_telephony_format(audio_data)
                return converted_audio

        except asyncio.TimeoutError:
            logger.error("Timeout na API Murf")
            return None
        except Exception as e:
            logger.exception("Erro ao gerar áudio com Murf", error=str(e))
            return None

    async def _download_audio(self, url: str) -> Optional[bytes]:
        """Baixa arquivo de áudio da URL"""
        try:
            session = await self._get_session()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error("Erro ao baixar áudio", status=response.status)
                    return None
        except Exception as e:
            logger.exception("Erro ao baixar áudio", error=str(e))
            return None

    async def _convert_to_telephony_format(self, audio_data: bytes) -> bytes:
        """
        Converte áudio para formato de telefonia

        Entrada: WAV 24kHz
        Saída: PCM 8kHz mono 16-bit (formato para FreeSWITCH)
        """
        try:
            # Usar asyncio para não bloquear
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._convert_sync,
                audio_data
            )
        except Exception as e:
            logger.exception("Erro ao converter áudio", error=str(e))
            return audio_data

    def _convert_sync(self, audio_data: bytes) -> bytes:
        """Conversão síncrona de áudio"""
        try:
            # Carregar áudio
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format="wav")

            # Converter para mono se necessário
            if audio.channels > 1:
                audio = audio.set_channels(1)

            # Converter sample rate para 8kHz (telefonia)
            audio = audio.set_frame_rate(8000)

            # Garantir 16-bit
            audio = audio.set_sample_width(2)

            # Exportar como PCM raw
            output = io.BytesIO()
            audio.export(output, format="raw")
            return output.getvalue()

        except Exception as e:
            logger.exception("Erro na conversão síncrona", error=str(e))
            raise

    async def list_voices(self, language: str = "pt-BR") -> list[dict]:
        """Lista vozes disponíveis para um idioma"""
        try:
            session = await self._get_session()

            async with session.get(
                f"{MURF_API_BASE}/speech/voices",
                params={"language": language}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("voices", [])
                else:
                    logger.error("Erro ao listar vozes", status=response.status)
                    return []

        except Exception as e:
            logger.exception("Erro ao listar vozes", error=str(e))
            return []

    async def get_voice_info(self, voice_id: str) -> Optional[dict]:
        """Obtém informações de uma voz específica"""
        voices = await self.list_voices()
        for voice in voices:
            if voice.get("voiceId") == voice_id:
                return voice
        return None
