"""
Translation model - i18n support
"""
from sqlalchemy import Column, String, Text, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Translation(Base):
    """Translation model for multi-language support"""
    
    __tablename__ = "translations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(200), nullable=False)  # message.welcome, button.start, etc.
    lang = Column(String(10), nullable=False)  # uk, en, ru, pl, de
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Unique constraint: one translation per key per language
    __table_args__ = (
        UniqueConstraint("key", "lang", name="uq_translation_key_lang"),
    )
    
    def __repr__(self):
        return f"<Translation(key={self.key}, lang={self.lang})>"

