"""
Pydantic schemas for User API
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    external_id: str
    platform: str
    language_code: str
    balance: Decimal
    metadata: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

