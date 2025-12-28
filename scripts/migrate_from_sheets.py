"""
Migration script from Google Sheets to PostgreSQL
Supports CSV/JSON import for user_wallets, bot_log, Partners_Settings
"""
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.bot import Bot as BotModel
from app.models.user import User as UserModel
from app.models.business_data import BusinessData as BusinessDataModel
from uuid import uuid4

# Create tables
Base.metadata.create_all(bind=engine)


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime"""
    if not date_str or date_str.strip() == '':
        return None
    
    # Try different formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%Y-%m-%d %H.%M',
        '%d.%m.%Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except:
            continue
    
    return None


def parse_decimal(value: Optional[str]) -> Decimal:
    """Parse decimal value"""
    if not value or value.strip() == '':
        return Decimal('0.0')
    
    try:
        # Replace comma with dot
        value = str(value).replace(',', '.')
        return Decimal(value)
    except:
        return Decimal('0.0')


def migrate_user_wallets(
    db: Session,
    bot_id: str,
    csv_path: str
) -> int:
    """
    Migrate user_wallets from CSV to PostgreSQL.
    
    Args:
        db: Database session
        bot_id: Bot UUID (as string)
        csv_path: Path to CSV file
    
    Returns:
        Number of migrated users
    """
    migrated = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                external_id = str(row.get('User Chat ID', '')).strip()
                if not external_id:
                    continue
                
                # Get or create user
                user = db.query(UserModel).filter(
                    UserModel.bot_id == bot_id,
                    UserModel.external_id == external_id,
                    UserModel.platform == 'telegram'
                ).first()
                
                if not user:
                    user = UserModel(
                        id=uuid4(),
                        bot_id=bot_id,
                        external_id=external_id,
                        platform='telegram',
                        language_code=row.get('Language', 'uk') or 'uk',
                        balance=parse_decimal(row.get('Total Earned TON', '0')),
                        metadata={
                            'username': row.get('Username', ''),
                            'wallet_address': row.get('Wallet Address', ''),
                            'total_invited': int(row.get('Total Invited', 0) or 0),
                            'top_status': row.get('TOP Status', 'locked') or 'locked',
                            'referred_by': row.get('Referred By', ''),
                            'first_join_date': row.get('First Join Date', ''),
                            'device': row.get('Device', ''),
                            'geo': row.get('Geo', ''),
                        },
                        is_active=row.get('Status', 'active') != 'ban'
                    )
                    db.add(user)
                else:
                    # Update existing
                    user.language_code = row.get('Language', user.language_code) or user.language_code
                    user.balance = parse_decimal(row.get('Total Earned TON', str(user.balance)))
                    if not user.metadata:
                        user.metadata = {}
                    user.metadata.update({
                        'username': row.get('Username', user.metadata.get('username', '')),
                        'wallet_address': row.get('Wallet Address', user.metadata.get('wallet_address', '')),
                        'total_invited': int(row.get('Total Invited', user.metadata.get('total_invited', 0)) or 0),
                        'top_status': row.get('TOP Status', user.metadata.get('top_status', 'locked')) or 'locked',
                    })
                    user.is_active = row.get('Status', 'active') != 'ban'
                
                # Save wallet in business_data if exists
                wallet_address = row.get('Wallet Address', '').strip()
                if wallet_address:
                    wallet_data = BusinessDataModel(
                        id=uuid4(),
                        bot_id=bot_id,
                        data_type='wallet',
                        data={
                            'user_id': str(user.id),
                            'external_id': external_id,
                            'wallet_address': wallet_address,
                        }
                    )
                    db.add(wallet_data)
                
                migrated += 1
                
            except Exception as e:
                print(f"Error migrating user {row.get('User Chat ID', 'unknown')}: {e}")
                continue
    
    db.commit()
    return migrated


def migrate_bot_log(
    db: Session,
    bot_id: str,
    csv_path: str
) -> int:
    """
    Migrate bot_log from CSV to PostgreSQL.
    
    Args:
        db: Database session
        bot_id: Bot UUID
        csv_path: Path to CSV file
    
    Returns:
        Number of migrated log entries
    """
    migrated = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                external_id = str(row.get('User Chat ID', '')).strip()
                if not external_id:
                    continue
                
                # Get user
                user = db.query(UserModel).filter(
                    UserModel.bot_id == bot_id,
                    UserModel.external_id == external_id,
                    UserModel.platform == 'telegram'
                ).first()
                
                if not user:
                    # Skip if user doesn't exist
                    continue
                
                # Create log entry
                ref_param = row.get('Ref Parameter', '').strip()
                click_type = row.get('Click Type', 'Organic')
                
                log_data = BusinessDataModel(
                    id=uuid4(),
                    bot_id=bot_id,
                    data_type='log',
                    data={
                        'user_id': str(user.id),
                        'external_id': external_id,
                        'timestamp': row.get('Timestamp', ''),
                        'message_text': row.get('Message Text', ''),
                        'ref_parameter': ref_param if ref_param and ref_param.upper() != 'NO_REF' else 'NO_REF',
                        'click_type': click_type,
                        'referred_by': row.get('Referred By', ''),
                        'referral_level': int(row.get('Referral Level', 0) or 0),
                        'earned_ton': parse_decimal(row.get('Earned TON', '0')),
                        'payout_status': row.get('Payout Status', 'Unpaid'),
                        'language': row.get('Language', ''),
                        'device': row.get('Device', ''),
                        'geo': row.get('Geo', ''),
                    }
                )
                
                db.add(log_data)
                migrated += 1
                
            except Exception as e:
                print(f"Error migrating log entry: {e}")
                continue
    
    db.commit()
    return migrated


def migrate_partners_settings(
    db: Session,
    bot_id: str,
    csv_path: str
) -> int:
    """
    Migrate Partners_Settings from CSV to PostgreSQL.
    
    Args:
        db: Database session
        bot_id: Bot UUID
        csv_path: Path to CSV file
    
    Returns:
        Number of migrated partners
    """
    migrated = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                bot_name = row.get('Bot Name', '').strip()
                if not bot_name:
                    continue
                
                # Create partner data
                partner_data = BusinessDataModel(
                    id=uuid4(),
                    bot_id=bot_id,
                    data_type='partner',
                    data={
                        'bot_name': bot_name,
                        'description': row.get('Description', ''),
                        'description_en': row.get('Description_en', ''),
                        'description_ru': row.get('Description_ru', ''),
                        'description_de': row.get('Description_de', ''),
                        'description_es': row.get('Description_es', ''),
                        'referral_link': row.get('Referral Link', ''),
                        'commission': parse_decimal(row.get('Commission (%)', '0')),
                        'category': row.get('Category', 'NEW'),
                        'active': row.get('Active', 'Yes'),
                        'verified': row.get('Verified', 'Yes'),
                        'roi_score': parse_decimal(row.get('ROI Score', '0')),
                        'duration': row.get('Duration', ''),
                        'gpt': row.get('GPT', ''),
                        'short_link': row.get('Short Link', ''),
                        'added': row.get('Added', ''),
                        'owner': row.get('Owner', ''),
                    }
                )
                
                db.add(partner_data)
                migrated += 1
                
            except Exception as e:
                print(f"Error migrating partner {row.get('Bot Name', 'unknown')}: {e}")
                continue
    
    db.commit()
    return migrated


def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate data from Google Sheets to PostgreSQL')
    parser.add_argument('--bot-id', required=True, help='Bot UUID')
    parser.add_argument('--user-wallets', help='Path to user_wallets CSV file')
    parser.add_argument('--bot-log', help='Path to bot_log CSV file')
    parser.add_argument('--partners', help='Path to Partners_Settings CSV file')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        # Verify bot exists
        bot = db.query(BotModel).filter(BotModel.id == args.bot_id).first()
        if not bot:
            print(f"❌ Bot {args.bot_id} not found. Please create bot first.")
            return
        
        print(f"📦 Migrating data for bot: {bot.name} ({bot.id})")
        
        total_migrated = 0
        
        # Migrate user_wallets
        if args.user_wallets:
            print(f"\n📥 Migrating user_wallets from {args.user_wallets}...")
            count = migrate_user_wallets(db, args.bot_id, args.user_wallets)
            print(f"✅ Migrated {count} users")
            total_migrated += count
        
        # Migrate bot_log
        if args.bot_log:
            print(f"\n📥 Migrating bot_log from {args.bot_log}...")
            count = migrate_bot_log(db, args.bot_id, args.bot_log)
            print(f"✅ Migrated {count} log entries")
            total_migrated += count
        
        # Migrate partners
        if args.partners:
            print(f"\n📥 Migrating Partners_Settings from {args.partners}...")
            count = migrate_partners_settings(db, args.bot_id, args.partners)
            print(f"✅ Migrated {count} partners")
            total_migrated += count
        
        print(f"\n🎉 Total migrated: {total_migrated} records")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Migration error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

