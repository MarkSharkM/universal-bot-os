"""
Authentication endpoints for Admin API.
Login and token verification.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.core.security import (
    create_access_token,
    verify_admin_credentials,
    get_current_admin
)
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class VerifyResponse(BaseModel):
    valid: bool
    user: Optional[str] = None


# ==================== AUTHENTICATION ENDPOINTS ====================

@router.post("/auth/login", response_model=LoginResponse)
@limiter.limit("5/minute")  # Prevent brute force attacks
async def admin_login(request: Request, credentials: LoginRequest):
    """
    Admin login endpoint.
    Returns JWT token for authentication.
    
    Args:
        credentials: Username and password
    
    Returns:
        JWT access token
    
    Raises:
        HTTPException: If credentials are invalid
    """
    if not verify_admin_credentials(credentials.username, credentials.password):
        logger.warning(f"Failed login attempt for username: {credentials.username}")
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": "admin"})
    
    logger.info(f"Admin user '{credentials.username}' logged in successfully")
    
    from app.core.config import settings
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )


@router.get("/auth/verify", response_model=VerifyResponse)
async def verify_token(admin: dict = Depends(get_current_admin)):
    """
    Verify JWT token.
    Protected endpoint that requires valid admin token.
    
    Args:
        admin: Admin info from token (injected by dependency)
    
    Returns:
        Verification status
    """
    return VerifyResponse(
        valid=True,
        user=admin.get("sub")
    )
