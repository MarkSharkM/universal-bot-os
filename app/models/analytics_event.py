"""
Analytics Event model - stores Mini App analytics events
"""
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AnalyticsEvent(Base):
    """Analytics Event model - stores Mini App events for metrics"""
    
    __tablename__ = "analytics_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user_external_id = Column(String(200), nullable=True, index=True)  # For events before user creation
    event_name = Column(String(100), nullable=False, index=True)  # e.g., "partner_click", "wallet_connected"
    event_data = Column(JSON, nullable=False, default=dict)  # Additional event data
    platform = Column(String(50), default="telegram", nullable=False)  # telegram, web, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    bot = relationship("Bot", backref="analytics_events")
    user = relationship("User", backref="analytics_events")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_analytics_bot_event", "bot_id", "event_name"),
        Index("idx_analytics_bot_date", "bot_id", "created_at"),
        Index("idx_analytics_user_event", "user_id", "event_name"),
    )
    
    def __repr__(self):
        return f"<AnalyticsEvent(id={self.id}, bot_id={self.bot_id}, event={self.event_name}, created_at={self.created_at})>"
