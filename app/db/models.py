"""
SQLAlchemy models for LigAI
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Prompt(Base):
    """AI prompt configuration"""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    voice_id: Mapped[str] = mapped_column(String(50), default="pt-BR-isadora")
    llm_model: Mapped[str] = mapped_column(String(50), default="gpt-4.1-nano")
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    greeting_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    greeting_duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    calls: Mapped[List["Call"]] = relationship(back_populates="prompt")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "voice_id": self.voice_id,
            "llm_model": self.llm_model,
            "temperature": self.temperature,
            "greeting_text": self.greeting_text,
            "greeting_duration_ms": self.greeting_duration_ms,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Call(Base):
    """Call record"""

    __tablename__ = "calls"
    __table_args__ = (
        Index("idx_calls_status", "status"),
        Index("idx_calls_start_time", "start_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    freeswitch_uuid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    caller_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    called_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    prompt_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("prompts.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    direction: Mapped[str] = mapped_column(String(10), default="outbound")
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    prompt: Mapped[Optional["Prompt"]] = relationship(back_populates="calls")
    messages: Mapped[List["CallMessage"]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )

    def to_dict(self, include_messages: bool = False) -> dict:
        data = {
            "id": self.id,
            "call_id": self.call_id,
            "freeswitch_uuid": self.freeswitch_uuid,
            "caller_number": self.caller_number,
            "called_number": self.called_number,
            "prompt_id": self.prompt_id,
            "status": self.status,
            "direction": self.direction,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data


class Setting(Base):
    """System settings (API keys, configurations)"""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self, hide_secrets: bool = True) -> dict:
        value = self.value
        if hide_secrets and self.is_secret and value:
            # Show only last 4 characters for secrets
            value = "*" * 16 + value[-4:] if len(value) > 4 else "****"
        return {
            "id": self.id,
            "key": self.key,
            "value": value,
            "description": self.description,
            "is_secret": self.is_secret,
            "is_configured": bool(self.value),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CallMessage(Base):
    """Call conversation message"""

    __tablename__ = "call_messages"
    __table_args__ = (Index("idx_messages_call", "call_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[int] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    call: Mapped["Call"] = relationship(back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "call_id": self.call_id,
            "role": self.role,
            "content": self.content,
            "audio_duration_ms": self.audio_duration_ms,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# === WEBHOOKS ===

class WebhookConfig(Base):
    """Webhook configuration"""

    __tablename__ = "webhook_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    events: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    secret: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    logs: Mapped[List["WebhookLog"]] = relationship(
        back_populates="config", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "url": self.url,
            "events": json.loads(self.events) if self.events else [],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WebhookLog(Base):
    """Webhook delivery log"""

    __tablename__ = "webhook_logs"
    __table_args__ = (
        Index("idx_webhook_logs_config", "config_id"),
        Index("idx_webhook_logs_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    config_id: Mapped[int] = mapped_column(
        ForeignKey("webhook_configs.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    config: Mapped["WebhookConfig"] = relationship(back_populates="logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "config_id": self.config_id,
            "event_type": self.event_type,
            "status_code": self.status_code,
            "success": self.success,
            "attempt": self.attempt,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# === SCHEDULED CALLS ===

class ScheduledCall(Base):
    """Scheduled call"""

    __tablename__ = "scheduled_calls"
    __table_args__ = (
        Index("idx_scheduled_calls_time", "scheduled_time"),
        Index("idx_scheduled_calls_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("prompts.id"), nullable=True
    )
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    call_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    prompt: Mapped[Optional["Prompt"]] = relationship()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "phone_number": self.phone_number,
            "prompt_id": self.prompt_id,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "status": self.status,
            "call_id": self.call_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# === CAMPAIGNS ===

class Campaign(Base):
    """Campaign for batch dialing"""

    __tablename__ = "campaigns"
    __table_args__ = (Index("idx_campaigns_status", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("prompts.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    max_concurrent: Mapped[int] = mapped_column(Integer, default=5)
    total_contacts: Mapped[int] = mapped_column(Integer, default=0)
    completed_contacts: Mapped[int] = mapped_column(Integer, default=0)
    failed_contacts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    prompt: Mapped[Optional["Prompt"]] = relationship()
    contacts: Mapped[List["CampaignContact"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prompt_id": self.prompt_id,
            "status": self.status,
            "max_concurrent": self.max_concurrent,
            "total_contacts": self.total_contacts,
            "completed_contacts": self.completed_contacts,
            "failed_contacts": self.failed_contacts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class CampaignContact(Base):
    """Contact in a campaign"""

    __tablename__ = "campaign_contacts"
    __table_args__ = (
        Index("idx_campaign_contacts_campaign", "campaign_id"),
        Index("idx_campaign_contacts_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    call_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship(back_populates="contacts")

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "phone_number": self.phone_number,
            "name": self.name,
            "extra_data": json.loads(self.extra_data) if self.extra_data else None,
            "status": self.status,
            "call_id": self.call_id,
            "attempts": self.attempts,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }
