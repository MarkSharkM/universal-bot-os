"""
Business data model - flexible storage for bot-specific data
(Replaces Google Sheets)
"""
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class BusinessData(Base):
    """Business data model - flexible JSONB storage for bot-specific data"""
    
    __tablename__ = "business_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id"), nullable=False)
    data_type = Column(String(100), nullable=False)  # wallet, partner, log, etc.
    data = Column(JSON, nullable=False)  # Flexible structure
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bot = relationship("Bot", backref="business_data")
    
    # Index for efficient queries
    __table_args__ = (
        Index("idx_business_data_bot_type", "bot_id", "data_type"),
    )
    
    def __repr__(self):
        return f"<BusinessData(id={self.id}, bot_id={self.bot_id}, type={self.data_type})>"

