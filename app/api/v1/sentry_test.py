"""
Sentry test endpoint for Universal Bot OS
Trigger a test error to verify Sentry error tracking
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/sentry-debug")
async def trigger_error():
    """
    Test endpoint to trigger a Sentry error.
    This will create a division by zero error that Sentry should catch.
    
    Usage: GET /sentry-debug
    """
    division_by_zero = 1 / 0
    return {"status": "This should never return"}
