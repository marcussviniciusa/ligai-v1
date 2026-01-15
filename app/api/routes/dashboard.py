"""
Dashboard WebSocket route for real-time updates
"""

import asyncio
import json
from typing import Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


class DashboardBroadcaster:
    """
    Manages WebSocket connections for dashboard real-time updates.
    Singleton pattern - use the global `broadcaster` instance.
    """

    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            self.connections.add(websocket)
        logger.info("Dashboard client connected", total_connections=len(self.connections))

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        async with self._lock:
            self.connections.discard(websocket)
        logger.info("Dashboard client disconnected", total_connections=len(self.connections))

    async def broadcast(self, event_type: str, data: dict):
        """
        Broadcast a message to all connected dashboard clients.

        Args:
            event_type: Type of event (call_started, call_ended, etc.)
            data: Event data to send
        """
        if not self.connections:
            return

        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Send to all connections, remove any that fail
        disconnected = set()
        async with self._lock:
            for websocket in self.connections:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.warning("Failed to send to dashboard client", error=str(e))
                    disconnected.add(websocket)

            # Clean up disconnected clients
            self.connections -= disconnected

    async def send_to(self, websocket: WebSocket, event_type: str, data: dict):
        """Send a message to a specific WebSocket connection"""
        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.warning("Failed to send to specific client", error=str(e))


# Global broadcaster instance
broadcaster = DashboardBroadcaster()


# === Event helper functions (to be called from CallHandler) ===

async def emit_call_started(call_id: str, data: dict):
    """Emit when a new call starts"""
    await broadcaster.broadcast("call_started", {
        "call_id": call_id,
        **data,
    })


async def emit_call_state_changed(call_id: str, state: str, duration: float, message_count: int):
    """Emit when call state changes"""
    await broadcaster.broadcast("call_state_changed", {
        "call_id": call_id,
        "state": state,
        "duration": duration,
        "message_count": message_count,
    })


async def emit_call_ended(call_id: str, duration: float, summary: str = None):
    """Emit when a call ends"""
    await broadcaster.broadcast("call_ended", {
        "call_id": call_id,
        "duration": duration,
        "summary": summary,
    })


async def emit_stats_updated():
    """Emit updated statistics"""
    from db.database import AsyncSessionLocal
    from db import crud

    async with AsyncSessionLocal() as db:
        stats = await crud.get_call_stats(db)

    # Add active calls count from memory
    from state import active_calls
    stats["active_calls"] = len(active_calls)

    await broadcaster.broadcast("stats_updated", stats)


# === WebSocket Route ===

@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard real-time updates.

    Clients connect here to receive:
    - call_started: When a new call begins
    - call_state_changed: When call state changes (idle/processing/speaking)
    - call_ended: When a call finishes
    - stats_updated: Periodic statistics updates
    """
    await broadcaster.connect(websocket)

    try:
        # Send initial stats on connection
        await emit_stats_updated()

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (ping/pong or commands)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 second timeout for ping
                )

                # Handle client messages
                try:
                    message = json.loads(data)
                    msg_type = message.get("type")

                    if msg_type == "ping":
                        await broadcaster.send_to(websocket, "pong", {})
                    elif msg_type == "get_stats":
                        from db.database import AsyncSessionLocal
                        from db import crud
                        from state import active_calls
                        async with AsyncSessionLocal() as db:
                            stats = await crud.get_call_stats(db)
                        stats["active_calls"] = len(active_calls)
                        await broadcaster.send_to(websocket, "stats", stats)

                except json.JSONDecodeError:
                    pass

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("Dashboard WebSocket error", error=str(e))
    finally:
        await broadcaster.disconnect(websocket)
