"""
User model - represents a user across platforms
"""
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class User(Base):
    """User model - multi-tenant with bot_id isolation"""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(200), nullable=False)  # telegram_id, web_user_id, etc.
    platform = Column(String(50), nullable=False)  # telegram, web, whatsapp
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id"), nullable=False)
    language_code = Column(String(10), nullable=False, default="uk")  # uk, en, ru, pl, de
    balance = Column(Numeric(10, 2), default=0.0, nullable=False)
    custom_data = Column(JSON, nullable=False, default=dict)  # Custom fields per bot
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bot = relationship("Bot", backref="users")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    
    # Unique constraint: one user per bot per platform
    __table_args__ = (
        UniqueConstraint("bot_id", "external_id", "platform", name="uq_user_bot_platform"),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, external_id={self.external_id}, bot_id={self.bot_id})>"

