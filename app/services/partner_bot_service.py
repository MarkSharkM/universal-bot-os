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
Твоя мета: витягти ВСІ дані зі скріншотів та створити маркетинговий текст.

### ІНСТРУКЦІЇ:

1. ВІЗУАЛЬНИЙ АНАЛІЗ - Витягни ВСЕ що бачиш:
   - Program Name: Головна назва бота або сервісу
   - Bot Username: Юзернейм з '@' (наприклад, @EVAAIphoto_bot)
   - Referral Link: Повна лінка якщо видно (наприклад, t.me/bot?start=xxx)
   - Commission: Відсоток комісії (наприклад, 30 якщо бачиш "30%")
   - Duration: Тривалість в ДНЯХ (6 місяців = 180, безстроково = 9999)
   - Average Income: Середній дохід на користувача (число, наприклад 0.1)
   - Icon/Emoji: Емодзі бота якщо є

2. ГЕНЕРАЦІЯ ТА ПЕРЕКЛАД КОНТЕНТУ:
   Створи структурований об'єкт для 5 мов: uk, en, ru, de, es.
   
   ВАЖЛИВО: Обов'язково додавай емодзі в описи!
   
   Для КОЖНОЇ мови згенеруй:
   - title: Назва програми
   - description: Маркетинговий опис (1-2 речення) з емодзі 🎁💎🏦🎯💰⭐🚀
   - terms: Резюме умов (наприклад, "30% від рефералів 6 місяців")

3. СУВОРИЙ ФОРМАТ ВИВОДУ:
   - Поверни ТІЛЬКИ валідний JSON (без ```json блоків)
   - Не додавай розмовний текст

### JSON SCHEMA:

{
  "program_name": "EVA AI | Kling v2.6",
  "bot_username": "@EVAAIphoto_bot",
  "referral_link": "https://t.me/EVAAIphoto_bot?start=_tgr_WLMqwSg2OTky",
  "commission": 30,
  "duration": 180,
  "average_income": 0.1,
  "translations": {
    "uk": {
      "title": "EVA AI",
      "description": "📸 Оживіть ваші фото за допомогою EVA AI! 🎬",
      "terms": "30% від рефералів протягом 6 місяців"
    },
    "en": {...},
    "ru": {...},
    "de": {...},
    "es": {...}
  }
}

ВАЖЛИВО:
- commission це ЧИСЛО без % (30, не "30%")
- duration в ДНЯХ (6 міс = 180, 1 рік = 365)
- Якщо щось не видно на скріні - постав 0 або пустий рядок
- Завжди включай емодзі в description!
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

    async def process_photo(self, user: User, photo_data: Dict[str, Any], media_group_id: str = None):
        """
        Process received photo with media_group support:
        1. If media_group_id exists - store photo and wait for group
        2. Otherwise - process immediately
        3. After timeout - process all photos in group together
        """
        file_id = photo_data.get('file_id')
        if not file_id:
            await self.adapter.send_message(self.bot_id, user.external_id, "❌ Помилка: Немає file_id.")
            return

        # Handle media group (album)
        if media_group_id:
            await self._handle_media_group(user, photo_data, media_group_id)
            return
        
        # Single photo - process immediately
        await self._process_single_or_grouped_photos(user, [photo_data])
    
    async def _handle_media_group(self, user: User, photo_data: Dict[str, Any], media_group_id: str):
        """
        Handle photos from media group (album).
        Shows button for user to click when all photos uploaded.
        """
        from app.core.redis import cache
        import json
        
        if not cache.is_connected:
            await self._process_single_or_grouped_photos(user, [photo_data])
            return
        
        # Keys for this media group
        group_key = f"media_group:{self.bot_id}:{user.id}:{media_group_id}"
        lock_key = f"media_group_lock:{self.bot_id}:{user.id}:{media_group_id}"
        
        # Check if already processing
        if cache.get(lock_key):
            return
        
        # Get existing photos
        existing_data = cache.get(group_key)
        if existing_data:
            photos = existing_data if isinstance(existing_data, list) else json.loads(existing_data)
        else:
            photos = []
        
        # Add new photo
        photos.append(photo_data)
        
        # Save to Redis with 5 minute TTL
        cache.set(group_key, photos, ttl=300)
        
        # Store mapping for callback (short_id -> full keys)
        short_id = media_group_id[-8:]
        mapping_key = f"mg_map:{short_id}"
        cache.set(mapping_key, {
            "group_key": group_key,
            "lock_key": lock_key,
            "user_id": str(user.id)
        }, ttl=300)
        
        # Show button with current count
        keyboard = {
            "inline_keyboard": [
                [{"text": f"🔍 Аналізувати {len(photos)} фото", "callback_data": f"analyze_mg:{short_id}"}]
            ]
        }
        
        await self.adapter.send_message(
            self.bot_id,
            user.external_id,
            f"📸 <b>Отримано {len(photos)} фото</b>\n\nНатисни кнопку коли завантажиш усі:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        logger.info(f"Media group {media_group_id}: Received photo #{len(photos)}")
    
    async def handle_analyze_media_group(self, user: User, short_id: str):
        """Handle 'Analyze photos' button click"""
        from app.core.redis import cache
        import json
        
        mapping_key = f"mg_map:{short_id}"
        mapping = cache.get(mapping_key)
        
        if not mapping:
            await self.adapter.send_message(
                self.bot_id, user.external_id,
                "❌ Фото не знайдено. Надішліть знову."
            )
            return
        
        group_key = mapping.get("group_key")
        lock_key = mapping.get("lock_key")
        
        # Prevent double processing
        if cache.get(lock_key):
            await self.adapter.send_message(
                self.bot_id, user.external_id,
                "⏳ Вже аналізую..."
            )
            return
        
        # Get photos
        photos_data = cache.get(group_key)
        if not photos_data:
            await self.adapter.send_message(
                self.bot_id, user.external_id,
                "❌ Фото не знайдено. Надішліть знову."
            )
            return
        
        photos = photos_data if isinstance(photos_data, list) else json.loads(photos_data)
        
        # Lock and cleanup
        cache.set(lock_key, "1", ttl=120)
        cache.delete(group_key)
        cache.delete(mapping_key)
        
        await self.adapter.send_message(
            self.bot_id, user.external_id,
            f"⏳ <b>Аналізую {len(photos)} фото...</b>",
            parse_mode="HTML"
        )
        
        logger.info(f"Analyzing {len(photos)} photos for user {user.id}")
        await self._process_single_or_grouped_photos(user, photos)
    
    async def _process_single_or_grouped_photos(self, user: User, photos: list):
        """
        Process one or more photos:
        1. Download all photos
        2. Send all to AI for analysis
        3. Show single preview
        """
        try:
            # 1. Download all photos
            image_urls = []
            for photo_data in photos:
                file_id = photo_data.get('file_id')
                if file_id:
                    image_url = await self.adapter.get_file_path(self.bot_id, file_id)
                    if image_url:
                        image_urls.append(image_url)
            
            if not image_urls:
                await self.adapter.send_message(self.bot_id, user.external_id, "❌ Не вдалося завантажити фото.")
                return

            # 2. AI Analysis with all images
            from app.services.translation_service import TranslationService
            ai_service = AIService(self.db, self.bot_id, TranslationService(self.db, self.bot_id))
            
            full_prompt = f"{PARTNER_ANALYSIS_PROMPT}\n\nAnalyze these {len(image_urls)} image(s):"
            
            # For multiple images, send first image as main, others in context
            response_text = await ai_service.generate_response(
                user.id,
                full_prompt,
                user_lang="uk",
                image_url=image_urls[0] if len(image_urls) == 1 else image_urls  # Pass list if multiple
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
                    "photo_count": len(photos),
                    "file_unique_ids": [p.get('file_unique_id') for p in photos]
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
                f"<b>📊 Фінансові дані:</b>\n"
                f"🔗 <b>Link:</b> {'✅ ' + escape(referral_link[:40]) + '...' if referral_link else '❌ Не вказано'}\n"
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
                # Store target_bot_id in proposal for later use
                data['_target_bot_id'] = str(target_bot.id)
                proposal.data['payload'] = data
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(proposal, 'data')
                self.db.commit()
                
                buttons = [
                    [{"text": "✏️ Edit", "callback_data": f"edit_partner:{str(proposal.id)[:8]}"}],
                    [
                        {"text": f"✅ Add to {target_bot.name}", "callback_data": f"approve_p:{str(proposal.id)[:8]}"},
                        {"text": "❌ Cancel", "callback_data": f"cancel_p:{str(proposal.id)[:8]}"}
                    ]
                ]
            else:
                # Multiple bots - show selection buttons with bot index
                buttons.append([{"text": "✏️ Edit", "callback_data": f"edit_partner:{str(proposal.id)[:8]}"}])
                
                # Store bot list in proposal for lookup
                bot_mapping = {str(i): str(bot.id) for i, bot in enumerate(main_bots)}
                data['_bot_mapping'] = bot_mapping
                proposal.data['payload'] = data
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(proposal, 'data')
                self.db.commit()
                
                for i, bot in enumerate(main_bots):
                    bot_name = bot.name[:20]  # Truncate long names
                    buttons.append([
                        {"text": f"➕ Add to {bot_name}", "callback_data": f"approve_p:{str(proposal.id)[:8]}:{i}"}
                    ])
                
                buttons.append([{"text": "❌ Cancel", "callback_data": f"cancel_p:{str(proposal.id)[:8]}"}])
            
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

    async def handle_approval(self, user: User, proposal_short_id: str, bot_index: str = None):
        """
        Handle approval callback - adds partner to TARGET bot.
        
        Args:
            user: User who approved
            proposal_short_id: Short proposal ID (first 8 chars of UUID)
            bot_index: Bot index from callback_data (for multi-bot selection)
        """
        # Find proposal by short ID (match first 8 chars)
        proposals = self.db.query(BusinessData).filter(
            BusinessData.bot_id == self.bot_id,
            BusinessData.data_type == 'partner_proposal'
        ).all()
        
        proposal = None
        for p in proposals:
            if str(p.id).startswith(proposal_short_id):
                proposal = p
                break
        
        if not proposal:
            await self.adapter.send_message(self.bot_id, user.external_id, "❌ Proposal not found or expired.")
            return
            
        data = proposal.data.get('payload')
        if not data:
            await self.adapter.send_message(self.bot_id, user.external_id, "❌ Invalid proposal data.")
            return

        # Get target_bot_id from proposal data or bot_index
        if bot_index is not None:
            # Multi-bot selection - lookup bot_id from mapping
            bot_mapping = data.get('_bot_mapping', {})
            target_bot_id_str = bot_mapping.get(bot_index)
            if not target_bot_id_str:
                await self.adapter.send_message(self.bot_id, user.external_id, f"❌ Invalid bot selection.")
                return
        else:
            # Single bot - get from stored target_bot_id
            target_bot_id_str = data.get('_target_bot_id')
            if not target_bot_id_str:
                await self.adapter.send_message(self.bot_id, user.external_id, "❌ No target bot specified.")
                return
        
        # Convert to UUID
        try:
            from uuid import UUID as UUID_type
            target_bot_uuid = UUID_type(target_bot_id_str)
        except ValueError:
            await self.adapter.send_message(self.bot_id, user.external_id, f"❌ Invalid target bot ID.")
            return

        # Verify target bot exists
        target_bot = self.db.query(Bot).filter(Bot.id == target_bot_uuid).first()
        if not target_bot:
            await self.adapter.send_message(self.bot_id, user.external_id, f"❌ Target bot not found.")
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

    async def handle_edit(self, user: User, proposal_short_id: str):
        """Handle edit callback - show editable fields"""
        # Find proposal by short ID
        proposals = self.db.query(BusinessData).filter(
            BusinessData.bot_id == self.bot_id,
            BusinessData.data_type == 'partner_proposal'
        ).all()
        
        proposal = None
        for p in proposals:
            if str(p.id).startswith(proposal_short_id):
                proposal = p
                break
        
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
            f"<b>📋 Основні дані (з AI):</b>\n"
            f"• Name: {escape(data.get('program_name', 'N/A'))}\n"
            f"• Username: {escape(data.get('bot_username', 'N/A'))}\n\n"
            f"<b>💰 Фінансові дані (ОБОВ'ЯЗКОВО заповни):</b>\n"
            f"• Commission: {escape(str(data.get('commission', '❌ НЕ ВКАЗАНО')))}\n"
            f"• Duration: {escape(str(data.get('duration', '❌ НЕ ВКАЗАНО')))} days\n"
            f"• Avg Income: {escape(str(data.get('average_income', '❌ НЕ ВКАЗАНО')))}\n"
            f"• Referral Link: {'✅ Вказано' if data.get('referral_link') else '❌ НЕ ВКАЗАНО'}\n\n"
            f"<b>⚡ Швидке редагування:</b>\n"
            f"Натисни кнопку нижче або відправ текст:\n\n"
            f"<b>📝 Приклади:</b>\n"
            f"<code>commission: 78.5</code>\n"
            f"<code>average_income: 15.5</code>\n"
            f"<code>duration: 90</code>\n"
            f"<code>referral_link: https://t.me/bot?start=ref123</code>"
        )
        
        # Create quick-edit buttons for common fields
        buttons = [
            [
                {"text": "💰 Commission", "callback_data": f"editfield:commission:{str(proposal.id)[:8]}"},
                {"text": "⏳ Duration", "callback_data": f"editfield:duration:{str(proposal.id)[:8]}"}
            ],
            [
                {"text": "📊 Avg Income", "callback_data": f"editfield:avgincome:{str(proposal.id)[:8]}"},
                {"text": "🔗 Ref Link", "callback_data": f"editfield:reflink:{str(proposal.id)[:8]}"}
            ],
            [{"text": "🔙 Back to Preview", "callback_data": f"preview_partner:{str(proposal.id)[:8]}"}],
            [
                {"text": "✅ Save & Approve", "callback_data": f"approve_p:{str(proposal.id)[:8]}"},
                {"text": "❌ Cancel", "callback_data": f"cancel_p:{str(proposal.id)[:8]}"}
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
        # Simple query without JSONB operators (more compatible)
        proposals = self.db.query(BusinessData).filter(
            BusinessData.bot_id == self.bot_id,
            BusinessData.data_type == 'partner_proposal'
        ).order_by(BusinessData.created_at.desc()).all()
        
        # Filter in Python for status and user_id
        proposal = None
        for p in proposals:
            if p.data.get('status') == 'pending' and p.data.get('user_id') == str(user.id):
                proposal = p
                break
        
        if not proposal:
            await self.adapter.send_message(
                self.bot_id, 
                user.external_id, 
                "❌ Не знайдено активного proposal для редагування.\nСпочатку надішліть скріншот."
            )
            return
        
        # Auto-detect URL and treat as referral_link
        text_lower = text.strip().lower()
        if text_lower.startswith('http://') or text_lower.startswith('https://') or text_lower.startswith('t.me/'):
            field = 'referral_link'
            value = text.strip()
            if value.startswith('t.me/'):
                value = 'https://' + value
        elif ':' not in text:
            await self.adapter.send_message(
                self.bot_id,
                user.external_id,
                "❌ Невірний формат. Використовуйте:\n<code>field: value</code>\n\nАбо просто вставте URL для referral_link.",
                parse_mode="HTML"
            )
            return
        else:
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
            f"🔗 <b>Link:</b> {'✅ ' + escape(referral_link[:40]) + '...' if referral_link else '❌ Не вказано'}\n"
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
            # Store target_bot_id in proposal
            data['_target_bot_id'] = str(target_bot.id)
            proposal.data['payload'] = data
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(proposal, 'data')
            self.db.commit()
            
            buttons = [
                [{"text": "✏️ Edit", "callback_data": f"edit_partner:{str(proposal.id)[:8]}"}],
                [
                    {"text": f"✅ Add to {target_bot.name}", "callback_data": f"approve_p:{str(proposal.id)[:8]}"},
                    {"text": "❌ Cancel", "callback_data": f"cancel_p:{str(proposal.id)[:8]}"}
                ]
            ]
        else:
            # Multiple bots - show selection with bot index
            buttons.append([{"text": "✏️ Edit", "callback_data": f"edit_partner:{str(proposal.id)[:8]}"}])
            
            # Store bot mapping
            bot_mapping = {str(i): str(bot.id) for i, bot in enumerate(main_bots)}
            data['_bot_mapping'] = bot_mapping
            proposal.data['payload'] = data
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(proposal, 'data')
            self.db.commit()
            
            for i, bot in enumerate(main_bots):
                bot_name = bot.name[:20]  # Truncate long names
                buttons.append([
                    {"text": f"➕ Add to {bot_name}", "callback_data": f"approve_p:{str(proposal.id)[:8]}:{i}"}
                ])
            
            buttons.append([{"text": "❌ Cancel", "callback_data": f"cancel_p:{str(proposal.id)[:8]}"}])
        
        await self.adapter.send_message(
            self.bot_id,
            user.external_id,
            preview_msg,
            reply_markup={"inline_keyboard": buttons},
            parse_mode="HTML"
        )
