"""
Message model - stores conversation history for AI context
"""
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Message(Base):
    """Message model - conversation history for AI context"""
    
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=False, default=dict)  # message_id, reply_to, etc.
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="messages")
    bot = relationship("Bot", backref="messages")
    
    # Index for efficient AI context retrieval
    __table_args__ = (
        Index("idx_messages_user_timestamp", "user_id", "timestamp"),
        Index("idx_messages_bot_timestamp", "bot_id", "timestamp"),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, user_id={self.user_id})>"

