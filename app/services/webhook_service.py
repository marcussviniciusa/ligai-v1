"""
Webhook service - dispatch events to configured endpoints
"""

import asyncio
import hashlib
import hmac
import json
from datetime import datetime
from typing import Optional

import aiohttp
import structlog

logger = structlog.get_logger(__name__)

# Supported events
SUPPORTED_EVENTS = [
    "call.started",
    "call.ended",
    "call.failed",
    "call.state_changed",
]

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 5, 15]  # Exponential backoff: 1s, 5s, 15s


async def dispatch_event(event_type: str, payload: dict) -> None:
    """
    Dispatch event to all configured webhooks.
    Runs in background - does not block the caller.
    """
    asyncio.create_task(_dispatch_event_async(event_type, payload))


async def _dispatch_event_async(event_type: str, payload: dict) -> None:
    """Internal: dispatch event to all active webhooks"""
    from db.database import AsyncSessionLocal
    from db import crud

    try:
        async with AsyncSessionLocal() as db:
            configs = await crud.get_active_webhook_configs(db, event_type)

            for config in configs:
                asyncio.create_task(
                    _send_webhook(
                        config.id,
                        config.url,
                        config.secret,
                        event_type,
                        payload
                    )
                )
    except Exception as e:
        logger.exception("Error dispatching webhook event", error=str(e))


async def _send_webhook(
    config_id: int,
    url: str,
    secret: Optional[str],
    event_type: str,
    payload: dict,
    attempt: int = 1
) -> None:
    """Send webhook with retry logic"""
    full_payload = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": payload,
    }
    payload_json = json.dumps(full_payload, ensure_ascii=False)

    headers = {"Content-Type": "application/json"}

    # Add HMAC signature if secret configured
    if secret:
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=payload_json,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                success = 200 <= response.status < 300
                response_body = await response.text()

                # Log the attempt
                await _log_webhook(
                    config_id, event_type, payload_json,
                    response.status, response_body, attempt, success
                )

                if not success and attempt < MAX_RETRIES:
                    logger.warning(
                        "Webhook failed, retrying",
                        url=url,
                        status=response.status,
                        attempt=attempt
                    )
                    await asyncio.sleep(RETRY_DELAYS[attempt - 1])
                    await _send_webhook(
                        config_id, url, secret, event_type, payload, attempt + 1
                    )
                elif success:
                    logger.info(
                        "Webhook delivered successfully",
                        url=url,
                        event_name=event_type
                    )

    except Exception as e:
        logger.error("Webhook request failed", url=url, error=str(e))
        await _log_webhook(
            config_id, event_type, payload_json,
            None, None, attempt, False, str(e)
        )

        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAYS[attempt - 1])
            await _send_webhook(
                config_id, url, secret, event_type, payload, attempt + 1
            )


async def _log_webhook(
    config_id: int,
    event_type: str,
    payload: str,
    status_code: Optional[int],
    response_body: Optional[str],
    attempt: int,
    success: bool,
    error_message: Optional[str] = None
) -> None:
    """Log webhook delivery attempt"""
    from db.database import AsyncSessionLocal
    from db import crud

    try:
        async with AsyncSessionLocal() as db:
            await crud.create_webhook_log(
                db,
                config_id=config_id,
                event_type=event_type,
                payload=payload,
                status_code=status_code,
                response_body=response_body[:1000] if response_body else None,
                attempt=attempt,
                success=success,
                error_message=error_message,
            )
            await db.commit()
    except Exception as e:
        logger.error("Failed to log webhook", error=str(e))


async def send_test_webhook(webhook_id: int) -> dict:
    """Send a test event to a webhook"""
    from db.database import AsyncSessionLocal
    from db import crud

    async with AsyncSessionLocal() as db:
        config = await crud.get_webhook_config(db, webhook_id)
        if not config:
            return {"success": False, "message": "Webhook not found"}

    test_payload = {
        "event": "test",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "message": "This is a test webhook from LigAI",
            "webhook_id": webhook_id,
        },
    }
    payload_json = json.dumps(test_payload, ensure_ascii=False)

    headers = {"Content-Type": "application/json"}

    if config.secret:
        signature = hmac.new(
            config.secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                config.url,
                data=payload_json,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                success = 200 <= response.status < 300
                return {
                    "success": success,
                    "status_code": response.status,
                    "message": "Test delivered" if success else f"HTTP {response.status}"
                }
    except Exception as e:
        return {"success": False, "message": str(e)}
