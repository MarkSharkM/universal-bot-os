"""
Script to fix share text translations in database
Replaces old "7% RevShare" text with unified message
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env BEFORE importing anything from app
try:
    from dotenv import load_dotenv
    root_env = Path(__file__).parent.parent / ".env"
    parent_env = Path(__file__).parent.parent.parent / ".env"
    
    if root_env.exists():
        load_dotenv(root_env)
        print(f"✅ Loaded .env from {root_env}")
    elif parent_env.exists():
        load_dotenv(parent_env)
        print(f"✅ Loaded .env from {parent_env}")
except ImportError:
    print("⚠️  python-dotenv not installed, relying on system environment")

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.translation import Translation
from app.core.database import Base

# Create tables
Base.metadata.create_all(bind=engine)


def fix_share_text():
    """Fix share text translations"""
    db: Session = SessionLocal()
    
    try:
        # Define new translations
        translations_to_update = [
            # share_text_pro
            {'key': 'share_text_pro', 'lang': 'uk', 'text': '🚀 Долучайся до EarnHubAggregatorBot — отримуй зірки за активність!'},
            {'key': 'share_text_pro', 'lang': 'en', 'text': '🚀 Join EarnHubAggregatorBot — earn Stars for your activity!'},
            {'key': 'share_text_pro', 'lang': 'ru', 'text': '🚀 Присоединяйся к EarnHubAggregatorBot — получай звёзды за активность!'},
            {'key': 'share_text_pro', 'lang': 'de', 'text': '🚀 Tritt EarnHubAggregatorBot bei — sammle Stars für deine Aktivität!'},
            {'key': 'share_text_pro', 'lang': 'es', 'text': '🚀 ¡Únete a EarnHubAggregatorBot — gana Stars por tu actividad!'},
            
            # share_text_starter (same as pro)
            {'key': 'share_text_starter', 'lang': 'uk', 'text': '🚀 Долучайся до EarnHubAggregatorBot — отримуй зірки за активність!'},
            {'key': 'share_text_starter', 'lang': 'en', 'text': '🚀 Join EarnHubAggregatorBot — earn Stars for your activity!'},
            {'key': 'share_text_starter', 'lang': 'ru', 'text': '🚀 Присоединяйся к EarnHubAggregatorBot — получай звёзды за активность!'},
            {'key': 'share_text_starter', 'lang': 'de', 'text': '🚀 Tritt EarnHubAggregatorBot bei — sammle Stars für deine Aktivität!'},
            {'key': 'share_text_starter', 'lang': 'es', 'text': '🚀 ¡Únete a EarnHubAggregatorBot — gana Stars por tu actividad!'},
        ]
        
        updated = 0
        created = 0
        
        for trans_data in translations_to_update:
            # Check if translation exists
            existing = db.query(Translation).filter(
                Translation.key == trans_data['key'],
                Translation.lang == trans_data['lang']
            ).first()
            
            if existing:
                # Update existing
                old_text = existing.text
                existing.text = trans_data['text']
                updated += 1
                print(f"✅ Updated {trans_data['key']} ({trans_data['lang']})")
                if '7%' in old_text or 'RevShare' in old_text:
                    print(f"   Old: {old_text[:80]}...")
                    print(f"   New: {trans_data['text']}")
            else:
                # Create new
                translation = Translation(
                    key=trans_data['key'],
                    lang=trans_data['lang'],
                    text=trans_data['text']
                )
                db.add(translation)
                created += 1
                print(f"✅ Created {trans_data['key']} ({trans_data['lang']})")
        
        db.commit()
        print(f"\n✅ Updated {updated} translations")
        print(f"✅ Created {created} new translations")
        print(f"\n🎉 Share text translations fixed!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("📥 Fixing share text translations...")
    fix_share_text()
    print("✅ Done!")
