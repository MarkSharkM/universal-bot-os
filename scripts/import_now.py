#!/usr/bin/env python3
"""
Quick import script - runs locally but connects to Railway database
Requires DATABASE_URL from Railway
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.bot import Bot

# Import functions
from scripts.import_translations import import_translations
from scripts.migrate_from_sheets import (
    migrate_user_wallets,
    migrate_bot_log,
    migrate_partners_settings
)

BOT_NAME = "EarnHubAggregatorBot"
BASE_PATH = Path(__file__).parent.parent / "old-prod-hub-bot"


def main():
    """Run import"""
    print("=" * 60)
    print("📥 Importing data for EarnHubAggregatorBot")
    print("=" * 60)
    print()
    
    # Check DATABASE_URL
    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL not found!")
        print("💡 Get it from Railway: Service → Variables → DATABASE_URL")
        print("   Or set in .env file")
        return
    
    db = SessionLocal()
    
    try:
        # Get bot
        bot = db.query(Bot).filter(Bot.name == BOT_NAME, Bot.is_active == True).first()
        if not bot:
            print(f"❌ Active bot '{BOT_NAME}' not found")
            print("💡 Create bot first via Admin UI")
            return
        
        print(f"✅ Found bot: {bot.name} ({bot.id})")
        print()
        
        bot_id_str = str(bot.id)
        total = 0
        
        # 1. Translations
        translations_path = BASE_PATH / "translations_for prod tg.csv"
        if translations_path.exists():
            print(f"📥 [1/4] Importing translations...")
            try:
                import_translations(str(translations_path))
                print("✅ Translations imported")
                total += 1
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print(f"⚠️  Translations file not found: {translations_path}")
        
        # 2. Users
        users_path = BASE_PATH / "Earnbot_Referrals - user_wallets.csv"
        if users_path.exists():
            print(f"\n📥 [2/4] Importing users...")
            try:
                count = migrate_user_wallets(db, bot_id_str, str(users_path))
                print(f"✅ Imported {count} users")
                total += count
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print(f"⚠️  Users file not found: {users_path}")
        
        # 3. Partners
        partners_path = BASE_PATH / "Earnbot_Referrals - Partners_Settings.csv"
        if partners_path.exists():
            print(f"\n📥 [3/4] Importing partners...")
            try:
                count = migrate_partners_settings(db, bot_id_str, str(partners_path))
                print(f"✅ Imported {count} partners")
                total += count
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print(f"⚠️  Partners file not found: {partners_path}")
        
        # 4. Logs
        logs_path = BASE_PATH / "Earnbot_Referrals - bot_log.csv"
        if logs_path.exists():
            print(f"\n📥 [4/4] Importing logs...")
            try:
                count = migrate_bot_log(db, bot_id_str, str(logs_path))
                print(f"✅ Imported {count} log entries")
                total += count
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print(f"⚠️  Logs file not found: {logs_path}")
        
        print("\n" + "=" * 60)
        print(f"🎉 Import completed! Total: {total} records")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()

