"""
SEO Endpoints - Multi-tenant
Handles SEO-optimized pages for bots (for web presence)
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.models.bot import Bot

router = APIRouter()


@router.get("/bot/{bot_id}", response_class=HTMLResponse)
async def bot_seo_page(
    bot_id: UUID,
    db: Session = Depends(get_db)
):
    """
    SEO-optimized page for bot.
    Multi-tenant: each bot gets its own SEO page.
    
    Args:
        bot_id: Bot UUID
        db: Database session
    
    Returns:
        HTML page with bot info
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # TODO: Generate SEO-optimized HTML
    # This will include bot name, description, meta tags, etc.
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{bot.name} - Universal Bot OS</title>
        <meta name="description" content="Telegram bot: {bot.name}">
    </head>
    <body>
        <h1>{bot.name}</h1>
        <p>Platform: {bot.platform_type}</p>
        <p>Status: {'Active' if bot.is_active else 'Inactive'}</p>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)

