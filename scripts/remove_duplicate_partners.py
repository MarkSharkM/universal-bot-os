"""
Remove duplicate partners from database.
Keeps the first occurrence of each partner (by bot_name) and deletes duplicates.
"""
import sys
import os
from sqlalchemy import and_

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.business_data import BusinessData


def remove_duplicates(bot_id: str):
    """Remove duplicate partners for a specific bot"""
    db = SessionLocal()
    try:
        # Get all partners for this bot
        partners = db.query(BusinessData).filter(
            and_(
                BusinessData.bot_id == bot_id,
                BusinessData.data_type == 'partner'
            )
        ).all()
        
        print(f"Found {len(partners)} total partners")
        
        # Group by bot_name
        seen = {}
        duplicates = []
        
        for partner in partners:
            bot_name = partner.data.get('bot_name')
            if not bot_name:
                continue
            
            if bot_name not in seen:
                seen[bot_name] = partner
                print(f"✅ Keeping: {bot_name} (ID: {partner.id})")
            else:
                duplicates.append(partner)
                print(f"❌ Duplicate: {bot_name} (ID: {partner.id})")
        
        if not duplicates:
            print("\n✅ No duplicates found!")
            return
        
        print(f"\n🗑️  Found {len(duplicates)} duplicates to remove")
        
        # Confirm deletion
        response = input("\nDo you want to delete these duplicates? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return
        
        # Delete duplicates
        for dup in duplicates:
            db.delete(dup)
            print(f"🗑️  Deleted: {dup.data.get('bot_name')} (ID: {dup.id})")
        
        db.commit()
        print(f"\n✅ Successfully removed {len(duplicates)} duplicate partners!")
        
        # Show final count
        final_count = db.query(BusinessData).filter(
            and_(
                BusinessData.bot_id == bot_id,
                BusinessData.data_type == 'partner'
            )
        ).count()
        
        print(f"📊 Final partner count: {final_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # EarnHubAggregatorBot ID
    BOT_ID = "4f3c45a5-39ac-4d6e-a0eb-263765d70b1a"
    
    print("🔍 Removing duplicate partners...")
    print(f"Bot ID: {BOT_ID}\n")
    
    remove_duplicates(BOT_ID)

