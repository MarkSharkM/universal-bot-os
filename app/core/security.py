"""
Security utilities: JWT, password hashing, admin authentication
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_admin_credentials(username: str, password: str) -> bool:
    """
    Verify admin username and password against settings.
    
    Args:
        username: Admin username
        password: Admin password (plain text)
    
    Returns:
        True if credentials match, False otherwise
    """
    return username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme)
) -> Dict[str, Any]:
    """
    FastAPI dependency to verify admin JWT token.
    Use as dependency in protected admin routes.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or user is not admin
    
    Example:
        @router.get("/admin/protected")
        async def protected_route(admin: dict = Depends(get_current_admin)):
            return {"message": "Access granted"}
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify this is an admin token
    if payload.get("sub") != "admin":
        logger.warning(f"Non-admin token attempt: {payload.get('sub')}")
        raise HTTPException(
            status_code=403,
            detail="Not authorized - admin access required",
        )
    
    return payload

