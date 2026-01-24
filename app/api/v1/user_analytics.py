"""
User Analytics API - Multi-tenant
Separated from admin.py to reduce file complexity.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, String, Integer
from datetime import datetime, timedelta
from uuid import UUID
import logging

from app.core.database import get_db
from app.models.user import User
from app.models.business_data import BusinessData

logger = logging.getLogger(__name__)

router = APIRouter(tags=["User Analytics"])


@router.get("/bots/{bot_id}/users/analytics")
async def get_users_analytics(
    bot_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated Users and Revenue analytics.
    
    Returns:
        - daily_new_users: Chart data
        - daily_revenue: Chart data (from Payment logs)
        - revenue_stats: Total earnings, total buyers
    """
    try:
        # 1. Calculate time range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 2. Daily New Users (Chart)
        # Query Users created_at
        daily_users = db.query(
            func.date_trunc('day', User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.bot_id == bot_id,
            User.created_at >= start_date
        ).group_by(func.date_trunc('day', User.created_at)).order_by('date').all()
        
        daily_new_users_map = {row.date.strftime('%Y-%m-%d'): row.count for row in daily_users if row.date}
        
        # 3. Daily Revenue (Chart)
        # Query BusinessData type='payment'
        # Note: Only captures data since logging was implemented
        daily_payments = db.query(
            func.date_trunc('day', BusinessData.created_at).label('date'),
            func.count(BusinessData.id).label('count'),
            func.sum(cast(BusinessData.data.op('->>')('amount'), Integer)).label('amount') 
        ).filter(
            BusinessData.bot_id == bot_id,
            BusinessData.data_type == 'payment',
            BusinessData.created_at >= start_date
        ).group_by(func.date_trunc('day', BusinessData.created_at)).order_by('date').all()
        
        daily_revenue_map = {row.date.strftime('%Y-%m-%d'): float(row.amount or 0) for row in daily_payments if row.date}
        
        # Fill missing dates
        chart_days = []
        current = start_date
        while current <= end_date:
            day_str = current.strftime('%Y-%m-%d')
            chart_days.append({
                "date": day_str,
                "new_users": daily_new_users_map.get(day_str, 0),
                "revenue": daily_revenue_map.get(day_str, 0)
            })
            current += timedelta(days=1)
            
        # 4. Total Stats (All time)
        # Total Users
        total_users_count = db.query(func.count(User.id)).filter(User.bot_id == bot_id).scalar()
        
        # Total Payers (Unique users who have payment method)
        # Logic: users with top_unlock_method='payment'
        total_buyers_count = db.query(func.count(User.id)).filter(
            User.bot_id == bot_id,
            User.custom_data.op('->>')('top_unlock_method') == 'payment'
        ).scalar() or 0
        
        # Total Revenue (Estimate based on buyers * price, plus logged payments)
        # Since logs are new, we calculate: (All Buyers) * 1 Star
        estimated_revenue = total_buyers_count * 1 # Assuming price is 1 star
        
        return {
            "period_days": days,
            "chart_data": chart_days,
            "stats": {
                "total_users": total_users_count,
                "total_buyers": total_buyers_count,
                "total_revenue": estimated_revenue,
                "currency": "XTR"
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching user analytics: {e}", exc_info=True)
        # Return empty structure on error to prevent frontend crash
        return {
            "error": str(e),
            "chart_data": [],
            "stats": {
                "total_users": 0,
                "total_buyers": 0,
                "total_revenue": 0
            }
        }
