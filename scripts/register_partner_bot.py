from sqlalchemy.orm import Session
from dotenv import load_dotenv
load_dotenv() # Load .env file

from app.core.database import SessionLocal
from app.models.bot import Bot
from app.utils.encryption import encrypt_token, hash_token

def register_bot():
    db = SessionLocal()
    try:
        token = "7563402433:AAGtA2WzumIu1yWaNJxkmxwu4k1uKoUIT84"
        # Check if bot exists by token (we can't easily check encrypted token without decrypting all, 
        # so checking by name or platform_type + partial match might be better, 
        # but for now let's check by name)
        existing_bot = db.query(Bot).filter(Bot.name == "HubPartnerbot").first()
        
        if existing_bot:
            print(f"Bot already exists: {existing_bot.name} ({existing_bot.id})")
            return

        encrypted_token = encrypt_token(token)
        token_hash_value = hash_token(token)  # SHA-256 hash for fast lookup
        
        bot = Bot(
            name="HubPartnerbot",
            platform_type="telegram",
            token=encrypted_token,
            token_hash=token_hash_value,  # Add hash for O(1) lookup
            default_lang="uk",
            config={
                "role": "admin_helper",
                "ai": {
                    "provider": "openai",
                    "model": "gpt-4o", # Vision supported
                    "system_prompt": "You are a Partner Bot."
                }
            },
            is_active=True
        )
        db.add(bot)
        db.commit()
        print(f"Bot created: {bot.id}")
        print(f"Token hash: {token_hash_value[:16]}... (for debugging)")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    register_bot()
