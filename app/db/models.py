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
