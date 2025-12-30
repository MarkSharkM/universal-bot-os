#!/usr/bin/env python3
"""
Check bots and their partners to find duplicates and mismatches.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.bot import Bot
from app.models.business_data import BusinessData
from sqlalchemy import func

def check_bots_and_partners():
    db = SessionLocal()
    try:
        # Get all bots
        bots = db.query(Bot).all()
        print(f"🔍 Знайдено ботів: {len(bots)}\n")
        
        for bot in bots:
            print(f"Bot ID: {bot.id}")
            print(f"  Name: {bot.name}")
            print(f"  Platform: {bot.platform_type}")
            print(f"  Active: {bot.is_active}")
            print(f"  Token (first 20): {bot.token[:20] if bot.token else 'None'}...")
            
            # Count partners for this bot
            partners_count = db.query(BusinessData).filter(
                BusinessData.bot_id == bot.id,
                BusinessData.data_type == 'partner',
                BusinessData.deleted_at.is_(None)
            ).count()
            
            # Get active partners
            all_partners = db.query(BusinessData).filter(
                BusinessData.bot_id == bot.id,
                BusinessData.data_type == 'partner',
                BusinessData.deleted_at.is_(None)
            ).all()
            
            active_partners = []
            for p in all_partners:
                data = p.data or {}
                if data.get('active') == 'Yes':
                    active_partners.append(p)
            
            print(f"  Partners (total): {partners_count}")
            print(f"  Partners (active): {len(active_partners)}")
            
            if active_partners:
                print("  Active partners:")
                for p in active_partners:
                    data = p.data or {}
                    print(f"    - {data.get('bot_name', 'Unknown')} ({data.get('category', 'NEW')})")
            
            print()
        
        # Check for duplicate bot names
        print("🔍 Перевірка дублікатів:")
        bot_names = {}
        for bot in bots:
            if bot.name in bot_names:
                bot_names[bot.name].append(bot)
            else:
                bot_names[bot.name] = [bot]
        
        duplicates = {name: bots_list for name, bots_list in bot_names.items() if len(bots_list) > 1}
        if duplicates:
            print("⚠️  Знайдено дублікати ботів:")
            for name, bots_list in duplicates.items():
                print(f"  '{name}': {len(bots_list)} ботів")
                for bot in bots_list:
                    print(f"    - ID: {bot.id}, Active: {bot.is_active}")
        else:
            print("✅ Дублікатів не знайдено")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_bots_and_partners()

