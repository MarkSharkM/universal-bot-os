"""
Admin API module - Multi-tenant bot management.

Modular structure:
- auth.py: Authentication endpoints (login, verify)
- bots.py: Bot CRUD operations
- users.py: User management
- messages.py: Message history & testing
- translations.py: Translation management
- partners.py: Partner bot management

All endpoints require admin authentication except /auth/login.
"""
from fastapi import APIRouter

from .auth import router as auth_router
from .bots import router as bots_router
from .users import router as users_router
from .messages import router as messages_router
from .translations import router as translations_router
from .partners import router as partners_router

# Main admin router
router = APIRouter()

# Include all sub-routers
router.include_router(auth_router, tags=["auth"])
router.include_router(bots_router, tags=["bots"])
router.include_router(users_router, tags=["users"])
router.include_router(messages_router, tags=["messages"])
router.include_router(translations_router, tags=["translations"])
router.include_router(partners_router, tags=["partners"])

__all__ = ["router"]
