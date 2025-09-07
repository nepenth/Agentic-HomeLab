from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Text
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime
from typing import Optional


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Email mailbox settings
    email_server = Column(String(255), nullable=True)
    email_port = Column(Integer, nullable=True)
    email_username = Column(String(255), nullable=True)
    email_password_encrypted = Column(Text, nullable=True)  # Encrypted password
    email_use_ssl = Column(Boolean, default=True, nullable=True)
    email_mailbox = Column(String(50), default="INBOX", nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"