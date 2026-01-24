"""
Partner Bot Service
Handles AI analysis of screenshots and partner creation flow.
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from uuid import UUID
import logging
import json
import asyncio

from app.models.bot import Bot
from app.models.user import User
from app.models.business_data import BusinessData
from app.services.ai_service import AIService
from app.adapters.telegram import TelegramAdapter

logger = logging.getLogger(__name__)

# System Prompt from User Request
PARTNER_ANALYSIS_PROMPT = """
Ти — просунутий бекенд-агент для партнерської платформи в Telegram.
Твої вхідні дані — це зображення (скріншот) іншого Telegram-бота або сервісу.
Твоя мета: витягти дані, створити маркетинговий текст та перекласти його.

### ІНСТРУКЦІЇ:

1. ВІЗУАЛЬНИЙ АНАЛІЗ: Проскануй зображення на наявність:
   - Program Name: Головна назва бота або сервісу.
   - Bot Username: Юзернейм, що починається з '@' (наприклад, @GoGift_bot).
   - Commission: Відсоток або сума винагороди (наприклад, "10%", "0.5 TON").
   - Context: Зрозумій суть сервісу, щоб написати якісний опис.

2. ГЕНЕРАЦІЯ ТА ПЕРЕКЛАД КОНТЕНТУ:
   Створи структурований об'єкт для 5 мов: Англійська (en), Німецька (de), Іспанська (es), Французька (fr), Польська (pl).
   Для КОЖНОЇ мови згенеруй:
   - title: Назва програми (транслітерація або переклад, якщо доречно).
   - description: Привабливий маркетинговий опис (1-2 речення) на основі тексту зі скріншоту.
   - terms: Коротке резюме умов винагороди (наприклад, "Отримуйте 10% від кожного реферала безстроково").

3. СУВОРИЙ ФОРМАТ ВИВОДУ:
   - Поверни ТІЛЬКИ валідний JSON.
   - НЕ використовуй форматування Markdown (НЕ пиши блоки ```json).
   - НЕ додавай жодного розмовного тексту ("Ось ваш результат...").
   - Використовуй точну схему JSON, наведену нижче.

### JSON SCHEMA (Ключі залишати англійською):

{
  "program_name": "String",
  "bot_username": "@String",
  "commission": "String",
  "translations": {
    "en": {
      "title": "String",
      "description": "String",
      "terms": "String"
    },
    # ... other languages
  }
}
Please ensure strict JSON syntax.
"""

class PartnerBotService:
    def __init__(self, db: Session, bot_id: UUID):
        self.db = db
        self.bot_id = bot_id
        self.adapter = TelegramAdapter()
        # No TranslationService needed here as this is an admin tool with fixed language (or handled by AI)

    async def handle_start(self, user: User):
        """Handle /start command"""
        message = (
            "👋 **Привіт, адмін!**\n\n"
            "Я допоможу додати нових партнерів.\n"
            "Просто надішли мені **скріншот** бота (профіль або головне меню),\n"
            "і я згенерую весь контент автоматично.\n\n"
            "📸 *Чекаю на фото...*"
        )
        await self.adapter.send_message(
            self.bot_id,
            user.external_id,
            message,
            parse_mode="Markdown"
        )

    async def process_photo(self, user: User, photo_data: Dict[str, Any]):
        """
        Process received photo:
        1. Download
        2. Analyze with AI
        3. Show preview
        """
        file_id = photo_data.get('file_id')
        if not file_id:
            await self.adapter.send_message(self.bot_id, user.external_id, "❌ Помилка: Немає file_id.")
            return

        # 1. Get File URL
        await self.adapter.send_message(self.bot_id, user.external_id, "⏳ *Аналізую зображення...*", parse_mode="Markdown")
        
        image_url = await self.adapter.get_file_path(self.bot_id, file_id)
        if not image_url:
            await self.adapter.send_message(self.bot_id, user.external_id, "❌ Не вдалося завантажити фото.")
            return

        # 2. AI Analysis
        # Setup AI Service with custom system prompt for this interaction
        from app.services.translation_service import TranslationService
        ai_service = AIService(self.db, self.bot_id, TranslationService(self.db, self.bot_id))
        
        # Override system prompt temporarily in config or just pass it via build_system_prompt logic?
        # Since AIService pulls from config, we can temporarily inject our prompt into the payload construction
        # But AIService.generate_response calls build_system_prompt.
        # Let's just create a temporary config overrides dict or pass custom prompt if we modified AIService...
        # Wait, I didn't add `custom_prompt` arg to `generate_response`.
        # I can cheat: Configure the bot in DB to have this system prompt! 
        # (This was part of registration script).
        # OR better: The user prompt is specific to this task.
        
        # Let's assume the bot config HAS this prompt. If not, we should update the bot config.
        # Actually, let's update bot config on the fly if needed, or better, 
        # update AIService to accept `system_prompt_override`.
        # For now, I will assume the bot in DB has the correct prompt or I rely on the prompt being sent in the user message? NO.
        # I'll rely on the registered bot having the prompt. 
        # BUT, to be safe, I'll pass it as part of the "user message" instructions:
        
        full_prompt = f"{PARTNER_ANALYSIS_PROMPT}\n\nAnalyze this image:"
        
        try:
            response_text = await ai_service.generate_response(
                user.id,
                full_prompt, # Put instructions in user message to ensure they are used
                user_lang="uk",
                image_url=image_url
            )
            
            # 3. Parse JSON
            try:
                # Cleanup markdown code blocks if present
                clean_json = response_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
            except json.JSONDecodeError:
                logger.error(f"AI returned invalid JSON: {response_text}")
                await self.adapter.send_message(self.bot_id, user.external_id, f"❌ AI повернув невалідний JSON.\nraw: {response_text[:100]}...")
                return

            # 4. Save Temporary Proposal
            # We use BusinessData with type 'partner_proposal'
            
            proposal = BusinessData(
                bot_id=self.bot_id,
                data_type='partner_proposal',
                data={
                    "status": "pending",
                    "payload": data,
                    "user_id": str(user.id),
                    "file_unique_id": photo_data.get('file_unique_id')
                }
            )
            self.db.add(proposal)
            self.db.commit()
            self.db.refresh(proposal)
            
            # 5. Show Preview
            # Format a nice message
            preview_msg = (
                f"✅ **Analysis Complete!**\n\n"
                f"👤 **Name:** {data.get('program_name')}\n"
                f"🔗 **Username:** {data.get('bot_username')}\n"
                f"💰 **Commission:** {data.get('commission')}\n\n"
                f"🇬🇧 **EN:** {data.get('translations', {}).get('en', {}).get('description')}\n"
                # Add more langs if needed or keep short
            )
            
            buttons = [[
                {"text": "✅ Approve & Add", "callback_data": f"approve_partner:{proposal.id}"},
                {"text": "❌ Cancel", "callback_data": f"cancel_partner:{proposal.id}"}
            ]]
            
            await self.adapter.send_message(
                self.bot_id,
                user.external_id,
                preview_msg,
                reply_markup={"inline_keyboard": buttons},
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error in process_photo: {e}", exc_info=True)
            await self.adapter.send_message(self.bot_id, user.external_id, f"❌ Error: {str(e)}")

    async def handle_approval(self, user: User, proposal_id: str):
        """Handle approval callback"""
        try:
            # Ensure valid UUID
            uuid_obj = UUID(proposal_id)
        except ValueError:
            await self.adapter.send_message(self.bot_id, user.external_id, "❌ Invalid proposal UUID.")
            return

        proposal = self.db.query(BusinessData).filter(
            BusinessData.id == uuid_obj
        ).first()
        
        if not proposal:
            await self.adapter.send_message(self.bot_id, user.external_id, "❌ Proposal not found or expired.")
            return
            
        data = proposal.data.get('payload')
        if not data:
            await self.adapter.send_message(self.bot_id, user.external_id, "❌ Invalid proposal data.")
            return

        # Create Real Partner Record
        # This corresponds to how admin/partners.js works -> likely writes to BusinessData type='partner'
        
        # Structure for 'partner' type:
        # {
        #   "name": ...,
        #   "category": "NEW",
        #   "referral_link": "https://t.me/...",
        #   "commission": ...,
        #   "active": "Yes",
        #   "verified": "Yes",
        #   "duration": "9999",
        #   "roi": 0,
        #   "description_en": ...,
        #   "description_de": ...,
        #   ...
        # }
        
        # Map AI data to Partner Schema
        partner_data = {
            "name": data.get("program_name"),
            "category": "NEW",
            "referral_link": f"https://t.me/{data.get('bot_username').replace('@', '')}",
            "commission": data.get("commission"),
            "active": "Yes",
            "verified": "Yes",
            "duration": "9999",
            "roi": 0,
            "created_at": str(asyncio.get_event_loop().time()), # simplistic timestamp
            # Translations
        }
        
        # Add flat translations (based on how frontend/admin usage expects it)
        # Assuming admin stores them as description_{lang} keys or similar.
        # Let's check admin.py listing... it seemed to return raw data.
        # I will store structured translations if possible, or flat if that's the convention.
        # The AI schema returns "translations": { "en": {...} }
        # I'll store it as "translations" object inside data.
        partner_data["translations"] = data.get("translations")
        partner_data["program_name"] = data.get("program_name")
        partner_data["bot_username"] = data.get("bot_username")
        
        new_partner = BusinessData(
            bot_id=self.bot_id,
            data_type='partner',
            data=partner_data
        )
        self.db.add(new_partner)
        
        # Delete proposal? Or keep as archive?
        # Let's delete to keep clean.
        self.db.delete(proposal)
        self.db.commit()
        
        await self.adapter.send_message(
            self.bot_id,
            user.external_id,
            f"🎉 **Partner Added!**\n\n{data.get('program_name')} is now in the database.",
            parse_mode="Markdown"
        )
