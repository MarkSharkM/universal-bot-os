"""
Health check utilities
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.config import settings
import redis
import logging

logger = logging.getLogger(__name__)


async def check_database() -> Dict[str, Any]:
    """
    Check database connectivity.
    
    Returns:
        Dictionary with status and details
    """
    try:
        db = SessionLocal()
        try:
            # Simple query to check connection
            db.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "message": "Database connection successful"
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }


async def check_redis() -> Dict[str, Any]:
    """
    Check Redis connectivity.
    
    Returns:
        Dictionary with status and details
    """
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        return {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }


async def get_health_status() -> Dict[str, Any]:
    """
    Get overall health status.
    
    Returns:
        Dictionary with health status of all components
    """
    db_status = await check_database()
    redis_status = await check_redis()
    
    overall_status = "healthy"
    if db_status["status"] != "healthy":
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "components": {
            "database": db_status,
            "redis": redis_status,
        }
    }

