#!/usr/bin/env python3
"""
Створення таблиць БД для Universal Bot OS
Використовується при першому запуску або міграції
"""
import sys
from pathlib import Path

# Додати корінь проекту в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import engine, Base
from app.models import bot, user, message, translation, business_data

def create_tables():
    """Створити всі таблиці в БД"""
    print("🔧 Створюю таблиці в БД...")
    
    try:
        # Імпортувати всі моделі
        from app.models.bot import Bot
        from app.models.user import User
        from app.models.message import Message
        from app.models.translation import Translation
        from app.models.business_data import BusinessData
        
        # Створити всі таблиці
        Base.metadata.create_all(bind=engine)
        
        print("✅ Таблиці створено успішно!")
        print("\n📋 Створені таблиці:")
        print("   - bots")
        print("   - users")
        print("   - messages")
        print("   - translations")
        print("   - business_data")
        
    except Exception as e:
        print(f"❌ Помилка при створенні таблиць: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_tables()

