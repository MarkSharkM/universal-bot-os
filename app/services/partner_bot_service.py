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
   - Program Name: Головна назва бота або сервісу (видима назва на скріні).
   - Bot Username: Юзернейм, що починається з '@' (наприклад, @GoGift_bot).
   - Context: Зрозумій суть сервісу, щоб написати якісний опис.
   - Icon/Emoji: Якщо бачиш емодзі/іконку бота - включи її в опис (наприклад, 🎁, 💎, 🏦).
   
   ВАЖЛИВО: НЕ витягуй referral_link, commission, duration, average_income зі скріна!
   Адмін додасть ці дані вручну через Edit.

2. ГЕНЕРАЦІЯ ТА ПЕРЕКЛАД КОНТЕНТУ:
   Створи структурований об'єкт для 5 мов: Українська (uk), Англійська (en), Російська (ru), Німецька (de), Іспанська (es).
   
   ВАЖЛИВО: Обов'язково додавай емодзі/іконки в описи для візуальної привабливості!
   
   Для КОЖНОЇ мови згенеруй:
   - title: Назва програми (транслітерація або переклад, якщо доречно).
   - description: Привабливий маркетинговий опис (1-2 речення) на основі тексту зі скріншоту.
     * ОБОВ'ЯЗКОВО включай емодзі в опис (🎁, 💎, 🏦, 🎯, 💰, ⭐, 🚀, etc.)
     * Формат: "Emoji Короткий опис що це Emoji"
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
  "translations": {
    "uk": {
      "title": "String",
      "description": "String with Emoji 🎁",
      "terms": "String"
    },
    "en": {
      "title": "String",
      "description": "String with Emoji 🎁",
      "terms": "String"
    },
    "ru": {
      "title": "String", 
      "description": "String with Emoji 🎁",
      "terms": "String"
    },
    "de": {...},
    "es": {...}
  }
}

ПРИКЛАД ХОРОШОГО ОПИСУ:
"🎁 Подарунки за активність" (UK)
"🎁 Gifts for activity" (EN)
"💎 Зірки за транзакції 🏦" (UK)

Please ensure strict JSON syntax and ALWAYS include emojis in descriptions!
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
            # Format a nice message using HTML (more reliable than Markdown)
            # Show ALL translations for review
            from html import escape
            
            program_name = escape(data.get('program_name', 'N/A'))
            bot_username = escape(data.get('bot_username', 'N/A'))
            
            # These fields are added manually by admin via Edit
            commission = data.get('commission', 0)
            duration = data.get('duration', 9999)
            average_income = data.get('average_income', 0)
            referral_link = data.get('referral_link', '')
            
            # Calculate ROI
            roi_score = round((float(commission) / 100) * float(average_income), 1) if commission and average_income else 0.0
            
            translations = data.get('translations', {})
            
            # Build preview with all translations
            preview_msg = (
                f"✅ <b>Analysis Complete!</b>\n\n"
                f"👤 <b>Name:</b> {program_name}\n"
                f"🔗 <b>Username:</b> {bot_username}\n\n"
                f"<b>📊 Фінансові дані (додай через Edit):</b>\n"
                f"🔗 <b>Link:</b> {escape(referral_link[:50]) if referral_link else '❌ Не вказано'}...\n"
                f"💰 <b>Commission:</b> {commission}%\n"
                f"⏳ <b>Duration:</b> {duration} days\n"
                f"📊 <b>Avg Income:</b> {average_income}\n"
                f"⭐ <b>ROI Score:</b> {roi_score}\n\n"
                f"📝 <b>Translations:</b>\n\n"
            )
            
            # Add all languages
            lang_flags = {
                'uk': '🇺🇦',
                'en': '🇬🇧',
                'ru': '🇷🇺',
                'de': '🇩🇪',
                'es': '🇪🇸'
            }
            
            for lang, flag in lang_flags.items():
                trans = translations.get(lang, {})
                title = escape(trans.get('title', 'N/A'))
                desc = escape(trans.get('description', 'N/A')[:80])  # First 80 chars
                preview_msg += f"{flag} <b>{lang.upper()}:</b> {title}\n{desc}...\n\n"
            
            # Get list of available bots for selection
            available_bots = self.db.query(Bot).filter(
                Bot.platform_type == "telegram",
                Bot.is_active == True
            ).all()
            
            # Filter out admin helper bots (Partner Bot itself)
            main_bots = [b for b in available_bots if not (b.config and b.config.get('role') == 'admin_helper')]
            
            # Create buttons with bot selection
            buttons = []
            
            if len(main_bots) == 1:
                # Only one bot - skip selection, go straight to approve
                target_bot = main_bots[0]
                buttons = [
                    [{"text": "✏️ Edit", "callback_data": f"edit_partner:{proposal.id}"}],
                    [
                        {"text": f"✅ Add to {target_bot.name}", "callback_data": f"approve_partner:{proposal.id}:{target_bot.id}"},
                        {"text": "❌ Cancel", "callback_data": f"cancel_partner:{proposal.id}"}
                    ]
                ]
            else:
                # Multiple bots - show selection
                buttons.append([{"text": "✏️ Edit", "callback_data": f"edit_partner:{proposal.id}"}])
                
                for bot in main_bots:
                    bot_name = bot.name[:25]  # Truncate long names
                    buttons.append([
                        {"text": f"➕ Add to {bot_name}", "callback_data": f"approve_partner:{proposal.id}:{bot.id}"}
                    ])
                
                buttons.append([{"text": "❌ Cancel", "callback_data": f"cancel_partner:{proposal.id}"}])
            
            await self.adapter.send_message(
                self.bot_id,
                user.external_id,
                preview_msg,
                reply_markup={"inline_keyboard": buttons},
                parse_mode="HTML"
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

    async def handle_approval(self, user: User, proposal_id: str, target_bot_id: str = None):
        """
        Handle approval callback - adds partner to TARGET bot.
        
        Args:
            user: User who approved
            proposal_id: Proposal UUID
            target_bot_id: Target bot UUID (from callback_data)
        """
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

        # Convert target_bot_id to UUID if provided
        if target_bot_id:
            try:
                from uuid import UUID as UUID_type
                target_bot_uuid = UUID_type(target_bot_id)
            except ValueError:
                await self.adapter.send_message(self.bot_id, user.external_id, f"❌ Invalid target bot ID: {target_bot_id}")
                return
        else:
            # No target specified - should not happen with new UI, but handle gracefully
            await self.adapter.send_message(self.bot_id, user.external_id, "❌ No target bot specified.")
            return

        # Verify target bot exists
        target_bot = self.db.query(Bot).filter(Bot.id == target_bot_uuid).first()
        if not target_bot:
            await self.adapter.send_message(self.bot_id, user.external_id, f"❌ Target bot not found: {target_bot_id}")
            return

        # Create Real Partner Record in TARGET bot
        translations = data.get("translations", {})
        
        # Validate required fields
        referral_link = data.get("referral_link", "").strip()
        if not referral_link:
            await self.adapter.send_message(
                self.bot_id,
                user.external_id,
                "❌ <b>Referral Link відсутній!</b>\n\nДодайте через Edit:\n<code>referral_link: https://t.me/...</code>",
                parse_mode="HTML"
            )
            return
        
        commission = float(data.get("commission", 0))
        if not commission:
            await self.adapter.send_message(
                self.bot_id,
                user.external_id,
                "❌ <b>Commission відсутня!</b>\n\nДодайте через Edit:\n<code>commission: 30</code>",
                parse_mode="HTML"
            )
            return
        
        # Calculate ROI: (commission / 100) * average_income
        average_income = float(data.get("average_income", 0))
        roi_score = round((commission / 100) * average_income, 1) if commission and average_income else 0.0
        
        partner_data = {
            "bot_name": data.get("program_name"),  # Main name
            "category": "NEW",
            "referral_link": referral_link,
            "commission": commission,
            "active": "Yes",
            "verified": "Yes",
            "duration": str(data.get("duration", 9999)),
            "roi_score": roi_score,
            "gpt": "",
            "short_link": "",
            # Flat translation structure (matches existing partners)
            # Primary description (Ukrainian as main)
            "description": translations.get("uk", {}).get("description", translations.get("en", {}).get("description", "")),
            # All language descriptions
            "description_en": translations.get("en", {}).get("description", ""),
            "description_ru": translations.get("ru", {}).get("description", translations.get("en", {}).get("description", "")),
            "description_de": translations.get("de", {}).get("description", ""),
            "description_es": translations.get("es", {}).get("description", ""),
        }
        
        new_partner = BusinessData(
            bot_id=target_bot_uuid,  # Add to TARGET bot (selected by admin)
            data_type='partner',
            data=partner_data
        )
        self.db.add(new_partner)
        
        # Delete proposal
        self.db.delete(proposal)
        self.db.commit()
        
        await self.adapter.send_message(
            self.bot_id,
            user.external_id,
            f"🎉 <b>Partner Added!</b>\n\n{data.get('program_name')} додано в <b>{target_bot.name}</b>.",
            parse_mode="HTML"
        )

    async def handle_edit(self, user: User, proposal_id: str):
        """Handle edit callback - show editable fields"""
        try:
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
        
        # Show edit menu with buttons for each field
        from html import escape
        
        edit_msg = (
            f"✏️ <b>Edit Partner Data</b>\n\n"
            f"Оберіть що хочете змінити:\n\n"
            f"<b>Поточні дані:</b>\n"
            f"• Name: {escape(data.get('program_name', 'N/A'))}\n"
            f"• Username: {escape(data.get('bot_username', 'N/A'))}\n"
            f"• Commission: {escape(str(data.get('commission', 'N/A')))}\n"
            f"• Duration: {escape(str(data.get('duration', 'N/A')))} days\n"
            f"• Avg Income: {escape(str(data.get('average_income', 'N/A')))}\n"
            f"• Referral Link: {escape(data.get('referral_link', 'N/A')[:50])}...\n\n"
            f"Або відправте текст в форматі:\n"
            f"<code>field: value</code>\n\n"
            f"<b>Доступні поля:</b>\n"
            f"• name: [назва програми]\n"
            f"• username: @username\n"
            f"• commission: 30\n"
            f"• duration: 365\n"
            f"• average_income: 23.90\n"
            f"• referral_link: https://t.me/...\n"
            f"• uk_title, uk_description\n"
            f"• en_title, en_description\n"
            f"• ru_title, ru_description\n"
            f"• de_title, de_description\n"
            f"• es_title, es_description\n\n"
            f"<b>Приклад:</b>\n"
            f"<code>commission: 40</code>\n"
            f"<code>average_income: 15.5</code>\n"
            f"<code>uk_description: 🎁 Подарунки за активність</code>"
        )
        
        buttons = [
            [{"text": "🔙 Back to Preview", "callback_data": f"preview_partner:{proposal.id}"}],
            [
                {"text": "✅ Save & Approve", "callback_data": f"approve_partner:{proposal.id}"},
                {"text": "❌ Cancel", "callback_data": f"cancel_partner:{proposal.id}"}
            ]
        ]
        
        await self.adapter.send_message(
            self.bot_id,
            user.external_id,
            edit_msg,
            reply_markup={"inline_keyboard": buttons},
            parse_mode="HTML"
        )
        
    async def handle_text_edit(self, user: User, text: str):
        """Handle text-based editing of proposal"""
        # Find latest pending proposal for this user
        proposal = self.db.query(BusinessData).filter(
            BusinessData.bot_id == self.bot_id,
            BusinessData.data_type == 'partner_proposal',
            BusinessData.data['status'].astext == 'pending',
            BusinessData.data['user_id'].astext == str(user.id)
        ).order_by(BusinessData.created_at.desc()).first()
        
        if not proposal:
            await self.adapter.send_message(
                self.bot_id, 
                user.external_id, 
                "❌ Не знайдено активного proposal для редагування.\nСпочатку надішліть скріншот."
            )
            return
        
        # Parse text: "field: value"
        if ':' not in text:
            await self.adapter.send_message(
                self.bot_id,
                user.external_id,
                "❌ Невірний формат. Використовуйте:\n<code>field: value</code>",
                parse_mode="HTML"
            )
            return
        
        field, value = text.split(':', 1)
        field = field.strip().lower()
        value = value.strip()
        
        data = proposal.data.get('payload', {})
        
        # Update based on field
        if field == 'name':
            data['program_name'] = value
        elif field == 'username':
            data['bot_username'] = value if value.startswith('@') else f'@{value}'
        elif field == 'commission':
            # Remove % if present, convert to float
            value_clean = value.replace('%', '').strip()
            try:
                data['commission'] = float(value_clean)
            except ValueError:
                await self.adapter.send_message(
                    self.bot_id,
                    user.external_id,
                    f"❌ Commission має бути числом (наприклад: 30)"
                )
                return
        elif field == 'duration':
            try:
                data['duration'] = int(value)
            except ValueError:
                await self.adapter.send_message(
                    self.bot_id,
                    user.external_id,
                    f"❌ Duration має бути числом (наприклад: 365)"
                )
                return
        elif field == 'average_income':
            try:
                data['average_income'] = float(value)
            except ValueError:
                await self.adapter.send_message(
                    self.bot_id,
                    user.external_id,
                    f"❌ Average Income має бути числом (наприклад: 23.90)"
                )
                return
        elif field == 'referral_link':
            data['referral_link'] = value
        elif '_' in field:  # Language-specific field (e.g., en_title)
            lang, sub_field = field.split('_', 1)
            if lang in ['uk', 'en', 'ru', 'de', 'es']:
                if 'translations' not in data:
                    data['translations'] = {}
                if lang not in data['translations']:
                    data['translations'][lang] = {}
                data['translations'][lang][sub_field] = value
        else:
            await self.adapter.send_message(
                self.bot_id,
                user.external_id,
                f"❌ Невідоме поле: {field}\nДив. список доступних полів."
            )
            return
        
        # Save updated data
        proposal.data['payload'] = data
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(proposal, 'data')
        self.db.commit()
        
        await self.adapter.send_message(
            self.bot_id,
            user.external_id,
            f"✅ Оновлено: <b>{field}</b> = {value}",
            parse_mode="HTML"
        )
        
        # Show updated preview
        await self.show_preview(user, proposal)
    
    async def show_preview(self, user: User, proposal: BusinessData):
        """Show preview of proposal data"""
        data = proposal.data.get('payload', {})
        from html import escape
        
        program_name = escape(data.get('program_name', 'N/A'))
        bot_username = escape(data.get('bot_username', 'N/A'))
        commission = data.get('commission', 0)
        duration = data.get('duration', 9999)
        average_income = data.get('average_income', 0)
        referral_link = data.get('referral_link', '')
        
        # Calculate ROI
        roi_score = round((float(commission) / 100) * float(average_income), 1) if commission and average_income else 0.0
        
        translations = data.get('translations', {})
        
        preview_msg = (
            f"✅ <b>Updated Preview</b>\n\n"
            f"👤 <b>Name:</b> {program_name}\n"
            f"🔗 <b>Username:</b> {bot_username}\n\n"
            f"<b>📊 Фінансові дані:</b>\n"
            f"🔗 <b>Link:</b> {escape(referral_link[:50]) if referral_link else '❌ Не вказано'}...\n"
            f"💰 <b>Commission:</b> {commission}%\n"
            f"⏳ <b>Duration:</b> {duration} days\n"
            f"📊 <b>Avg Income:</b> {average_income}\n"
            f"⭐ <b>ROI Score:</b> {roi_score}\n\n"
            f"📝 <b>Translations:</b>\n\n"
        )
        
        lang_flags = {
            'uk': '🇺🇦',
            'en': '🇬🇧',
            'ru': '🇷🇺',
            'de': '🇩🇪',
            'es': '🇪🇸'
        }
        
        for lang, flag in lang_flags.items():
            trans = translations.get(lang, {})
            title = escape(trans.get('title', 'N/A'))
            desc = escape(trans.get('description', 'N/A')[:80])
            preview_msg += f"{flag} <b>{lang.upper()}:</b> {title}\n{desc}...\n\n"
        
        # Get list of available bots for selection
        available_bots = self.db.query(Bot).filter(
            Bot.platform_type == "telegram",
            Bot.is_active == True
        ).all()
        
        # Filter out admin helper bots
        main_bots = [b for b in available_bots if not (b.config and b.config.get('role') == 'admin_helper')]
        
        # Create buttons with bot selection
        buttons = []
        
        if len(main_bots) == 1:
            # Only one bot - skip selection
            target_bot = main_bots[0]
            buttons = [
                [{"text": "✏️ Edit", "callback_data": f"edit_partner:{proposal.id}"}],
                [
                    {"text": f"✅ Add to {target_bot.name}", "callback_data": f"approve_partner:{proposal.id}:{target_bot.id}"},
                    {"text": "❌ Cancel", "callback_data": f"cancel_partner:{proposal.id}"}
                ]
            ]
        else:
            # Multiple bots - show selection
            buttons.append([{"text": "✏️ Edit", "callback_data": f"edit_partner:{proposal.id}"}])
            
            for bot in main_bots:
                bot_name = bot.name[:25]  # Truncate long names
                buttons.append([
                    {"text": f"➕ Add to {bot_name}", "callback_data": f"approve_partner:{proposal.id}:{bot.id}"}
                ])
            
            buttons.append([{"text": "❌ Cancel", "callback_data": f"cancel_partner:{proposal.id}"}])
        
        await self.adapter.send_message(
            self.bot_id,
            user.external_id,
            preview_msg,
            reply_markup={"inline_keyboard": buttons},
            parse_mode="HTML"
        )
