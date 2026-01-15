"""
Campaign service - manages batch dialing campaigns
"""

import asyncio
import csv
import io
import json
from datetime import datetime
from typing import List, Optional, Dict

import structlog

from config import settings

logger = structlog.get_logger(__name__)

# Active campaign tasks
_active_campaigns: Dict[int, asyncio.Task] = {}


async def start_campaign(campaign_id: int) -> bool:
    """Start or resume a campaign"""
    from db.database import AsyncSessionLocal
    from db import crud

    if campaign_id in _active_campaigns:
        logger.warning("Campaign already running", campaign_id=campaign_id)
        return False

    async with AsyncSessionLocal() as db:
        campaign = await crud.get_campaign(db, campaign_id)
        if not campaign:
            return False

        if campaign.status not in ("pending", "paused"):
            logger.warning(
                "Cannot start campaign with status",
                campaign_id=campaign_id,
                status=campaign.status
            )
            return False

        await crud.update_campaign(
            db, campaign_id,
            status="running",
            started_at=datetime.utcnow() if campaign.status == "pending" else None
        )
        await db.commit()

    # Start execution task
    task = asyncio.create_task(_run_campaign(campaign_id))
    _active_campaigns[campaign_id] = task

    logger.info("Campaign started", campaign_id=campaign_id)
    return True


async def pause_campaign(campaign_id: int) -> bool:
    """Pause a running campaign"""
    from db.database import AsyncSessionLocal
    from db import crud

    if campaign_id not in _active_campaigns:
        return False

    # Cancel the task
    _active_campaigns[campaign_id].cancel()
    del _active_campaigns[campaign_id]

    async with AsyncSessionLocal() as db:
        await crud.update_campaign(db, campaign_id, status="paused")
        await db.commit()

    logger.info("Campaign paused", campaign_id=campaign_id)
    return True


def is_campaign_running(campaign_id: int) -> bool:
    """Check if a campaign is currently running"""
    return campaign_id in _active_campaigns


async def _run_campaign(campaign_id: int):
    """Main campaign execution loop"""
    from db.database import AsyncSessionLocal
    from db import crud
    from services.dialer_service import initiate_call
    from services.webhook_service import dispatch_event
    from state import active_calls

    try:
        while True:
            async with AsyncSessionLocal() as db:
                campaign = await crud.get_campaign(db, campaign_id)

                if not campaign or campaign.status != "running":
                    logger.info(
                        "Campaign no longer running",
                        campaign_id=campaign_id,
                        status=campaign.status if campaign else "deleted"
                    )
                    break

                # Check global call limit
                current_active = len(active_calls)
                if current_active >= settings.MAX_CONCURRENT_CALLS:
                    logger.debug(
                        "Max concurrent calls reached",
                        active=current_active,
                        max=settings.MAX_CONCURRENT_CALLS
                    )
                    await asyncio.sleep(5)
                    continue

                # Count active calls for this campaign
                campaign_active = await crud.count_campaign_active_calls(
                    db, campaign_id
                )

                # Check campaign concurrency limit
                if campaign_active >= campaign.max_concurrent:
                    logger.debug(
                        "Campaign max concurrent reached",
                        campaign_id=campaign_id,
                        active=campaign_active,
                        max=campaign.max_concurrent
                    )
                    await asyncio.sleep(5)
                    continue

                # Get next pending contact
                contact = await crud.get_next_pending_contact(db, campaign_id)

                if not contact:
                    # Campaign completed
                    await crud.update_campaign(
                        db, campaign_id,
                        status="completed",
                        completed_at=datetime.utcnow()
                    )
                    await db.commit()

                    logger.info("Campaign completed", campaign_id=campaign_id)

                    # Dispatch webhook
                    await dispatch_event("campaign.completed", {
                        "campaign_id": campaign_id,
                        "name": campaign.name,
                        "total_contacts": campaign.total_contacts,
                        "completed_contacts": campaign.completed_contacts,
                        "failed_contacts": campaign.failed_contacts,
                    })
                    break

                # Mark contact as calling
                await crud.update_campaign_contact(
                    db, contact.id,
                    status="calling",
                    attempts=contact.attempts + 1,
                    last_attempt_at=datetime.utcnow()
                )
                await db.commit()

                # Get prompt config
                prompt_config = None
                if campaign.prompt_id:
                    prompt = await crud.get_prompt(db, campaign.prompt_id)
                    if prompt:
                        prompt_config = prompt.to_dict()

                # Initiate call
                try:
                    call_id = await initiate_call(contact.phone_number, prompt_config)

                    if call_id:
                        await crud.update_campaign_contact(
                            db, contact.id,
                            call_id=call_id
                        )
                        await db.commit()

                        # Start task to wait for call completion
                        asyncio.create_task(
                            _wait_for_call_completion(campaign_id, contact.id, call_id)
                        )

                        logger.info(
                            "Campaign call initiated",
                            campaign_id=campaign_id,
                            contact_id=contact.id,
                            call_id=call_id
                        )
                    else:
                        await crud.update_campaign_contact(
                            db, contact.id,
                            status="failed",
                            error_message="Failed to initiate call"
                        )
                        await _update_campaign_stats(db, campaign_id)
                        await db.commit()

                except Exception as e:
                    logger.exception(
                        "Error initiating campaign call",
                        contact_id=contact.id,
                        error=str(e)
                    )
                    await crud.update_campaign_contact(
                        db, contact.id,
                        status="failed",
                        error_message=str(e)
                    )
                    await db.commit()

            # Small delay between calls
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("Campaign task cancelled", campaign_id=campaign_id)
    except Exception as e:
        logger.exception("Error in campaign loop", campaign_id=campaign_id, error=str(e))
    finally:
        if campaign_id in _active_campaigns:
            del _active_campaigns[campaign_id]


async def _wait_for_call_completion(
    campaign_id: int,
    contact_id: int,
    call_id: str
):
    """Wait for a call to complete and update contact status"""
    from state import active_calls
    from db.database import AsyncSessionLocal
    from db import crud

    # Poll for call completion
    max_wait = 3600  # 1 hour max
    waited = 0

    while waited < max_wait:
        if call_id not in active_calls:
            break
        await asyncio.sleep(5)
        waited += 5

    # Update contact status
    async with AsyncSessionLocal() as db:
        await crud.update_campaign_contact(
            db, contact_id,
            status="completed",
            completed_at=datetime.utcnow()
        )
        await _update_campaign_stats(db, campaign_id)
        await db.commit()

    logger.info(
        "Campaign contact completed",
        campaign_id=campaign_id,
        contact_id=contact_id
    )


async def _update_campaign_stats(db, campaign_id: int):
    """Update campaign statistics"""
    from db import crud

    stats = await crud.get_campaign_contact_stats(db, campaign_id)
    await crud.update_campaign(
        db, campaign_id,
        completed_contacts=stats["completed"],
        failed_contacts=stats["failed"],
    )


def parse_csv_contacts(csv_content: str) -> List[Dict]:
    """Parse CSV content to list of contacts"""
    contacts = []

    try:
        # Try to detect delimiter
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(csv_content[:1024], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(csv_content), dialect=dialect)

    for row in reader:
        # Try common column names for phone
        phone = (
            row.get("phone_number") or
            row.get("phone") or
            row.get("telefone") or
            row.get("numero") or
            row.get("number")
        )

        if not phone:
            continue

        # Clean phone number
        phone = "".join(filter(str.isdigit, str(phone)))
        if len(phone) < 10:
            continue

        # Try common column names for name
        name = (
            row.get("name") or
            row.get("nome") or
            row.get("cliente") or
            row.get("contact")
        )

        # Extra data - everything else
        extra = {
            k: v for k, v in row.items()
            if k.lower() not in (
                "phone_number", "phone", "telefone", "numero", "number",
                "name", "nome", "cliente", "contact"
            ) and v
        }

        contacts.append({
            "phone_number": phone,
            "name": name,
            "extra_data": json.dumps(extra) if extra else None,
        })

    return contacts
