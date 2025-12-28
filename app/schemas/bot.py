"""
Pydantic schemas for Bot API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class BotCreate(BaseModel):
    """Schema for creating a bot"""
    name: str
    platform_type: str = "telegram"
    token: str
    default_lang: str = "uk"
    config: Dict[str, Any] = Field(default_factory=dict)


class BotUpdate(BaseModel):
    """Schema for updating a bot"""
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    default_lang: Optional[str] = None
    is_active: Optional[bool] = None


class BotResponse(BaseModel):
    """Schema for bot response"""
    id: UUID
    name: str
    platform_type: str
    default_lang: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

