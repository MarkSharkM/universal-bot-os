"""
Bot model - represents a bot instance
"""
from sqlalchemy import Column, String, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Bot(Base):
    """Bot model for multi-tenant architecture"""
    
    __tablename__ = "bots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform_type = Column(String(50), nullable=False)  # telegram, web, whatsapp
    token = Column(String(500), nullable=False)  # Encrypted bot token
    name = Column(String(200), nullable=False)
    config = Column(JSON, nullable=False, default=dict)  # AI prompts, colors, keys, settings
    default_lang = Column(String(10), nullable=False, default="uk")  # uk, en, ru, pl, de
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Bot(id={self.id}, name={self.name}, platform={self.platform_type})>"

