#!/usr/bin/env python3
"""
LigAI - Sistema de Ligação com Inteligência Artificial
Servidor WebSocket principal para processamento de chamadas
"""

import asyncio
import json
import os
import signal
import sys
from typing import Optional

import structlog
import uvloop
import websockets

from call_handler import CallHandler, initialize_fillers
from config import settings

# Configurar logging
import logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
print("LigAI iniciando...", flush=True)

# Armazena chamadas ativas
active_calls: dict[str, CallHandler] = {}


async def handle_connection(websocket):
    """
    Gerencia uma conexão WebSocket do FreeSWITCH

    O FreeSWITCH envia áudio via mod_audio_fork e recebe áudio de volta.

    Protocolo mod_audio_fork:
    - Primeira mensagem: JSON com metadata (ou texto simples)
    - Mensagens seguintes: áudio binário L16 8kHz mono
    - Resposta: áudio binário para playback
    """
    print(f"[WS] Nova conexão recebida!", flush=True)
    call_id: Optional[str] = None
    freeswitch_uuid: Optional[str] = None
    handler: Optional[CallHandler] = None

    try:
        # Extrair UUID do FreeSWITCH do path da URL (ex: /uuid-aqui)
        ws_path = websocket.request.path if hasattr(websocket, 'request') else getattr(websocket, 'path', '/')
        print(f"[WS] Path: {ws_path}", flush=True)
        if ws_path and ws_path != '/' and len(ws_path) > 1:
            freeswitch_uuid = ws_path.strip('/')
            print(f"[WS] FreeSWITCH UUID extraído do path: {freeswitch_uuid}", flush=True)

        # Primeira mensagem contém metadata
        initial_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        print(f"[WS] Primeira mensagem: {type(initial_msg)} - {len(initial_msg) if hasattr(initial_msg, '__len__') else 'N/A'} bytes", flush=True)

        # Tentar parsear como JSON primeiro
        if isinstance(initial_msg, str):
            try:
                metadata = json.loads(initial_msg)
                call_id = metadata.get("uuid") or metadata.get("call_id") or freeswitch_uuid or f"call_{id(websocket)}"
                if not freeswitch_uuid:
                    freeswitch_uuid = metadata.get("uuid")
            except json.JSONDecodeError:
                call_id = freeswitch_uuid or initial_msg.strip()
        elif isinstance(initial_msg, bytes):
            # Pode ser áudio já, usar UUID do path ou ID genérico
            call_id = freeswitch_uuid or f"call_{id(websocket)}"
        else:
            call_id = freeswitch_uuid or f"call_{id(websocket)}"

        # Se não temos UUID do FreeSWITCH, usar call_id
        if not freeswitch_uuid:
            freeswitch_uuid = call_id

        logger.info(
            "Nova chamada recebida via mod_audio_fork",
            call_id=call_id,
            freeswitch_uuid=freeswitch_uuid
        )

        # Criar handler para esta chamada
        handler = CallHandler(
            call_id=call_id,
            caller_number="unknown",  # mod_audio_stream não envia caller_id
            called_number="unknown",
            websocket=websocket,
            freeswitch_uuid=freeswitch_uuid
        )
        active_calls[call_id] = handler

        # Iniciar o handler (conecta ao Deepgram, etc)
        await handler.start()

        logger.info("Handler iniciado, aguardando áudio...", call_id=call_id)

        # Loop principal de processamento de áudio
        async for message in websocket:
            if isinstance(message, bytes):
                # Áudio recebido do FreeSWITCH (L16 8kHz mono)
                await handler.process_audio(message)
            else:
                # Mensagem de controle/texto do mod_audio_stream
                try:
                    data = json.loads(message)
                    event_type = data.get("type") or data.get("event")

                    if event_type in ("disconnect", "hangup", "stop"):
                        logger.info("Chamada encerrada", call_id=call_id)
                        break
                    elif event_type == "dtmf":
                        digit = data.get("digit")
                        logger.info("DTMF recebido", call_id=call_id, digit=digit)
                        await handler.handle_dtmf(digit)
                    else:
                        logger.debug("Mensagem recebida", call_id=call_id, data=data)

                except json.JSONDecodeError:
                    # Pode ser texto simples (logs, etc)
                    logger.debug("Texto recebido", call_id=call_id, message=message)

    except websockets.exceptions.ConnectionClosed:
        logger.info("Conexão WebSocket fechada", call_id=call_id)
    except asyncio.TimeoutError:
        logger.error("Timeout aguardando metadata inicial", call_id=call_id)
    except Exception as e:
        logger.exception("Erro no processamento da chamada", call_id=call_id, error=str(e))
    finally:
        # Cleanup
        if handler:
            await handler.stop()
        if call_id and call_id in active_calls:
            del active_calls[call_id]
        logger.info("Chamada finalizada", call_id=call_id)


async def health_check_handler(websocket):
    """Handler para health checks"""
    await websocket.send(json.dumps({
        "status": "healthy",
        "active_calls": len(active_calls)
    }))


async def main():
    """Função principal do servidor"""

    # Usar uvloop para melhor performance
    uvloop.install()

    host = settings.WEBSOCKET_HOST
    port = settings.WEBSOCKET_PORT

    logger.info(f"Iniciando LigAI WebSocket Server em {host}:{port}")

    # Pré-gerar áudios de filler para reduzir latência
    await initialize_fillers()

    # Configurar shutdown graceful
    stop = asyncio.Event()

    def signal_handler():
        logger.info("Recebido sinal de shutdown")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    async with websockets.serve(
        handle_connection,
        host,
        port,
        ping_interval=30,
        ping_timeout=10,
        max_size=10 * 1024 * 1024,  # 10MB max message size
        compression=None  # Desabilitar compressão para áudio
    ):
        logger.info("Servidor WebSocket iniciado com sucesso")
        await stop.wait()

    # Encerrar todas as chamadas ativas
    logger.info(f"Encerrando {len(active_calls)} chamadas ativas...")
    for call_id, handler in list(active_calls.items()):
        await handler.stop()

    logger.info("Servidor encerrado")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Servidor interrompido pelo usuário")
        sys.exit(0)
