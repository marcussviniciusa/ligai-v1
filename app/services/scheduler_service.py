"""
Scheduler service - executes scheduled calls
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import structlog

from config import settings

logger = structlog.get_logger(__name__)

# Control flags
_scheduler_running = False
_scheduler_task: Optional[asyncio.Task] = None


async def start_scheduler():
    """Start the scheduler background task"""
    global _scheduler_running, _scheduler_task

    if _scheduler_running:
        logger.warning("Scheduler already running")
        return

    _scheduler_running = True
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("Scheduler started")


async def stop_scheduler():
    """Stop the scheduler background task"""
    global _scheduler_running, _scheduler_task

    _scheduler_running = False
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None

    logger.info("Scheduler stopped")


async def _scheduler_loop():
    """Main scheduler loop - checks for due calls every 10 seconds"""
    while _scheduler_running:
        try:
            await _process_due_calls()
        except Exception as e:
            logger.exception("Error in scheduler loop", error=str(e))

        await asyncio.sleep(10)


async def _process_due_calls():
    """Process all calls that are due"""
    from db.database import AsyncSessionLocal
    from db import crud
    from services.dialer_service import initiate_call
    from services.webhook_service import dispatch_event
    from state import active_calls

    async with AsyncSessionLocal() as db:
        # Get calls due in the next minute
        due_calls = await crud.get_due_scheduled_calls(
            db,
            until=datetime.utcnow() + timedelta(minutes=1)
        )

        for scheduled_call in due_calls:
            # Check concurrent call limit
            if len(active_calls) >= settings.MAX_CONCURRENT_CALLS:
                logger.warning(
                    "Max concurrent calls reached, skipping scheduled call",
                    scheduled_id=scheduled_call.id
                )
                continue

            # Mark as executing
            await crud.update_scheduled_call(
                db, scheduled_call.id, status="executing"
            )
            await db.commit()

            # Get prompt config
            prompt_config = None
            if scheduled_call.prompt_id:
                prompt = await crud.get_prompt(db, scheduled_call.prompt_id)
                if prompt:
                    prompt_config = prompt.to_dict()

            # Initiate the call
            try:
                call_id = await initiate_call(
                    scheduled_call.phone_number,
                    prompt_config
                )

                if call_id:
                    await crud.update_scheduled_call(
                        db, scheduled_call.id,
                        status="completed",
                        call_id=call_id
                    )
                    logger.info(
                        "Scheduled call executed",
                        scheduled_id=scheduled_call.id,
                        call_id=call_id
                    )
                else:
                    await crud.update_scheduled_call(
                        db, scheduled_call.id,
                        status="failed"
                    )
                    logger.error(
                        "Scheduled call failed to initiate",
                        scheduled_id=scheduled_call.id
                    )

            except Exception as e:
                await crud.update_scheduled_call(
                    db, scheduled_call.id,
                    status="failed"
                )
                logger.exception(
                    "Error executing scheduled call",
                    scheduled_id=scheduled_call.id,
                    error=str(e)
                )

            await db.commit()
