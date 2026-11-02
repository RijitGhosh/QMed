"""Database schema: users, sessions, transfers, bb84_sessions, activity_logs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(80))
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    password_salt: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16))
    department: Mapped[Optional[str]] = mapped_column(String(80))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    public_key: Mapped[str] = mapped_column(String(64))            # X25519 public key (hex)
    encrypted_private_key: Mapped[str] = mapped_column(Text)       # password-protected blob (JSON)


class AuthSession(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped[User] = relationship()


class Transfer(Base):
    __tablename__ = "transfers"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[Optional[str]] = mapped_column(String(24), unique=True, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[Optional[str]] = mapped_column(String(64))   # random id, never user input
    file_size: Mapped[int] = mapped_column(Integer)
    encryption_algorithm: Mapped[Optional[str]] = mapped_column(String(32))
    nonce: Mapped[Optional[str]] = mapped_column(String(32))
    key_id: Mapped[Optional[str]] = mapped_column(String(32))
    key_envelope: Mapped[Optional[str]] = mapped_column(Text)            # wrapped key (JSON)
    original_sha256: Mapped[Optional[str]] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    integrity_status: Mapped[str] = mapped_column(String(16), default="UNVERIFIED")
    qber: Mapped[Optional[float]] = mapped_column(Float)
    qber_threshold: Mapped[Optional[float]] = mapped_column(Float)
    eve_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    bb84_status: Mapped[str] = mapped_column(String(48))
    message: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    sender: Mapped[User] = relationship(foreign_keys=[sender_id])
    recipient: Mapped[User] = relationship(foreign_keys=[recipient_id])


class BB84Session(Base):
    __tablename__ = "bb84_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("transfers.id"), index=True)
    initiator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    receiver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    bit_count: Mapped[int] = mapped_column(Integer)
    sifted_key_length: Mapped[int] = mapped_column(Integer)
    test_sample_size: Mapped[int] = mapped_column(Integer)
    mismatches: Mapped[int] = mapped_column(Integer)
    qber: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    eve_enabled: Mapped[bool] = mapped_column(Boolean)
    decision: Mapped[str] = mapped_column(String(32))
    key_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(48), index=True)
    status: Mapped[str] = mapped_column(String(16))
    transfer_id: Mapped[Optional[str]] = mapped_column(String(24))
    description: Mapped[Optional[str]] = mapped_column(String(300))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    source_ip: Mapped[Optional[str]] = mapped_column(String(45))
    user: Mapped[Optional[User]] = relationship()


Index("ix_transfers_status_recipient", Transfer.recipient_id, Transfer.status)
