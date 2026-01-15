"""
CRUD operations for database models
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    Prompt, Call, CallMessage, Setting,
    WebhookConfig, WebhookLog, ScheduledCall, Campaign, CampaignContact
)


# === Prompt CRUD ===

async def get_prompt(db: AsyncSession, prompt_id: int) -> Optional[Prompt]:
    """Get a prompt by ID"""
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    return result.scalar_one_or_none()


async def get_prompt_by_name(db: AsyncSession, name: str) -> Optional[Prompt]:
    """Get a prompt by name"""
    result = await db.execute(select(Prompt).where(Prompt.name == name))
    return result.scalar_one_or_none()


async def get_active_prompt(db: AsyncSession) -> Optional[Prompt]:
    """Get the currently active prompt"""
    result = await db.execute(select(Prompt).where(Prompt.is_active == True))
    return result.scalar_one_or_none()


async def get_prompts(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[Prompt]:
    """List all prompts"""
    result = await db.execute(
        select(Prompt)
        .order_by(Prompt.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_prompt(db: AsyncSession, **kwargs) -> Prompt:
    """Create a new prompt"""
    prompt = Prompt(**kwargs)
    db.add(prompt)
    await db.flush()
    await db.refresh(prompt)
    return prompt


async def update_prompt(
    db: AsyncSession,
    prompt_id: int,
    **kwargs
) -> Optional[Prompt]:
    """Update a prompt"""
    prompt = await get_prompt(db, prompt_id)
    if not prompt:
        return None

    for key, value in kwargs.items():
        if hasattr(prompt, key) and value is not None:
            setattr(prompt, key, value)

    prompt.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(prompt)
    return prompt


async def delete_prompt(db: AsyncSession, prompt_id: int) -> bool:
    """Delete a prompt"""
    result = await db.execute(delete(Prompt).where(Prompt.id == prompt_id))
    return result.rowcount > 0


async def set_active_prompt(db: AsyncSession, prompt_id: int) -> Optional[Prompt]:
    """Set a prompt as active (deactivate all others)"""
    # Deactivate all prompts
    await db.execute(update(Prompt).values(is_active=False))

    # Activate the specified prompt
    prompt = await get_prompt(db, prompt_id)
    if prompt:
        prompt.is_active = True
        await db.flush()
        await db.refresh(prompt)

    return prompt


# === Call CRUD ===

async def get_call(db: AsyncSession, call_id: int) -> Optional[Call]:
    """Get a call by ID"""
    result = await db.execute(
        select(Call)
        .options(selectinload(Call.messages))
        .where(Call.id == call_id)
    )
    return result.scalar_one_or_none()


async def get_call_by_call_id(db: AsyncSession, call_id: str) -> Optional[Call]:
    """Get a call by call_id (string UUID)"""
    result = await db.execute(
        select(Call)
        .options(selectinload(Call.messages))
        .where(Call.call_id == call_id)
    )
    return result.scalar_one_or_none()


async def get_calls(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> List[Call]:
    """List calls with optional filters"""
    query = select(Call).order_by(Call.start_time.desc())

    if status:
        query = query.where(Call.status == status)
    if from_date:
        query = query.where(Call.start_time >= from_date)
    if to_date:
        query = query.where(Call.start_time <= to_date)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_calls(
    db: AsyncSession,
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> int:
    """Count calls with optional filters"""
    query = select(func.count(Call.id))

    if status:
        query = query.where(Call.status == status)
    if from_date:
        query = query.where(Call.start_time >= from_date)
    if to_date:
        query = query.where(Call.start_time <= to_date)

    result = await db.execute(query)
    return result.scalar() or 0


async def create_call(db: AsyncSession, **kwargs) -> Call:
    """Create a new call record"""
    call = Call(**kwargs)
    db.add(call)
    await db.flush()
    await db.refresh(call)
    return call


async def update_call(db: AsyncSession, call_id: str, **kwargs) -> Optional[Call]:
    """Update a call by call_id"""
    call = await get_call_by_call_id(db, call_id)
    if not call:
        return None

    for key, value in kwargs.items():
        if hasattr(call, key) and value is not None:
            setattr(call, key, value)

    await db.flush()
    await db.refresh(call)
    return call


async def end_call(
    db: AsyncSession,
    call_id: str,
    summary: Optional[str] = None
) -> Optional[Call]:
    """Mark a call as ended"""
    call = await get_call_by_call_id(db, call_id)
    if not call:
        return None

    call.status = "completed"
    call.end_time = datetime.utcnow()
    if call.start_time:
        call.duration_seconds = (call.end_time - call.start_time).total_seconds()
    if summary:
        call.summary = summary

    await db.flush()
    await db.refresh(call)
    return call


async def delete_call(db: AsyncSession, call_id: int) -> bool:
    """Delete a call and its messages"""
    result = await db.execute(delete(Call).where(Call.id == call_id))
    return result.rowcount > 0


# === CallMessage CRUD ===

async def add_message(
    db: AsyncSession,
    call_db_id: int,
    role: str,
    content: str,
    audio_duration_ms: Optional[int] = None
) -> CallMessage:
    """Add a message to a call"""
    message = CallMessage(
        call_id=call_db_id,
        role=role,
        content=content,
        audio_duration_ms=audio_duration_ms,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def get_call_messages(
    db: AsyncSession,
    call_db_id: int
) -> List[CallMessage]:
    """Get all messages for a call"""
    result = await db.execute(
        select(CallMessage)
        .where(CallMessage.call_id == call_db_id)
        .order_by(CallMessage.timestamp)
    )
    return list(result.scalars().all())


# === Statistics ===

async def get_call_stats(
    db: AsyncSession,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> dict:
    """Get call statistics"""
    # Count by status
    total_query = select(func.count(Call.id))
    active_query = select(func.count(Call.id)).where(Call.status == "active")
    completed_query = select(func.count(Call.id)).where(Call.status == "completed")

    # Average duration
    avg_duration_query = select(func.avg(Call.duration_seconds)).where(
        Call.duration_seconds.isnot(None)
    )

    if from_date:
        total_query = total_query.where(Call.start_time >= from_date)
        completed_query = completed_query.where(Call.start_time >= from_date)
        avg_duration_query = avg_duration_query.where(Call.start_time >= from_date)

    if to_date:
        total_query = total_query.where(Call.start_time <= to_date)
        completed_query = completed_query.where(Call.start_time <= to_date)
        avg_duration_query = avg_duration_query.where(Call.start_time <= to_date)

    total = (await db.execute(total_query)).scalar() or 0
    active = (await db.execute(active_query)).scalar() or 0
    completed = (await db.execute(completed_query)).scalar() or 0
    avg_duration = (await db.execute(avg_duration_query)).scalar() or 0

    return {
        "total_calls": total,
        "active_calls": active,
        "completed_calls": completed,
        "avg_duration_seconds": round(avg_duration, 1) if avg_duration else 0,
    }


# === Setting CRUD ===

async def get_setting(db: AsyncSession, key: str) -> Optional[Setting]:
    """Get a setting by key"""
    result = await db.execute(select(Setting).where(Setting.key == key))
    return result.scalar_one_or_none()


async def get_setting_value(db: AsyncSession, key: str) -> Optional[str]:
    """Get just the value of a setting by key"""
    setting = await get_setting(db, key)
    return setting.value if setting else None


async def get_all_settings(db: AsyncSession) -> List[Setting]:
    """Get all settings"""
    result = await db.execute(select(Setting).order_by(Setting.key))
    return list(result.scalars().all())


async def upsert_setting(
    db: AsyncSession,
    key: str,
    value: str,
    description: Optional[str] = None,
    is_secret: bool = True
) -> Setting:
    """Create or update a setting"""
    setting = await get_setting(db, key)

    if setting:
        setting.value = value
        if description is not None:
            setting.description = description
        setting.updated_at = datetime.utcnow()
    else:
        setting = Setting(
            key=key,
            value=value,
            description=description,
            is_secret=is_secret,
        )
        db.add(setting)

    await db.flush()
    await db.refresh(setting)
    return setting


async def delete_setting(db: AsyncSession, key: str) -> bool:
    """Delete a setting by key"""
    result = await db.execute(delete(Setting).where(Setting.key == key))
    return result.rowcount > 0


async def init_default_settings(db: AsyncSession) -> None:
    """Initialize default settings if they don't exist"""
    default_settings = [
        {
            "key": "DEEPGRAM_API_KEY",
            "description": "API Key do Deepgram para reconhecimento de voz (STT)",
            "is_secret": True,
        },
        {
            "key": "MURF_API_KEY",
            "description": "API Key do Murf AI para sintese de voz (TTS)",
            "is_secret": True,
        },
        {
            "key": "OPENAI_API_KEY",
            "description": "API Key da OpenAI para processamento de linguagem (LLM)",
            "is_secret": True,
        },
    ]

    for setting_data in default_settings:
        existing = await get_setting(db, setting_data["key"])
        if not existing:
            setting = Setting(
                key=setting_data["key"],
                value="",
                description=setting_data["description"],
                is_secret=setting_data["is_secret"],
            )
            db.add(setting)

    await db.flush()


# === Webhook CRUD ===

async def get_webhook_config(db: AsyncSession, webhook_id: int) -> Optional[WebhookConfig]:
    """Get a webhook config by ID"""
    result = await db.execute(
        select(WebhookConfig).where(WebhookConfig.id == webhook_id)
    )
    return result.scalar_one_or_none()


async def get_webhook_configs(db: AsyncSession) -> List[WebhookConfig]:
    """Get all webhook configs"""
    result = await db.execute(
        select(WebhookConfig).order_by(WebhookConfig.created_at.desc())
    )
    return list(result.scalars().all())


async def get_active_webhook_configs(
    db: AsyncSession,
    event_type: str
) -> List[WebhookConfig]:
    """Get active webhook configs that subscribe to a specific event"""
    result = await db.execute(
        select(WebhookConfig).where(
            WebhookConfig.is_active == True,
            WebhookConfig.events.contains(event_type)
        )
    )
    return list(result.scalars().all())


async def create_webhook_config(db: AsyncSession, **kwargs) -> WebhookConfig:
    """Create a new webhook config"""
    webhook = WebhookConfig(**kwargs)
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


async def update_webhook_config(
    db: AsyncSession,
    webhook_id: int,
    **kwargs
) -> Optional[WebhookConfig]:
    """Update a webhook config"""
    webhook = await get_webhook_config(db, webhook_id)
    if not webhook:
        return None

    for key, value in kwargs.items():
        if hasattr(webhook, key) and value is not None:
            setattr(webhook, key, value)

    webhook.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(webhook)
    return webhook


async def delete_webhook_config(db: AsyncSession, webhook_id: int) -> bool:
    """Delete a webhook config"""
    result = await db.execute(
        delete(WebhookConfig).where(WebhookConfig.id == webhook_id)
    )
    return result.rowcount > 0


async def create_webhook_log(db: AsyncSession, **kwargs) -> WebhookLog:
    """Create a webhook delivery log"""
    log = WebhookLog(**kwargs)
    db.add(log)
    await db.flush()
    return log


async def get_webhook_logs(
    db: AsyncSession,
    config_id: int,
    limit: int = 50
) -> List[WebhookLog]:
    """Get logs for a webhook config"""
    result = await db.execute(
        select(WebhookLog)
        .where(WebhookLog.config_id == config_id)
        .order_by(WebhookLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# === ScheduledCall CRUD ===

async def get_scheduled_call(db: AsyncSession, schedule_id: int) -> Optional[ScheduledCall]:
    """Get a scheduled call by ID"""
    result = await db.execute(
        select(ScheduledCall).where(ScheduledCall.id == schedule_id)
    )
    return result.scalar_one_or_none()


async def get_scheduled_calls(
    db: AsyncSession,
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> List[ScheduledCall]:
    """Get scheduled calls with optional filters"""
    query = select(ScheduledCall).order_by(ScheduledCall.scheduled_time.asc())

    if status:
        query = query.where(ScheduledCall.status == status)
    if from_date:
        query = query.where(ScheduledCall.scheduled_time >= from_date)
    if to_date:
        query = query.where(ScheduledCall.scheduled_time <= to_date)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_due_scheduled_calls(
    db: AsyncSession,
    until: datetime
) -> List[ScheduledCall]:
    """Get scheduled calls that are due to be executed"""
    result = await db.execute(
        select(ScheduledCall)
        .where(
            ScheduledCall.status == "pending",
            ScheduledCall.scheduled_time <= until
        )
        .order_by(ScheduledCall.scheduled_time.asc())
    )
    return list(result.scalars().all())


async def create_scheduled_call(db: AsyncSession, **kwargs) -> ScheduledCall:
    """Create a new scheduled call"""
    scheduled = ScheduledCall(**kwargs)
    db.add(scheduled)
    await db.flush()
    await db.refresh(scheduled)
    return scheduled


async def update_scheduled_call(
    db: AsyncSession,
    schedule_id: int,
    **kwargs
) -> Optional[ScheduledCall]:
    """Update a scheduled call"""
    scheduled = await get_scheduled_call(db, schedule_id)
    if not scheduled:
        return None

    for key, value in kwargs.items():
        if hasattr(scheduled, key) and value is not None:
            setattr(scheduled, key, value)

    scheduled.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(scheduled)
    return scheduled


async def delete_scheduled_call(db: AsyncSession, schedule_id: int) -> bool:
    """Delete a scheduled call"""
    result = await db.execute(
        delete(ScheduledCall).where(ScheduledCall.id == schedule_id)
    )
    return result.rowcount > 0


# === Campaign CRUD ===

async def get_campaign(db: AsyncSession, campaign_id: int) -> Optional[Campaign]:
    """Get a campaign by ID"""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    return result.scalar_one_or_none()


async def get_campaigns(
    db: AsyncSession,
    status: Optional[str] = None
) -> List[Campaign]:
    """Get all campaigns with optional status filter"""
    query = select(Campaign).order_by(Campaign.created_at.desc())

    if status:
        query = query.where(Campaign.status == status)

    result = await db.execute(query)
    return list(result.scalars().all())


async def create_campaign(db: AsyncSession, **kwargs) -> Campaign:
    """Create a new campaign"""
    campaign = Campaign(**kwargs)
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign


async def update_campaign(
    db: AsyncSession,
    campaign_id: int,
    **kwargs
) -> Optional[Campaign]:
    """Update a campaign"""
    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        return None

    for key, value in kwargs.items():
        if hasattr(campaign, key) and value is not None:
            setattr(campaign, key, value)

    campaign.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(campaign)
    return campaign


async def delete_campaign(db: AsyncSession, campaign_id: int) -> bool:
    """Delete a campaign and all its contacts"""
    result = await db.execute(
        delete(Campaign).where(Campaign.id == campaign_id)
    )
    return result.rowcount > 0


# === CampaignContact CRUD ===

async def get_campaign_contact(
    db: AsyncSession,
    contact_id: int
) -> Optional[CampaignContact]:
    """Get a campaign contact by ID"""
    result = await db.execute(
        select(CampaignContact).where(CampaignContact.id == contact_id)
    )
    return result.scalar_one_or_none()


async def get_campaign_contacts(
    db: AsyncSession,
    campaign_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> List[CampaignContact]:
    """Get contacts for a campaign"""
    query = select(CampaignContact).where(
        CampaignContact.campaign_id == campaign_id
    ).order_by(CampaignContact.id.asc())

    if status:
        query = query.where(CampaignContact.status == status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_campaign_contacts(
    db: AsyncSession,
    campaign_id: int,
    status: Optional[str] = None
) -> int:
    """Count contacts in a campaign"""
    query = select(func.count(CampaignContact.id)).where(
        CampaignContact.campaign_id == campaign_id
    )

    if status:
        query = query.where(CampaignContact.status == status)

    result = await db.execute(query)
    return result.scalar() or 0


async def get_next_pending_contact(
    db: AsyncSession,
    campaign_id: int
) -> Optional[CampaignContact]:
    """Get next pending contact to call"""
    result = await db.execute(
        select(CampaignContact)
        .where(
            CampaignContact.campaign_id == campaign_id,
            CampaignContact.status == "pending"
        )
        .order_by(CampaignContact.id.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_campaign_contact(db: AsyncSession, **kwargs) -> CampaignContact:
    """Create a campaign contact"""
    contact = CampaignContact(**kwargs)
    db.add(contact)
    await db.flush()
    await db.refresh(contact)
    return contact


async def create_campaign_contacts_bulk(
    db: AsyncSession,
    campaign_id: int,
    contacts: List[dict]
) -> int:
    """Create multiple campaign contacts"""
    count = 0
    for contact_data in contacts:
        contact = CampaignContact(
            campaign_id=campaign_id,
            phone_number=contact_data["phone_number"],
            name=contact_data.get("name"),
            extra_data=contact_data.get("extra_data"),
        )
        db.add(contact)
        count += 1

    await db.flush()
    return count


async def update_campaign_contact(
    db: AsyncSession,
    contact_id: int,
    **kwargs
) -> Optional[CampaignContact]:
    """Update a campaign contact"""
    contact = await get_campaign_contact(db, contact_id)
    if not contact:
        return None

    for key, value in kwargs.items():
        if hasattr(contact, key) and value is not None:
            setattr(contact, key, value)

    await db.flush()
    await db.refresh(contact)
    return contact


async def get_campaign_contact_stats(
    db: AsyncSession,
    campaign_id: int
) -> dict:
    """Get contact statistics for a campaign"""
    total = await count_campaign_contacts(db, campaign_id)
    pending = await count_campaign_contacts(db, campaign_id, "pending")
    calling = await count_campaign_contacts(db, campaign_id, "calling")
    completed = await count_campaign_contacts(db, campaign_id, "completed")
    failed = await count_campaign_contacts(db, campaign_id, "failed")

    success_rate = (completed / total * 100) if total > 0 else 0

    return {
        "total": total,
        "pending": pending,
        "calling": calling,
        "completed": completed,
        "failed": failed,
        "success_rate": round(success_rate, 1),
    }


async def count_campaign_active_calls(
    db: AsyncSession,
    campaign_id: int
) -> int:
    """Count active calls (status=calling) for a campaign"""
    return await count_campaign_contacts(db, campaign_id, "calling")
