"""
Cliente Deepgram para Speech-to-Text em tempo real
Usando SDK v5.x com AsyncDeepgramClient
"""

import asyncio
from typing import Callable, Optional

import structlog
from deepgram import AsyncDeepgramClient as DGClient
from deepgram.core.events import EventType

from config import settings

logger = structlog.get_logger(__name__)


class DeepgramClient:
    """
    Cliente para transcrição em tempo real usando Deepgram Nova
    """

    def __init__(
        self,
        on_transcript: Callable[[str, bool], None],
        on_speech_started: Optional[Callable[[], None]] = None,
        on_speech_ended: Optional[Callable[[], None]] = None
    ):
        self.on_transcript = on_transcript
        self.on_speech_started = on_speech_started
        self.on_speech_ended = on_speech_ended

        self.client: Optional[DGClient] = None
        self.connection = None
        self.is_connected = False
        self._context_manager = None
        self._listen_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Estabelece conexão assíncrona com Deepgram"""
        try:
            # Criar cliente Deepgram async
            self.client = DGClient(api_key=settings.DEEPGRAM_API_KEY)

            # Criar context manager
            self._context_manager = self.client.listen.v1.connect(
                model=settings.DEEPGRAM_MODEL,
                language=settings.DEEPGRAM_LANGUAGE,
                encoding=settings.DEEPGRAM_ENCODING,
                sample_rate=str(settings.DEEPGRAM_SAMPLE_RATE),
                channels=str(settings.CHANNELS),
                punctuate="true",
                interim_results="true",
                endpointing="300",
                vad_events="true",
                smart_format="true",
            )

            # Entrar no context manager
            self.connection = await self._context_manager.__aenter__()

            # Registrar handlers
            self.connection.on(EventType.OPEN, self._on_open)
            self.connection.on(EventType.CLOSE, self._on_close)
            self.connection.on(EventType.MESSAGE, self._on_message)
            self.connection.on(EventType.ERROR, self._on_error)

            # Iniciar listening em background task
            self._listen_task = asyncio.create_task(self._listen_loop())

            self.is_connected = True
            logger.info("Conectado ao Deepgram (async)")

        except Exception as e:
            logger.exception("Erro ao conectar com Deepgram", error=str(e))
            raise

    async def _listen_loop(self):
        """Loop de escuta assíncrono"""
        try:
            await self.connection.start_listening()
        except asyncio.CancelledError:
            logger.info("Listen task cancelada")
        except Exception as e:
            logger.exception("Erro no listen loop", error=str(e))

    async def disconnect(self):
        """Encerra conexão com Deepgram"""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._context_manager:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.warning("Erro ao encerrar conexão Deepgram", error=str(e))

        self.is_connected = False
        logger.info("Desconectado do Deepgram")

    async def send_audio(self, audio_data: bytes):
        """Envia chunk de áudio para transcrição"""
        if not self.is_connected or not self.connection:
            return

        try:
            await self.connection._send(audio_data)
        except Exception as e:
            # Don't spam logs for send errors after disconnect
            if self.is_connected:
                logger.exception("Erro ao enviar áudio para Deepgram", error=str(e))

    def _on_open(self, *args, **kwargs):
        """Handler para evento de conexão aberta"""
        logger.info("Conexão Deepgram aberta")

    def _on_close(self, *args, **kwargs):
        """Handler para evento de conexão fechada"""
        self.is_connected = False
        logger.info("Conexão Deepgram fechada")

    def _on_message(self, message, *args, **kwargs):
        """Handler para mensagens recebidas (transcrições)"""
        try:
            msg_type = getattr(message, "type", None)

            # Verificar tipo de mensagem
            if msg_type == "SpeechStarted":
                if self.on_speech_started:
                    self._call_async(self.on_speech_started)
                return

            if msg_type == "UtteranceEnd":
                if self.on_speech_ended:
                    self._call_async(self.on_speech_ended)
                return

            # Processar transcrição
            channel = getattr(message, "channel", None)
            if not channel:
                return

            alternatives = getattr(channel, "alternatives", [])
            if not alternatives:
                return

            transcript = getattr(alternatives[0], "transcript", "")
            if not transcript:
                return

            is_final = getattr(message, "is_final", True)

            logger.info("Transcrição recebida", text=transcript, is_final=is_final)

            # Chamar callback
            self._call_async(self.on_transcript, transcript, is_final)

        except Exception as e:
            logger.exception("Erro ao processar mensagem Deepgram", error=str(e))

    def _on_error(self, error, *args, **kwargs):
        """Handler para erros"""
        logger.error("Erro Deepgram", error=str(error))

    def _call_async(self, callback, *args):
        """Chama callback async de forma segura"""
        try:
            loop = asyncio.get_event_loop()
            if asyncio.iscoroutinefunction(callback):
                asyncio.run_coroutine_threadsafe(callback(*args), loop)
            else:
                loop.call_soon_threadsafe(callback, *args)
        except Exception as e:
            logger.exception("Erro ao chamar callback", error=str(e))
