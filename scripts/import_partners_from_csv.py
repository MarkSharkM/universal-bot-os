"""
Quick import script for Partners_Settings from CSV
Can be used for initial import or updates
"""
import csv
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.business_data import BusinessData
from app.models.bot import Bot
from uuid import UUID


def parse_decimal(value: str) -> Decimal:
    """Parse decimal value"""
    if not value or value.strip() == '':
        return Decimal('0.0')
    try:
        value = str(value).replace(',', '.')
        return Decimal(value)
    except:
        return Decimal('0.0')


def import_partners(
    bot_id: str,
    csv_path: str,
    update_existing: bool = False
):
    """
    Import partners from CSV file.
    
    Args:
        bot_id: Bot UUID (as string)
        csv_path: Path to CSV file
        update_existing: If True, update existing partners by bot_name
    """
    db: Session = SessionLocal()
    
    try:
        # Verify bot exists
        bot = db.query(Bot).filter(Bot.id == bot_id).first()
        if not bot:
            print(f"❌ Bot {bot_id} not found")
            return
        
        print(f"📦 Importing partners for bot: {bot.name}")
        
        imported = 0
        updated = 0
        skipped = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    bot_name = row.get('Bot Name', '').strip()
                    if not bot_name:
                        skipped += 1
                        continue
                    
                    # Check if partner exists
                    existing = db.query(BusinessData).filter(
                        BusinessData.bot_id == bot_id,
                        BusinessData.data_type == 'partner',
                        BusinessData.data['bot_name'].astext == bot_name
                    ).first()
                    
                    if existing and not update_existing:
                        skipped += 1
                        continue
                    
                    partner_data = {
                        'bot_name': bot_name,
                        'description': row.get('Description', ''),
                        'description_en': row.get('Description_en', ''),
                        'description_ru': row.get('Description_ru', ''),
                        'description_de': row.get('Description_de', ''),
                        'description_es': row.get('Description_es', ''),
                        'referral_link': row.get('Referral Link', ''),
                        'commission': float(parse_decimal(row.get('Commission (%)', '0'))),
                        'category': row.get('Category', 'NEW'),
                        'active': row.get('Active', 'Yes'),
                        'verified': row.get('Verified', 'Yes'),
                        'roi_score': float(parse_decimal(row.get('ROI Score', '0'))),
                        'duration': row.get('Duration', ''),
                        'gpt': row.get('GPT', ''),
                        'short_link': row.get('Short Link', ''),
                        'added': row.get('Added', ''),
                        'owner': row.get('Owner', ''),
                    }
                    
                    if existing and update_existing:
                        # Update existing
                        existing.data = partner_data
                        updated += 1
                    else:
                        # Create new
                        partner = BusinessData(
                            bot_id=bot_id,
                            data_type='partner',
                            data=partner_data
                        )
                        db.add(partner)
                        imported += 1
                    
                except Exception as e:
                    print(f"⚠️  Error importing {row.get('Bot Name', 'unknown')}: {e}")
                    skipped += 1
                    continue
        
        db.commit()
        
        print(f"\n✅ Imported: {imported}")
        print(f"🔄 Updated: {updated}")
        print(f"⏭️  Skipped: {skipped}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Import partners from CSV')
    parser.add_argument('--bot-id', required=True, help='Bot UUID')
    parser.add_argument('--csv', required=True, help='Path to Partners_Settings CSV file')
    parser.add_argument('--update', action='store_true', help='Update existing partners')
    
    args = parser.parse_args()
    
    import_partners(args.bot_id, args.csv, args.update)

