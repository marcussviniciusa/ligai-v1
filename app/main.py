#!/usr/bin/env python3
"""
LigAI - Sistema de Ligação com Inteligência Artificial
Servidor principal com FastAPI + WebSocket para processamento de chamadas
"""

import asyncio
import json
import os
import sys
from typing import Optional
from contextlib import asynccontextmanager

import structlog
import uvloop
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from call_handler import CallHandler, initialize_fillers
from config import settings
from db.database import init_db, close_db

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

# Import shared state
from state import active_calls, pending_call_configs, pending_call_numbers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    uvloop.install()
    logger.info("Iniciando LigAI...")

    # Initialize database
    await init_db()

    # Pre-generate filler audio
    await initialize_fillers()

    # Start scheduler for scheduled calls
    from services.scheduler_service import start_scheduler, stop_scheduler
    await start_scheduler()

    logger.info("LigAI iniciado com sucesso")
    yield

    # Shutdown
    logger.info("Encerrando LigAI...")

    # Stop scheduler
    await stop_scheduler()

    # Close all active calls
    logger.info(f"Encerrando {len(active_calls)} chamadas ativas...")
    for call_id, handler in list(active_calls.items()):
        await handler.stop()

    # Close database
    await close_db()

    logger.info("LigAI encerrado")


# Create FastAPI app
app = FastAPI(
    title="LigAI API",
    description="Sistema de Ligação com Inteligência Artificial",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api-docs",      # Swagger UI em /api-docs
    redoc_url="/api-redoc",    # ReDoc em /api-redoc
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
from api.routes import prompts, calls, dashboard, webhooks, schedules, campaigns
from api.routes import settings as settings_routes

app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
app.include_router(calls.router, prefix="/api/v1/calls", tags=["calls"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(schedules.router, prefix="/api/v1/schedules", tags=["schedules"])
app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(settings_routes.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(dashboard.router, tags=["dashboard"])


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ligai",
        "active_calls": len(active_calls),
    }


@app.get("/api/v1/stats")
async def get_stats():
    """Get system statistics"""
    from db.database import AsyncSessionLocal
    from db import crud

    async with AsyncSessionLocal() as db:
        stats = await crud.get_call_stats(db)
        stats["active_calls"] = len(active_calls)
        stats["max_concurrent_calls"] = settings.MAX_CONCURRENT_CALLS
        return stats


# WebSocket endpoint for FreeSWITCH audio
@app.websocket("/ws/{uuid}")
@app.websocket("/")
async def freeswitch_websocket(websocket: WebSocket, uuid: Optional[str] = None):
    """
    WebSocket endpoint for FreeSWITCH mod_audio_fork connections.

    Protocol:
    - First message: JSON metadata or plain text
    - Following messages: Binary audio L16 8kHz mono
    - Response: Binary audio for playback
    """
    await websocket.accept()

    print(f"[WS] Nova conexão recebida! UUID: {uuid}", flush=True)
    call_id: Optional[str] = None
    freeswitch_uuid: Optional[str] = uuid
    handler: Optional[CallHandler] = None

    try:
        # First message contains metadata
        initial_msg = await asyncio.wait_for(websocket.receive(), timeout=10.0)
        print(f"[WS] Primeira mensagem recebida", flush=True)

        # Handle different message types
        if "text" in initial_msg:
            msg_data = initial_msg["text"]
            try:
                metadata = json.loads(msg_data)
                call_id = metadata.get("uuid") or metadata.get("call_id") or freeswitch_uuid or f"call_{id(websocket)}"
                if not freeswitch_uuid:
                    freeswitch_uuid = metadata.get("uuid")
            except json.JSONDecodeError:
                call_id = freeswitch_uuid or msg_data.strip()
        elif "bytes" in initial_msg:
            # Already audio, use UUID from path or generic ID
            call_id = freeswitch_uuid or f"call_{id(websocket)}"
        else:
            call_id = freeswitch_uuid or f"call_{id(websocket)}"

        # If no FreeSWITCH UUID, use call_id
        if not freeswitch_uuid:
            freeswitch_uuid = call_id

        logger.info(
            "Nova chamada recebida via mod_audio_fork",
            call_id=call_id,
            freeswitch_uuid=freeswitch_uuid
        )

        # Check if we have a pending prompt config for this call
        prompt_config = pending_call_configs.pop(call_id, None)

        # Get called_number from pending config if available
        called_number = "unknown"
        if call_id in pending_call_numbers:
            called_number = pending_call_numbers.pop(call_id)

        # Create handler for this call
        handler = CallHandler(
            call_id=call_id,
            caller_number="unknown",
            called_number=called_number,
            websocket=websocket,
            freeswitch_uuid=freeswitch_uuid,
            prompt_config=prompt_config,
        )
        active_calls[call_id] = handler

        # Save call to database
        call_db_id = None
        try:
            from db.database import AsyncSessionLocal
            from db import crud
            from datetime import datetime

            async with AsyncSessionLocal() as db:
                prompt_id = prompt_config.get("id") if prompt_config else None
                call_record = await crud.create_call(
                    db,
                    call_id=call_id,
                    freeswitch_uuid=freeswitch_uuid,
                    called_number=called_number,
                    prompt_id=prompt_id,
                    status="active",
                    direction="outbound",
                    start_time=datetime.utcnow(),
                )
                call_db_id = call_record.id
                await db.commit()
                logger.info("Chamada salva no banco", call_id=call_id, db_id=call_db_id)
        except Exception as e:
            logger.error("Erro ao salvar chamada no banco", error=str(e))

        # Emit call started event to dashboard
        from api.routes.dashboard import emit_call_started
        await emit_call_started(call_id, {
            "freeswitch_uuid": freeswitch_uuid,
            "called_number": called_number,
            "start_time": handler.start_time.isoformat() if handler.start_time else None,
        })

        # Dispatch webhook event
        from services.webhook_service import dispatch_event
        await dispatch_event("call.started", {
            "call_id": call_id,
            "called_number": called_number,
            "start_time": handler.start_time.isoformat() if handler.start_time else None,
        })

        # Start the handler (connects to Deepgram, etc)
        await handler.start()

        logger.info("Handler iniciado, aguardando áudio...", call_id=call_id)

        # Main audio processing loop
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                # Audio received from FreeSWITCH (L16 8kHz mono)
                await handler.process_audio(message["bytes"])
            elif "text" in message:
                # Control/text message from mod_audio_stream
                try:
                    data = json.loads(message["text"])
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
                    logger.debug("Texto recebido", call_id=call_id, message=message["text"])

    except WebSocketDisconnect:
        logger.info("Conexão WebSocket fechada", call_id=call_id)
    except asyncio.TimeoutError:
        logger.error("Timeout aguardando metadata inicial", call_id=call_id)
    except Exception as e:
        logger.exception("Erro no processamento da chamada", call_id=call_id, error=str(e))
    finally:
        # Emit call ended event to dashboard
        duration = 0
        transcript = []
        if handler:
            from api.routes.dashboard import emit_call_ended
            duration = handler.get_duration() if hasattr(handler, 'get_duration') else 0
            await emit_call_ended(call_id, duration)

            # Get transcript for webhook
            if hasattr(handler, 'conversation_history'):
                transcript = [
                    {"role": m.get("role", "unknown"), "content": m.get("content", "")}
                    for m in handler.conversation_history
                ]

        # Update call in database
        try:
            from db.database import AsyncSessionLocal
            from db import crud

            async with AsyncSessionLocal() as db:
                await crud.end_call(db, call_id)
                await db.commit()
                logger.info("Chamada atualizada no banco", call_id=call_id, duration=duration)
        except Exception as e:
            logger.error("Erro ao atualizar chamada no banco", error=str(e))

        # Dispatch webhook event
        try:
            from services.webhook_service import dispatch_event
            await dispatch_event("call.ended", {
                "call_id": call_id,
                "duration": duration,
                "transcript": transcript,
            })
        except Exception as e:
            logger.error("Erro ao enviar webhook call.ended", error=str(e))

        # Cleanup
        if handler:
            await handler.stop()
        if call_id and call_id in active_calls:
            del active_calls[call_id]
        logger.info("Chamada finalizada", call_id=call_id)


# Serve static files and SPA fallback
STATIC_DIR = "/app/static"
INDEX_FILE = f"{STATIC_DIR}/index.html"

# Check if static files exist (production build)
if os.path.exists(STATIC_DIR) and os.path.isdir(STATIC_DIR):
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=f"{STATIC_DIR}/assets"), name="assets")

    # SPA fallback - serve index.html for all non-API routes
    @app.get("/{path:path}")
    async def serve_spa(request: Request, path: str):
        # Skip API and WS routes
        if path.startswith("api/") or path.startswith("ws/") or path == "health":
            return None

        # Check if requesting a static file that exists
        static_file = os.path.join(STATIC_DIR, path)
        if os.path.isfile(static_file):
            return FileResponse(static_file)

        # Serve index.html for SPA routing
        if os.path.exists(INDEX_FILE):
            return FileResponse(INDEX_FILE)
        return {"error": "Frontend not built"}


def main():
    """Main entry point"""
    host = settings.WEBSOCKET_HOST
    port = settings.WEB_PORT

    logger.info(f"Iniciando LigAI em {host}:{port}")

    # Also listen on legacy WebSocket port for backwards compatibility
    logger.info(f"WebSocket FreeSWITCH disponível em ws://{host}:{port}/ws/{{uuid}}")
    logger.info(f"Interface web disponível em http://{host}:{port}/")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Servidor interrompido pelo usuário")
        sys.exit(0)
