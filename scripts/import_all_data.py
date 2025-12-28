"""
Comprehensive import script for all data from old production bot
Imports: translations, users, partners, logs
"""
import sys
import argparse
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.bot import Bot

# Import migration functions
from scripts.import_translations import import_translations
from scripts.migrate_from_sheets import (
    migrate_user_wallets,
    migrate_bot_log,
    migrate_partners_settings
)


def get_bot_by_name(db: Session, bot_name: str) -> Bot:
    """Get bot by name"""
    bot = db.query(Bot).filter(Bot.name == bot_name).first()
    if not bot:
        raise ValueError(f"Bot '{bot_name}' not found. Please create bot first via Admin UI.")
    return bot


def main():
    """Main import function"""
    parser = argparse.ArgumentParser(
        description='Import all data from old production bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all data for EarnHubAggregatorBot
  python scripts/import_all_data.py --bot-name EarnHubAggregatorBot
  
  # Import with custom paths
  python scripts/import_all_data.py --bot-name EarnHubAggregatorBot \\
    --translations old-prod-hub-bot/translations_for prod tg.csv \\
    --users old-prod-hub-bot/Earnbot_Referrals - user_wallets.csv \\
    --partners old-prod-hub-bot/Earnbot_Referrals - Partners_Settings.csv \\
    --logs old-prod-hub-bot/Earnbot_Referrals - bot_log.csv
        """
    )
    
    parser.add_argument('--bot-name', required=True, help='Bot name (e.g., EarnHubAggregatorBot)')
    parser.add_argument('--bot-id', help='Bot UUID (alternative to --bot-name)')
    
    # File paths with defaults
    base_path = Path(__file__).parent.parent / "old-prod-hub-bot"
    parser.add_argument('--translations', 
                       default=str(base_path / "translations_for prod tg.csv"),
                       help='Path to translations CSV')
    parser.add_argument('--users',
                       default=str(base_path / "Earnbot_Referrals - user_wallets.csv"),
                       help='Path to user_wallets CSV')
    parser.add_argument('--partners',
                       default=str(base_path / "Earnbot_Referrals - Partners_Settings.csv"),
                       help='Path to Partners_Settings CSV')
    parser.add_argument('--logs',
                       default=str(base_path / "Earnbot_Referrals - bot_log.csv"),
                       help='Path to bot_log CSV')
    
    # Options
    parser.add_argument('--skip-translations', action='store_true', help='Skip translations import')
    parser.add_argument('--skip-users', action='store_true', help='Skip users import')
    parser.add_argument('--skip-partners', action='store_true', help='Skip partners import')
    parser.add_argument('--skip-logs', action='store_true', help='Skip logs import')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        # Get bot
        if args.bot_id:
            bot = db.query(Bot).filter(Bot.id == UUID(args.bot_id)).first()
            if not bot:
                print(f"❌ Bot with ID {args.bot_id} not found")
                return
        else:
            bot = get_bot_by_name(db, args.bot_name)
        
        print(f"\n🤖 Importing data for bot: {bot.name} ({bot.id})")
        print("=" * 60)
        
        bot_id_str = str(bot.id)
        total_imported = 0
        
        # 1. Import translations
        if not args.skip_translations:
            translations_path = Path(args.translations)
            if translations_path.exists():
                print(f"\n📥 [1/4] Importing translations from {translations_path.name}...")
                try:
                    import_translations(str(translations_path))
                    print("✅ Translations imported successfully")
                    total_imported += 1
                except Exception as e:
                    print(f"❌ Error importing translations: {e}")
            else:
                print(f"⚠️  Translations file not found: {translations_path}")
        else:
            print("\n⏭️  [1/4] Skipping translations (--skip-translations)")
        
        # 2. Import users
        if not args.skip_users:
            users_path = Path(args.users)
            if users_path.exists():
                print(f"\n📥 [2/4] Importing users from {users_path.name}...")
                try:
                    count = migrate_user_wallets(db, bot_id_str, str(users_path))
                    print(f"✅ Imported {count} users")
                    total_imported += count
                except Exception as e:
                    print(f"❌ Error importing users: {e}")
            else:
                print(f"⚠️  Users file not found: {users_path}")
        else:
            print("\n⏭️  [2/4] Skipping users (--skip-users)")
        
        # 3. Import partners
        if not args.skip_partners:
            partners_path = Path(args.partners)
            if partners_path.exists():
                print(f"\n📥 [3/4] Importing partners from {partners_path.name}...")
                try:
                    count = migrate_partners_settings(db, bot_id_str, str(partners_path))
                    print(f"✅ Imported {count} partners")
                    total_imported += count
                except Exception as e:
                    print(f"❌ Error importing partners: {e}")
            else:
                print(f"⚠️  Partners file not found: {partners_path}")
        else:
            print("\n⏭️  [3/4] Skipping partners (--skip-partners)")
        
        # 4. Import logs
        if not args.skip_logs:
            logs_path = Path(args.logs)
            if logs_path.exists():
                print(f"\n📥 [4/4] Importing logs from {logs_path.name}...")
                try:
                    count = migrate_bot_log(db, bot_id_str, str(logs_path))
                    print(f"✅ Imported {count} log entries")
                    total_imported += count
                except Exception as e:
                    print(f"❌ Error importing logs: {e}")
            else:
                print(f"⚠️  Logs file not found: {logs_path}")
        else:
            print("\n⏭️  [4/4] Skipping logs (--skip-logs)")
        
        print("\n" + "=" * 60)
        print(f"🎉 Import completed! Total records: {total_imported}")
        print(f"\n💡 Next steps:")
        print(f"   1. Check Admin UI: /admin → Stats")
        print(f"   2. Test bot in Telegram")
        print(f"   3. Verify partners are visible")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

