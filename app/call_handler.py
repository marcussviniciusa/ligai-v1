"""
Handler de chamadas - Gerencia o fluxo de uma chamada individual
"""

import asyncio
import json
import os
import random
import time
import uuid as uuid_lib
import wave
from enum import Enum
from typing import Optional


class ConversationState(Enum):
    """Estados da máquina de estados de conversação"""
    IDLE = "idle"           # Pronto para receber entrada do usuário
    PROCESSING = "processing"  # Gerando resposta (filler + LLM)
    SPEAKING = "speaking"   # Tocando áudio da resposta

import aiofiles
import structlog
from websockets.server import WebSocketServerProtocol

from deepgram_client import DeepgramClient
from murf_client import MurfClient
from llm_client import LLMClient
from config import settings

logger = structlog.get_logger(__name__)

# Diretório para arquivos de áudio temporários
# ligai-app monta em /audio, FreeSWITCH monta em /var/lib/freeswitch/sounds/custom
AUDIO_TMP_DIR_APP = "/audio"
AUDIO_TMP_DIR_FS = "/var/lib/freeswitch/sounds/custom"

# Frases de filler para reduzir percepção de latência (2-3 segundos cada)
FILLER_PHRASES = [
    "Entendi perfeitamente.",
    "Certo, compreendi.",
    "Ok, entendi você.",
    "Perfeito, compreendi.",
    "Certo, entendi o que você disse.",
]

# Diretório para áudios de filler pré-gerados
FILLER_DIR_APP = "/audio/fillers"
FILLER_DIR_FS = "/var/lib/freeswitch/sounds/custom/fillers"

# Cache global de fillers gerados (compartilhado entre todas as chamadas)
_filler_cache: dict[str, tuple[str, str, int]] = {}  # phrase -> (path_app, path_fs, size)
_filler_ready = False


async def initialize_fillers():
    """Pré-gera os áudios de filler na inicialização do sistema.

    Deve ser chamado uma vez na startup da aplicação.
    Os arquivos são salvos permanentemente e reutilizados.
    """
    global _filler_cache, _filler_ready

    if _filler_ready:
        return

    logger.info("Inicializando áudios de filler...")

    # Criar diretório de fillers
    os.makedirs(FILLER_DIR_APP, exist_ok=True)

    # Verificar se fillers já existem
    existing_fillers = 0
    for i, phrase in enumerate(FILLER_PHRASES):
        filename = f"filler_{i}.wav"
        filepath_app = os.path.join(FILLER_DIR_APP, filename)
        filepath_fs = os.path.join(FILLER_DIR_FS, filename)

        if os.path.exists(filepath_app):
            # Filler já existe, carregar no cache
            file_size = os.path.getsize(filepath_app)
            _filler_cache[phrase] = (filepath_app, filepath_fs, file_size)
            existing_fillers += 1
            logger.debug(f"Filler existente: {phrase}")

    if existing_fillers == len(FILLER_PHRASES):
        logger.info(f"Todos os {existing_fillers} fillers já existem")
        _filler_ready = True
        return

    # Gerar fillers faltantes com Murf
    murf = MurfClient()

    for i, phrase in enumerate(FILLER_PHRASES):
        if phrase in _filler_cache:
            continue

        filename = f"filler_{i}.wav"
        filepath_app = os.path.join(FILLER_DIR_APP, filename)
        filepath_fs = os.path.join(FILLER_DIR_FS, filename)

        try:
            logger.info(f"Gerando filler: {phrase}")
            audio_data = await murf.text_to_speech(phrase)

            if audio_data:
                # Salvar como WAV
                with wave.open(filepath_app, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(8000)
                    wav_file.writeframes(audio_data)

                _filler_cache[phrase] = (filepath_app, filepath_fs, len(audio_data))
                logger.info(f"Filler gerado: {phrase} ({len(audio_data)} bytes)")
            else:
                logger.warning(f"Falha ao gerar filler: {phrase}")

        except Exception as e:
            logger.exception(f"Erro ao gerar filler '{phrase}'", error=str(e))

    _filler_ready = len(_filler_cache) > 0
    logger.info(f"Fillers inicializados: {len(_filler_cache)}/{len(FILLER_PHRASES)}")


def get_random_filler() -> Optional[tuple[str, str, str, int]]:
    """Retorna um filler aleatório do cache.

    Returns:
        Tuple de (phrase, path_app, path_fs, size) ou None se não houver fillers
    """
    if not _filler_cache:
        return None

    phrase = random.choice(list(_filler_cache.keys()))
    path_app, path_fs, size = _filler_cache[phrase]
    return phrase, path_app, path_fs, size


class CallHandler:
    """
    Gerencia uma chamada individual

    Fluxo:
    1. Recebe áudio do FreeSWITCH
    2. Envia para Deepgram (STT)
    3. Processa texto com LLM
    4. Converte resposta com Murf (TTS)
    5. Envia áudio de volta para FreeSWITCH
    """

    def __init__(
        self,
        call_id: str,
        caller_number: str,
        called_number: str,
        websocket: WebSocketServerProtocol,
        freeswitch_uuid: str = None
    ):
        self.call_id = call_id
        self.caller_number = caller_number
        self.called_number = called_number
        self.websocket = websocket
        self.freeswitch_uuid = freeswitch_uuid or call_id

        self.deepgram: Optional[DeepgramClient] = None
        self.murf: Optional[MurfClient] = None
        self.llm: Optional[LLMClient] = None

        self.is_running = False
        self.start_time = time.time()
        self.transcript_buffer = ""
        self.last_speech_time = time.time()
        self.is_speaking = False  # Usuário está falando (detectado pelo Deepgram)

        # Máquina de estados para controle de conversação
        self.state = ConversationState.IDLE
        self.conversation_history: list[dict] = []

        # Prompt do sistema para o assistente
        self.system_prompt = """Você é um assistente virtual de atendimento telefônico.
Seja cordial, objetivo e helpful. Responda de forma natural e conversacional.
Se não entender algo, peça educadamente para repetir.

REGRAS OBRIGATÓRIAS:
1. Respostas MUITO CURTAS - máximo 1-2 frases. Isso é uma ligação telefônica, não um texto.
2. NUNCA comece com frases de confirmação como "Entendi", "Compreendi", "Certo", "Ok", "Perfeito", "Claro" - o sistema já fala isso automaticamente.
3. Vá direto ao ponto, sem enrolação."""

    async def start(self):
        """Inicia os clientes de STT, TTS e LLM"""
        self.is_running = True

        # Inicializar Deepgram
        self.deepgram = DeepgramClient(
            on_transcript=self._on_transcript,
            on_speech_started=self._on_speech_started,
            on_speech_ended=self._on_speech_ended
        )
        await self.deepgram.connect()

        # Inicializar Murf
        self.murf = MurfClient()

        # Inicializar LLM
        self.llm = LLMClient(system_prompt=self.system_prompt)

        logger.info("CallHandler iniciado", call_id=self.call_id)

        # Enviar saudação inicial
        await self._send_greeting()

    async def stop(self):
        """Encerra a chamada e limpa recursos"""
        self.is_running = False

        if self.deepgram:
            await self.deepgram.disconnect()

        duration = time.time() - self.start_time
        logger.info(
            "CallHandler encerrado",
            call_id=self.call_id,
            duration_seconds=round(duration, 2)
        )

    async def process_audio(self, audio_data: bytes):
        """Processa chunk de áudio recebido do FreeSWITCH"""
        if not self.is_running or not self.deepgram:
            return

        # Log first audio chunk for debugging
        if not hasattr(self, '_audio_count'):
            self._audio_count = 0
        self._audio_count += 1
        if self._audio_count <= 3 or self._audio_count % 100 == 0:
            print(f"[AUDIO] Chunk #{self._audio_count}: {len(audio_data)} bytes", flush=True)

        # Enviar para Deepgram
        await self.deepgram.send_audio(audio_data)

    async def handle_dtmf(self, digit: str):
        """Processa dígito DTMF recebido"""
        logger.info("DTMF recebido", call_id=self.call_id, digit=digit)
        # Implementar lógica de DTMF se necessário (menus, etc)

    async def _on_transcript(self, text: str, is_final: bool):
        """Callback quando Deepgram retorna transcrição"""
        if not text.strip():
            return

        logger.debug(
            "Transcrição recebida",
            call_id=self.call_id,
            text=text,
            is_final=is_final,
            state=self.state.value
        )

        if is_final:
            self.transcript_buffer = ""

            # Só processa se estiver em IDLE
            if self.state == ConversationState.IDLE:
                await self._process_user_input(text)
            else:
                # PROCESSING ou SPEAKING: ignorar mensagem (não guardar)
                # Isso é mais natural em ligação - pessoa precisa esperar IA terminar
                logger.info(
                    f"Estado {self.state.value}: ignorando mensagem (IA ocupada)",
                    call_id=self.call_id,
                    text=text
                )
        else:
            self.transcript_buffer = text

    async def _on_speech_started(self):
        """Callback quando usuário começa a falar"""
        self.is_speaking = True
        self.last_speech_time = time.time()
        logger.debug("Usuário começou a falar", call_id=self.call_id)

    async def _on_speech_ended(self):
        """Callback quando usuário para de falar"""
        self.is_speaking = False
        logger.debug("Usuário parou de falar", call_id=self.call_id)

    async def _process_user_input(self, text: str):
        """Processa entrada do usuário e gera resposta"""
        logger.info("Processando entrada do usuário", call_id=self.call_id, text=text)

        # Transição: IDLE → PROCESSING
        self.state = ConversationState.PROCESSING

        # Adicionar ao histórico
        self.conversation_history.append({
            "role": "user",
            "content": text
        })

        try:
            # Tocar filler imediatamente para reduzir percepção de latência
            filler_task = None
            filler_info = get_random_filler()

            if filler_info:
                phrase, filler_path_app, filler_path_fs, filler_size = filler_info
                logger.info(f"Tocando filler: {phrase}", call_id=self.call_id)

                # Iniciar playback do filler (não aguarda terminar)
                filler_task = asyncio.create_task(
                    self._play_filler(filler_path_fs)
                )

            # Em paralelo com o filler, gerar resposta com LLM
            response = await self.llm.generate_response(
                text,
                self.conversation_history
            )

            logger.info(
                "Resposta gerada",
                call_id=self.call_id,
                response=response[:100] + "..." if len(response) > 100 else response
            )

            # Adicionar resposta ao histórico
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })

            # Aguardar filler terminar antes de tocar resposta
            if filler_task:
                await filler_task

            # Transição: PROCESSING → SPEAKING
            self.state = ConversationState.SPEAKING

            # Converter para áudio e enviar
            await self._speak(response)

        except Exception as e:
            logger.exception("Erro ao processar entrada", call_id=self.call_id, error=str(e))
            await self._speak("Desculpe, tive um problema. Pode repetir?")

    async def _play_filler(self, filepath_fs: str):
        """Reproduz áudio de filler via FreeSWITCH ESL

        Versão simplificada de _play_audio_file para fillers pré-gerados.
        Não deleta o arquivo após playback.
        """
        try:
            # Conectar ao ESL do FreeSWITCH
            reader, writer = await asyncio.open_connection('127.0.0.1', 8021)

            # Ler banner inicial
            await reader.readuntil(b'\n\n')

            # Autenticar
            writer.write(b'auth ClueCon\n\n')
            await writer.drain()
            auth_response = await reader.readuntil(b'\n\n')

            if b'+OK' not in auth_response:
                writer.close()
                await writer.wait_closed()
                return

            # Enviar comando uuid_broadcast
            cmd = f"api uuid_broadcast {self.freeswitch_uuid} {filepath_fs} aleg\n\n"
            writer.write(cmd.encode())
            await writer.drain()

            # Ler resposta
            header = await reader.readuntil(b'\n\n')
            header_str = header.decode()

            content_length = 0
            for line in header_str.split('\n'):
                if line.startswith('Content-Length:'):
                    content_length = int(line.split(':')[1].strip())
                    break

            if content_length > 0:
                await reader.readexactly(content_length)

            # Fechar conexão
            writer.close()
            await writer.wait_closed()

            # Aguardar duração aproximada do filler (~2s para frases mais longas)
            await asyncio.sleep(2.0)

        except Exception as e:
            logger.debug(f"Erro ao tocar filler: {e}")

    async def _send_greeting(self):
        """Envia saudação inicial"""
        # Transição: IDLE → SPEAKING (saudação não precisa de PROCESSING)
        self.state = ConversationState.SPEAKING

        greeting = "Olá! Bem-vindo ao atendimento. Como posso ajudar você hoje?"
        self.conversation_history.append({
            "role": "assistant",
            "content": greeting
        })
        await self._speak(greeting)

    async def _speak(self, text: str):
        """
        Converte texto em áudio e reproduz via FreeSWITCH

        Salva o áudio em arquivo e usa uuid_broadcast para playback
        """
        if not self.is_running or not self.murf:
            return

        try:
            logger.info("Gerando áudio TTS", call_id=self.call_id, text=text[:50])

            # Gerar áudio com Murf (retorna L16 8kHz mono)
            audio_data = await self.murf.text_to_speech(text)

            if audio_data:
                print(f"[TTS] Áudio gerado: {len(audio_data)} bytes", flush=True)

                # Salvar áudio em arquivo WAV
                filepath_app, filepath_fs = await self._save_audio_file(audio_data)

                if filepath_app and filepath_fs:
                    # Reproduzir via uuid_broadcast
                    await self._play_audio_file(filepath_app, filepath_fs, len(audio_data))

                    logger.info(
                        "Áudio enviado para playback via arquivo",
                        call_id=self.call_id,
                        audio_file=filepath_fs,
                        audio_bytes=len(audio_data)
                    )
            else:
                logger.warning("Falha ao gerar áudio TTS", call_id=self.call_id)

        except Exception as e:
            logger.exception("Erro ao gerar/enviar áudio", call_id=self.call_id, error=str(e))
        finally:
            # Transição: SPEAKING → IDLE
            self.state = ConversationState.IDLE
            logger.debug(f"Estado: IDLE (pronto para próxima entrada)", call_id=self.call_id)

    async def _save_audio_file(self, audio_data: bytes) -> tuple[Optional[str], Optional[str]]:
        """Salva áudio raw PCM como arquivo WAV

        Returns:
            Tuple de (caminho_app, caminho_freeswitch) ou (None, None) em caso de erro
        """
        try:
            # Gerar nome único para o arquivo
            filename = f"tts_{uuid_lib.uuid4().hex[:8]}.wav"
            filepath_app = os.path.join(AUDIO_TMP_DIR_APP, filename)
            filepath_fs = os.path.join(AUDIO_TMP_DIR_FS, filename)

            # Criar diretório se não existir
            os.makedirs(AUDIO_TMP_DIR_APP, exist_ok=True)

            # Criar arquivo WAV com o PCM data
            with wave.open(filepath_app, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(8000)  # 8kHz
                wav_file.writeframes(audio_data)

            print(f"[TTS] Arquivo salvo: {filepath_app}", flush=True)
            return filepath_app, filepath_fs

        except Exception as e:
            logger.exception("Erro ao salvar arquivo de áudio", error=str(e))
            return None, None

    async def _play_audio_file(self, filepath_app: str, filepath_fs: str, audio_size: int):
        """Reproduz arquivo de áudio via FreeSWITCH ESL

        Usa conexão TCP ao ESL do FreeSWITCH (porta 8021)
        """
        try:
            print(f"[TTS] Executando playback para UUID {self.freeswitch_uuid}", flush=True)

            # Conectar ao ESL do FreeSWITCH
            reader, writer = await asyncio.open_connection('127.0.0.1', 8021)

            # Ler banner inicial
            await reader.readuntil(b'\n\n')

            # Autenticar
            writer.write(b'auth ClueCon\n\n')
            await writer.drain()
            auth_response = await reader.readuntil(b'\n\n')

            if b'+OK' not in auth_response:
                print(f"[TTS] Erro na autenticação ESL", flush=True)
                writer.close()
                await writer.wait_closed()
                return

            # Enviar comando uuid_broadcast
            cmd = f"api uuid_broadcast {self.freeswitch_uuid} {filepath_fs} aleg\n\n"
            writer.write(cmd.encode())
            await writer.drain()

            # Ler header da resposta ESL
            header = await reader.readuntil(b'\n\n')
            header_str = header.decode()

            # Extrair Content-Length e ler body
            content_length = 0
            for line in header_str.split('\n'):
                if line.startswith('Content-Length:'):
                    content_length = int(line.split(':')[1].strip())
                    break

            body = b''
            if content_length > 0:
                body = await reader.readexactly(content_length)

            result = body.decode().strip() if body else header_str.strip()
            print(f"[TTS] Resposta ESL: {result}", flush=True)

            # Fechar conexão
            writer.close()
            await writer.wait_closed()

            if '+OK' in result or 'Broadcast' in result:
                print(f"[TTS] Playback iniciado com sucesso!", flush=True)

                # Estimar duração do áudio (PCM 8kHz 16-bit mono)
                duration_seconds = audio_size / (8000 * 2) + 1  # +1 buffer

                # Aguardar o áudio tocar antes de limpar
                await asyncio.sleep(duration_seconds)
            else:
                print(f"[TTS] Erro no playback: {result}", flush=True)

            # Limpar arquivo
            try:
                os.remove(filepath_app)
            except:
                pass

        except Exception as e:
            logger.exception("Erro ao reproduzir áudio via ESL", error=str(e))

    def get_status(self) -> dict:
        """Retorna status da chamada"""
        return {
            "call_id": self.call_id,
            "caller": self.caller_number,
            "called": self.called_number,
            "duration": time.time() - self.start_time,
            "is_speaking": self.is_speaking,
            "messages": len(self.conversation_history)
        }
