from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


class Conversation(db.Model):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120), default="Untitled Conversation")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __init__(self, title: str = "Untitled Conversation") -> None:
        self.title = title

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
        }


class Participant(db.Model):
    __tablename__ = "conversation_participants"

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    username: Mapped[str] = mapped_column(String(80), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    conversation: Mapped["Conversation"] = relationship(back_populates="participants")

    def __init__(self, conversation_id: int, username: str) -> None:
        self.conversation_id = conversation_id
        self.username = username

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "joined_at": self.joined_at.isoformat(),
        }


class Message(db.Model):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __init__(self, conversation_id: int, sender: str, content: str) -> None:
        self.conversation_id = conversation_id
        self.sender = sender
        self.content = content

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender": self.sender,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }
