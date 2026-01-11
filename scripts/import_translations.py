"""
Script to import translations from CSV to PostgreSQL
"""
import csv
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


def import_translations(csv_path: str):
    """Import translations from CSV file"""
    db: Session = SessionLocal()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            imported = 0
            skipped = 0
            
            for row in reader:
                lang = row['language'].strip()
                key = row['message_key'].strip()
                text = row['text'].strip()
                
                # Check if translation already exists
                existing = db.query(Translation).filter(
                    Translation.key == key,
                    Translation.lang == lang
                ).first()
                
                if existing:
                    # Update existing translation
                    existing.text = text
                    skipped += 1
                else:
                    # Create new translation
                    translation = Translation(
                        key=key,
                        lang=lang,
                        text=text
                    )
                    db.add(translation)
                    imported += 1
            
            db.commit()
            print(f"✅ Imported {imported} translations")
            print(f"⚠️  Updated {skipped} existing translations")
            
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Import translations from CSV')
    parser.add_argument('--csv', help='Path to translations CSV file', 
                       default=str(Path(__file__).parent / "mini_app_ui_translations.csv"))
    
    args = parser.parse_args()
    csv_path = Path(args.csv)
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        print(f"💡 Usage: python scripts/import_translations.py --csv path/to/translations.csv")
        sys.exit(1)
    
    print(f"📥 Importing translations from {csv_path}")
    import_translations(str(csv_path))
    print("✅ Done!")

