"""
Product Monitoring API endpoints.
Separate module to avoid bloating admin.py.
Only reads existing data from DB - no changes to bot/mini-app logic.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.message import Message
from app.models.business_data import BusinessData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Product Monitoring"])


@router.get("/product/{bot_id}")
async def get_product_monitoring(
    bot_id: str,
    days: int = 30,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Product monitoring dashboard data.
    Split by Telegram Bot vs Mini App.
    """
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            # Recalculate days for daily comparison loop
            days = (end_dt - start_dt).days
        except ValueError:
            start_dt = datetime.utcnow() - timedelta(days=days)
            end_dt = datetime.utcnow() + timedelta(days=1)
    else:
        start_dt = datetime.utcnow() - timedelta(days=days)
        end_dt = datetime.utcnow() + timedelta(days=1)
    
    try:
        # ============================================
        # TELEGRAM BOT METRICS
        # ============================================
        
        # Total unique users (by external_id)
        bot_total_users = db.query(func.count(distinct(User.external_id))).filter(
            User.bot_id == bot_id,
            User.external_id.isnot(None)
        ).scalar() or 0
        
        # Bot commands today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        bot_commands_today = db.query(Message).filter(
            Message.bot_id == bot_id,
            Message.role == 'user',
            Message.timestamp >= today_start,
            ~Message.content.ilike('%mini_app%'),
            ~Message.custom_data.op('->>')('source').ilike('%mini_app%')
        ).count()
        
        # Bot DAU (unique users last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        bot_dau = db.query(func.count(distinct(Message.user_id))).filter(
            Message.bot_id == bot_id,
            Message.role == 'user',
            Message.timestamp >= week_ago,
            ~Message.content.ilike('%mini_app%')
        ).scalar() or 0
        
        # Command usage breakdown
        bot_messages = db.query(Message).filter(
            Message.bot_id == bot_id,
            Message.role == 'user',
            Message.timestamp >= start_dt,
            Message.timestamp < end_dt,
            Message.content.ilike('/%')  # Commands start with /
        ).all()
        
        command_counts = {}
        for msg in bot_messages:
            cmd = msg.content.split()[0] if msg.content else '/unknown'
            # Skip mini app events
            if msg.custom_data and msg.custom_data.get('source', '').startswith('mini_app'):
                continue
            command_counts[cmd] = command_counts.get(cmd, 0) + 1
        
        # Response time - we don't track this in Message model currently
        # (Would need to add column or calculate from custom_data)
        response_times = 0
        
        # Language distribution
        lang_dist = db.query(
            User.language_code,
            func.count(User.id)
        ).filter(
            User.bot_id == bot_id,
            User.language_code.isnot(None)
        ).group_by(User.language_code).all()
        language_distribution = {lang or 'unknown': count for lang, count in lang_dist}
        
        # ============================================
        # MINI APP METRICS
        # ============================================
        
        # Mini App sessions (unique users with mini_app events)
        mini_app_sessions = db.query(func.count(distinct(Message.user_id))).filter(
            Message.bot_id == bot_id,
            Message.role == 'user',
            Message.timestamp >= start_dt,
            Message.timestamp < end_dt,
            Message.custom_data.op('->>')('source').ilike('%mini_app%')
        ).scalar() or 0
        
        # Mini App clicks today
        mini_app_clicks_today = db.query(Message).filter(
            Message.bot_id == bot_id,
            Message.role == 'user',
            Message.timestamp >= today_start,
            Message.content.ilike('%partner_click%')
        ).count()
        
        # Mini App DAU (7 days)
        mini_app_dau = db.query(func.count(distinct(Message.user_id))).filter(
            Message.bot_id == bot_id,
            Message.role == 'user',
            Message.timestamp >= week_ago,
            Message.custom_data.op('->>')('source').ilike('%mini_app%')
        ).scalar() or 0
        
        # Platform breakdown (from custom_data.platform)
        mini_app_messages = db.query(Message).filter(
            Message.bot_id == bot_id,
            Message.role == 'user',
            Message.timestamp >= start_dt,
            Message.timestamp < end_dt,
            Message.custom_data.op('->>')('source').ilike('%mini_app%')
        ).all()
        
        platform_counts = {'ios': 0, 'android': 0, 'web': 0, 'desktop': 0, 'other': 0}
        for msg in mini_app_messages:
            cd = msg.custom_data or {}
            platform = (cd.get('platform') or '').lower()
            if platform == 'ios':
                platform_counts['ios'] += 1
            elif platform == 'android':
                platform_counts['android'] += 1
            elif platform in ('web', 'weba', 'webk'):
                platform_counts['web'] += 1
            elif platform in ('tdesktop', 'macos'):
                platform_counts['desktop'] += 1
            elif platform:
                platform_counts['other'] += 1
        
        # ============================================
        # DAILY ACTIVITY COMPARISON (overselected range)
        # ============================================
        daily_data = []
        # Loop from start_dt to end_dt
        current_day = start_dt.date()
        date_range_days = (end_dt.date() - current_day).days
        
        for i in range(date_range_days):
            day = current_day + timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            
            # Bot commands that day
            bot_count = db.query(Message).filter(
                Message.bot_id == bot_id,
                Message.role == 'user',
                Message.timestamp >= day_start,
                Message.timestamp < day_end,
                ~Message.custom_data.op('->>')('source').ilike('%mini_app%')
            ).count()
            
            # Mini App events that day
            mini_count = db.query(Message).filter(
                Message.bot_id == bot_id,
                Message.role == 'user',
                Message.timestamp >= day_start,
                Message.timestamp < day_end,
                Message.custom_data.op('->>')('source').ilike('%mini_app%')
            ).count()
            
            daily_data.append({
                'date': day.isoformat(),
                'bot': bot_count,
                'mini_app': mini_count
            })
        
        return {
            'period_days': days,
            'generated_at': datetime.utcnow().isoformat(),
            
            # Telegram Bot section
            'telegram_bot': {
                'total_users': bot_total_users,
                'commands_today': bot_commands_today,
                'dau_7d': bot_dau,
                'avg_response_time_seconds': round(response_times, 3),
                'command_usage': dict(sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                'language_distribution': language_distribution
            },
            
            # Mini App section
            'mini_app': {
                'sessions': mini_app_sessions,
                'clicks_today': mini_app_clicks_today,
                'dau_7d': mini_app_dau,
                'platform_breakdown': platform_counts
            },
            
            # Comparison
            'daily_comparison': daily_data
        }
        
    except Exception as e:
        logger.error(f"Error in product monitoring: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
