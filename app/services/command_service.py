"""
Command Service - Multi-tenant command router
Routes bot commands to appropriate handlers (replaces Switch_Commands logic)
"""
from typing import Dict, Any, Optional, Callable, List, Tuple
from sqlalchemy.orm import Session
from uuid import UUID
import re
import logging
from urllib.parse import quote

from app.services.user_service import UserService
from app.services.translation_service import TranslationService
from app.services.partner_service import PartnerService
from app.services.referral_service import ReferralService
from app.services.earnings_service import EarningsService
from app.models.bot import Bot

logger = logging.getLogger(__name__)


class CommandService:
    """
    Multi-tenant command service.
    Routes commands to handlers, replaces n8n Switch_Commands logic.
    """
    
    # Command patterns (regex)
    COMMAND_PATTERNS = {
        'wallet': r'^/(?:start\s+)?wallet\b',
        'top': r'^/(?:start\s+)?top\b',
        'partners': r'^/(?:start\s+)?partners\b',
        'share': r'^/(?:start\s+)?share\b',
        'earnings': r'^/(?:start\s+)?earning(?:s)?\b',  # Support both /earning and /earnings
        'info': r'^/(?:start\s+)?info\b',
        'start': r'^/start\b',
    }
    
    def __init__(
        self,
        db: Session,
        bot_id: UUID,
        user_service: UserService,
        translation_service: TranslationService,
        partner_service: PartnerService,
        referral_service: ReferralService,
        earnings_service: EarningsService
    ):
        self.db = db
        self.bot_id = bot_id
        self.user_service = user_service
        self.translation_service = translation_service
        self.partner_service = partner_service
        self.referral_service = referral_service
        self.earnings_service = earnings_service
        self._bot_config = None  # Lazy load bot.config
    
    def parse_command(self, text: Optional[str]) -> Optional[str]:
        """
        Parse command from message text.
        
        Args:
            text: Message text (e.g., '/start', '/wallet', '/top')
        
        Returns:
            Command name or None
        """
        if not text:
            return None
        
        text = text.strip()
        
        # Get command patterns (from bot.config or default)
        patterns = self._get_command_patterns()
        
        # Check each pattern
        for cmd, pattern in patterns.items():
            # Skip disabled commands
            if not self._is_command_enabled(cmd):
                continue
            if re.match(pattern, text, re.IGNORECASE):
                return cmd
        
        return None
    
    def _get_command_patterns(self) -> Dict[str, str]:
        """
        Get command patterns from bot.config or use defaults.
        
        Returns:
            Dictionary of command patterns
        """
        config = self._get_bot_config()
        commands_config = config.get('commands', {})
        
        # If custom patterns are defined, use them
        custom_patterns = commands_config.get('patterns', {})
        if custom_patterns:
            # Merge with defaults (custom overrides defaults)
            patterns = self.COMMAND_PATTERNS.copy()
            patterns.update(custom_patterns)
            return patterns
        
        # Default: use hardcoded patterns
        return self.COMMAND_PATTERNS
    
    def extract_start_parameter(self, text: Optional[str]) -> Optional[str]:
        """
        Extract parameter from /start command.
        
        Args:
            text: Message text (e.g., '/start _tgr_123456')
        
        Returns:
            Start parameter or None
        """
        if not text:
            return None
        
        match = re.match(r'^/start\s+(.+)$', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _get_bot_config(self) -> Dict[str, Any]:
        """
        Get bot configuration (lazy load).
        
        Returns:
            Bot config dictionary
        """
        if self._bot_config is None:
            bot = self.db.query(Bot).filter(Bot.id == self.bot_id).first()
            if bot:
                self._bot_config = bot.config or {}
            else:
                self._bot_config = {}
        return self._bot_config
    
    def _get_bot_username(self) -> Optional[str]:
        """
        Get bot username from bot.config.username or bot.name.
        
        Returns:
            Bot username (without @) or None if not found
        """
        config = self._get_bot_config()
        username = config.get('username')
        if username:
            return username.replace('@', '').strip()
        
        # Fallback to bot.name
        bot = self.db.query(Bot).filter(Bot.id == self.bot_id).first()
        if bot and bot.name:
            # Extract username from name (remove spaces, keep only alphanumeric and underscores)
            import re
            return re.sub(r'[^a-zA-Z0-9_]', '', bot.name).strip().lower()
        
        return None
    
    def _get_buy_top_price(self, lang: str) -> int:
        """
        Get buy TOP price from bot.config or translations.
        
        Args:
            lang: User's language code
            
        Returns:
            Buy TOP price in stars
        """
        config = self._get_bot_config()
        earnings_config = config.get('earnings', {})
        
        # Try bot.config first
        buy_top_price = earnings_config.get('buy_top_price')
        if buy_top_price is not None:
            try:
                return int(buy_top_price)
            except:
                pass
        
        # Fallback to translation
        buy_top_price_str = self.translation_service.get_translation('buy_top_price', lang) or '1'
        try:
            return int(buy_top_price_str)
        except:
            return 1
    
    def _get_share_content(self, user: Any, lang: str) -> Tuple[str, str]:
        """
        Get share link and share text based on TGR status.
        Priority: TGR Link > Standard Referral Link
        
        Args:
            user: User object
            lang: Language code
            
        Returns:
            Tuple of (link_to_share, text_for_share)
        """
        # 1. Check for TGR Link (Saved by user)
        tgr_link = user.custom_data.get('tgr_link') if user.custom_data else None

        # Get bot name for share text (dynamic, no hardcode)
        bot_name = self._get_bot_config().get('name') or self._get_bot_config().get('username') or 'Bot'
        
        if tgr_link:
            # Use share_text_pro - unified text for all share types (TGR and standard)
            share_text = self.translation_service.get_translation('share_text_pro', lang, {'bot_name': bot_name})
            if not share_text or share_text == 'share_text_pro':
                 share_text = f"🚀 Join {bot_name} — earn Stars for your activity!"
            # Return TGR link and unified text
            return tgr_link, share_text

        # 2. Fallback: Standard Referral Link
        referral_link = self.referral_service.generate_referral_link(user.id)
        
        # Use share_text_pro for standard links too (unified message)
        share_text = self.translation_service.get_translation('share_text_pro', lang, {'bot_name': bot_name})
        
        # Fallback to old 'share_referral' logic if share_text_pro missing
        if not share_text or share_text == 'share_text_pro':
             bot_username = self._get_bot_username() or ''
             share_text = self.translation_service.get_translation('share_referral', lang, {'bot_username': bot_username})
             # Remove link placeholder AND "Ось твоє реферальне посилання:" text
             share_text = share_text.replace('[[referralLink]]', '').replace('{{referralLink}}', '')
             share_text = share_text.replace('Ось твоє реферальне посилання:', '').replace('Here is your referral link:', '').replace('Вот твоя реферальная ссылка:', '').replace('Hier ist dein Empfehlungslink:', '').replace('Aquí tienes tu enlace de referido:', '')
             share_text = share_text.strip()

        return referral_link, share_text
    
    def _get_buttons_for_command(self, command: str, lang: str, **kwargs) -> Optional[List[List[Dict[str, Any]]]]:
        """
        Get buttons for command from bot.config or return None to use defaults.
        
        Args:
            command: Command name (wallet, top, share, etc.)
            lang: User's language code
            **kwargs: Additional context (referral_link, etc.)
        
        Returns:
            List of button rows, or None to use default buttons
        """
        config = self._get_bot_config()
        ui_config = config.get('ui', {})
        buttons_config = ui_config.get('buttons', {})
        command_buttons = buttons_config.get(command, [])
        
        if not command_buttons:
            return None  # Use default buttons
        
        # Build buttons from config
        buttons = []
        for row in command_buttons:
            if not row.get('enabled', True):
                continue  # Skip disabled buttons
            
            button_row = []
            for button_config in row.get('buttons', []):
                if not button_config.get('enabled', True):
                    continue
                
                # Get button text (from translation key or direct text)
                text_key = button_config.get('text_key')
                if text_key:
                    text = self.translation_service.get_translation(text_key, lang)
                    if not text or text == text_key:
                        text = button_config.get('text', text_key)  # Fallback to direct text
                else:
                    text = button_config.get('text', 'Button')
                
                # Build button based on type
                button = {'text': text}
                
                # URL button
                if button_config.get('url'):
                    url = button_config['url']
                    # Replace placeholders
                    for key, value in kwargs.items():
                        url = url.replace(f'{{{key}}}', str(value))
                    button['url'] = url
                
                # Callback button
                elif button_config.get('callback_data'):
                    button['callback_data'] = button_config['callback_data']
                
                # Action button (special handling)
                elif button_config.get('action'):
                    action = button_config['action']
                    if action == 'share':
                        # Generate share URL
                        referral_link = kwargs.get('referral_link', '')
                        share_text = kwargs.get('share_text', '')
                        from urllib.parse import quote
                        button['url'] = f"https://t.me/share/url?url={quote(referral_link, safe='')}&text={quote(share_text, safe='')}"
                    elif action == 'wallet':
                        button['url'] = 'tg://resolve?domain=wallet'
                
                button_row.append(button)
            
            if button_row:
                buttons.append(button_row)
        
        return buttons if buttons else None
    
    def _is_command_enabled(self, command: str) -> bool:
        """
        Check if command is enabled for this bot.
        
        Args:
            command: Command name
            
        Returns:
            True if command is enabled, False otherwise
        """
        config = self._get_bot_config()
        commands_config = config.get('commands', {})
        
        # Check disabled list first
        disabled = commands_config.get('disabled', [])
        if command in disabled:
            return False
        
        # Check enabled list (if exists, only these are allowed)
        enabled = commands_config.get('enabled', [])
        if enabled:  # If enabled list exists, only these commands are allowed
            return command in enabled
        
        # Default: all commands enabled
        return True
    
    async def handle_command(
        self,
        command: str,
        user_id: UUID,
        user_lang: Optional[str] = None,
        start_param: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Route command to appropriate handler.
        
        Args:
            command: Command name (wallet, top, partners, etc.)
            user_id: User UUID
            user_lang: User's language code
            start_param: Parameter from /start command
        
        Returns:
            Response dictionary with message, buttons, etc.
        """
        logger.info(f"handle_command: command={command}, user_id={user_id}, lang={user_lang}, start_param={start_param}")
        
        # Check if command is enabled for this bot
        if not self._is_command_enabled(command):
            logger.warning(f"Command {command} is disabled for bot {self.bot_id}")
            disabled_msg = self.translation_service.get_translation('command_disabled', user_lang or 'en')
            if not disabled_msg or disabled_msg == 'command_disabled':
                disabled_msg = "Ця команда недоступна для цього бота." if (user_lang or 'en') == 'uk' else "This command is not available for this bot."
            return {'error': disabled_msg}
        
        handlers = {
            'wallet': self._handle_wallet,
            'top': self._handle_top,
            'partners': self._handle_partners,
            'share': self._handle_share,
            'earnings': self._handle_earnings,
            'info': self._handle_info,
            'start': self._handle_start,
        }
        
        handler = handlers.get(command)
        if not handler:
            logger.warning(f"Unknown command: {command}")
            return {'error': f'Unknown command: {command}'}
        
        try:
            # Handle async handlers (top, partners)
            if command in ('top', 'partners'):
                response = await handler(user_id, user_lang, start_param)
            else:
                response = handler(user_id, user_lang, start_param)
            logger.info(f"handle_command: {command} completed successfully, response has message: {bool(response.get('message'))}")
            return response
        except Exception as e:
            logger.error(f"Error handling command {command}: {e}", exc_info=True)
            return {'error': f'Error processing command: {str(e)}'}
    
    def _handle_wallet(
        self,
        user_id: UUID,
        user_lang: Optional[str],
        start_param: Optional[str]
    ) -> Dict[str, Any]:
        """Handle /wallet command"""
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        lang = user_lang or user.language_code or 'en'
        lang = self.translation_service.detect_language(lang)
        
        wallet = self.user_service.get_wallet(user_id)
        
        if wallet:
            # Has wallet
            earned = float(user.balance) if user.balance else 0.0
            message = self.translation_service.get_translation(
                'wallet_info_saved',
                lang,
                {'wallet': wallet}
            )
            message += f"\n{self.translation_service.get_translation('wallet_info_earnings', lang, {'amount': earned})}"
        else:
            # No wallet - show detailed instructions
            # Try wallet_help first (detailed), fallback to wallet_not_found (short), then wallet_info_empty
            message = self.translation_service.get_translation('wallet_help', lang)
            if not message or message == 'wallet_help':  # Translation not found
                message = self.translation_service.get_translation('wallet_not_found', lang)
                if not message or message == 'wallet_not_found':  # Still not found
                    message = self.translation_service.get_translation('wallet_info_empty', lang)
        
        buttons = [[{
            'text': self.translation_service.get_translation('btn_buy_stars', lang),
            'url': 'tg://resolve?domain=wallet'
        }]]
        
        return {
            'message': message,
            'buttons': buttons,
            'parse_mode': 'HTML'
        }
    
    async def _handle_top(
        self,
        user_id: UUID,
        user_lang: Optional[str],
        start_param: Optional[str]
    ) -> Dict[str, Any]:
        """Handle /top command"""
        logger.info(f"_handle_top: START user_id={user_id}, lang={user_lang}")
        
        try:
            logger.info(f"_handle_top: getting user")
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                logger.error(f"_handle_top: User {user_id} not found")
                raise ValueError(f"User {user_id} not found")
            
            lang = user_lang or user.language_code or 'en'
            lang = self.translation_service.detect_language(lang)
            logger.info(f"_handle_top: detected lang={lang}")
            
            # Check TOP unlock status
            logger.info(f"_handle_top: checking top unlock eligibility")
            can_unlock, invites_needed = self.referral_service.check_top_unlock_eligibility(user_id)
            logger.info(f"_handle_top: checking top status")
            top_status = self.user_service.get_top_status(user_id)
            logger.info(f"_handle_top: top_status={top_status}, can_unlock={can_unlock}, invites_needed={invites_needed}")
            
            # Get total_invited once (check_top_unlock_eligibility already called get_total_invited, but we need it for message)
            # Reuse from check_top_unlock_eligibility to avoid duplicate call
            total_invited = self.referral_service.get_total_invited(user_id)
        except Exception as e:
            logger.error(f"_handle_top: error checking top status: {e}", exc_info=True)
            raise
        
        if top_status == 'locked' and not can_unlock:
            # TOP is locked - use translations from database
            logger.info(f"_handle_top: TOP is locked, building locked message")
            try:
                referral_tag = self.referral_service.generate_referral_tag(user_id)
                logger.info(f"_handle_top: generated referral_tag")
                referral_link = self.referral_service.generate_referral_link(user_id)
                logger.info(f"_handle_top: generated referral_link")
                # total_invited already fetched above
                logger.info(f"_handle_top: total_invited={total_invited}")
            except Exception as e:
                logger.error(f"_handle_top: error in locked branch: {e}", exc_info=True)
                raise
            
            # Get buy_top_price from bot.config or translations
            buy_top_price = self._get_buy_top_price(lang)
            
            # Use translation key for locked message (with needed parameter)
            # Use top_locked_message for /top command (full message with share prompt)
            # earnings_step1_locked is shorter and used in /earnings
            # Use translation key for locked message (with needed parameter)
            # Use top_locked_message for /top command (full message with share prompt)
            # earnings_step1_locked is shorter and used in /earnings
            message = self.translation_service.get_translation(
                'top_locked_message',
                lang,
                {
                    'needed': invites_needed,
                    'price': buy_top_price
                }
            )
            
            # Fallback to earnings_step1_locked if top_locked_message not found
            if not message or message == 'top_locked_message':
                message = self.translation_service.get_translation(
                    'earnings_step1_locked',
                    lang,
                    {
                        'needed': invites_needed,
                        'price': buy_top_price
                    }
                )
            
            # Get share content (TGR/Pro or Standard/Starter)
            referral_link, share_text = self._get_share_content(user, lang)
            
            # Ensure no duplicates in share text (just text, no link)
            share_text = share_text.replace(referral_link, '').strip()
            
            # Get buttons from bot.config or use defaults
            buttons = self._get_buttons_for_command('top', lang, referral_link=referral_link, share_text=share_text, buy_top_price=buy_top_price)
            if not buttons:
                # Default buttons
                buttons = [[
                    {
                        'text': self.translation_service.get_translation('share_button', lang),
                        'url': f"https://t.me/share/url?url={quote(referral_link, safe='')}&text={quote(share_text, safe='')}"
                    },
                    {
                        'text': self.translation_service.get_translation('unlock_top_paid', lang, {'buy_top_price': buy_top_price}),
                        'callback_data': '/buy_top'
                    }
                ]]
            
            return {
                'message': message,
                'buttons': buttons,
                'parse_mode': 'HTML',
                'top_status': 'locked'
            }
        
        # TOP is open - show partners
        logger.info(f"_handle_top: TOP is open, getting partners")
        try:
            logger.info(f"_handle_top: calling get_top_partners")
            partners = await self.partner_service.get_top_partners(limit=20, user_lang=lang)
            logger.info(f"_handle_top: found {len(partners) if partners else 0} top partners")
        except Exception as e:
            logger.error(f"_handle_top: error getting top partners: {e}", exc_info=True)
            raise
        
        try:
            logger.info(f"_handle_top: generating referral_tag")
            referral_tag = self.referral_service.generate_referral_tag(user_id)
            
            logger.info(f"_handle_top: formatting top message")
            message = self.partner_service.format_top_message(
                partners,
                referral_tag,
                lang,
                translation_service=self.translation_service
            )
            logger.info(f"_handle_top: formatted message, length={len(message) if message else 0}")
        except Exception as e:
            logger.error(f"_handle_top: error formatting message: {e}", exc_info=True)
            raise
        
        if not message:
            # Fallback if translation not found
            error_msg = self.translation_service.get_translation('errorEmptyTopByLang', lang)
            if not error_msg or error_msg == 'errorEmptyTopByLang':
                error_msg_map = {
                    'uk': 'Поки що немає TOP-партнерів.',
                    'en': 'No TOP partners available yet.',
                    'ru': 'Пока нет TOP-партнёров.',
                    'de': 'Noch keine TOP-Partner verfügbar.',
                    'es': 'Aún no hay socios TOP disponibles.',
                }
                error_msg = error_msg_map.get(lang, error_msg_map['en'])
            message = error_msg
        
        # Get share content (TGR/Pro or Standard/Starter)
        referral_link, share_text = self._get_share_content(user, lang)
        
        # Ensure no duplicates in share text
        if referral_link in share_text:
            share_text = share_text.replace(referral_link, '').strip()
        # Get buttons from bot.config or use defaults
        buttons = self._get_buttons_for_command('top', lang, referral_link=referral_link, share_text=share_text)
        if not buttons:
            # Default buttons
            buttons = [[{
                'text': self.translation_service.get_translation('share_button', lang),
                'url': f"https://t.me/share/url?url={quote(referral_link, safe='')}&text={quote(share_text, safe='')}"
            }]]
        
        return {
            'message': message,
            'buttons': buttons,
            'parse_mode': 'HTML',
            'top_status': 'open'
        }
    
    async def _handle_partners(
        self,
        user_id: UUID,
        user_lang: Optional[str],
        start_param: Optional[str]
    ) -> Dict[str, Any]:
        """Handle /partners command"""
        logger.info(f"_handle_partners: user_id={user_id}, lang={user_lang}")
        
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found in _handle_partners")
            raise ValueError(f"User {user_id} not found")
        
        lang = user_lang or user.language_code or 'en'
        lang = self.translation_service.detect_language(lang)
        logger.info(f"_handle_partners: detected lang={lang}")
        
        try:
            partners = await self.partner_service.get_partners(limit=50, user_lang=lang)
            logger.info(f"_handle_partners: found {len(partners) if partners else 0} partners")
        except Exception as e:
            logger.error(f"_handle_partners: error getting partners: {e}", exc_info=True)
            raise
        
        # Build message
        intro = self.translation_service.get_translation('partners_intro', lang)
        if not intro or intro == 'partners_intro':  # Fallback if translation not found
            intro_map = {
                'uk': "🤖 <b>Перевірені Telegram-боти, які дають зірки за активність</b>\nОбери будь-який — запускай та прокачуйся! 💪",
                'en': "🤖 <b>Verified Telegram bots that give you Stars for actions</b>\nPick any — launch and level up! 💪",
                'ru': "🤖 <b>Проверенные Telegram-боты, которые дают звезды за активность</b>\nВыбери любой — запускай и прокачивайся! 💪",
                'de': "🤖 <b>Verifizierte Telegram-Bots, die dir Sterne für Aktionen geben</b>\nWähle einen aus — starte und steigere dich! 💪",
                'es': "🤖 <b>Bots de Telegram verificados que te dan Estrellas por acciones</b>\nElige cualquiera — ¡lanza y sube de nivel! 💪",
            }
            intro = intro_map.get(lang, intro_map['en'])
        
        if not partners:
            empty_msg = self.translation_service.get_translation('partners_empty', lang)
            if not empty_msg or empty_msg == 'partners_empty':
                empty_msg_map = {
                    'uk': 'Поки що немає доступних партнерів.',
                    'en': 'No partners available yet.',
                    'ru': 'Пока нет доступных партнёров.',
                    'de': 'Noch keine Partner verfügbar.',
                    'es': 'Aún no hay socios disponibles.',
                }
                empty_msg = empty_msg_map.get(lang, empty_msg_map['en'])
            message = f"{intro}\n\n{empty_msg}"
        else:
            partner_lines = []
            for i, partner in enumerate(partners, 1):
                launch_label = self.translation_service.get_translation('launch_label', lang)
                if not launch_label or launch_label == 'launch_label':  # Fallback if translation not found
                    launch_label_map = {
                        'uk': 'Запустити',
                        'en': 'Launch',
                        'ru': 'Запустить',
                    }
                    launch_label = launch_label_map.get(lang, 'Launch')
                # Use partner link as-is from database (no personalization)
                line = f"⭐ <b>{i}. {partner['bot_name']}</b>\n{partner['description']}\n🔗 <a href=\"{partner['referral_link']}\">{launch_label}</a>"
                partner_lines.append(line)
            
            message = f"{intro}\n\n" + "\n\n".join(partner_lines)
        
        # Get share content (TGR/Pro or Standard/Starter)
        referral_link, share_text = self._get_share_content(user, lang)
        
        if referral_link in share_text:
            share_text = share_text.replace(referral_link, '').strip()
        
        # Get buttons from bot.config or use defaults
        buttons = self._get_buttons_for_command('partners', lang, referral_link=referral_link, share_text=share_text)
        if not buttons:
            # Default buttons
            buttons = [
                [{'text': self.translation_service.get_translation('share_button', lang), 'url': f"https://t.me/share/url?url={quote(referral_link, safe='')}&text={quote(share_text, safe='')}"}],
                [{'text': self.translation_service.get_translation('partners_btn_top_partners', lang), 'callback_data': '/top'}],
                [{'text': self.translation_service.get_translation('partners_btn_earnings', lang), 'callback_data': '/earnings'}],
            ]
        
        return {
            'message': message,
            'buttons': buttons,
            'parse_mode': 'HTML'
        }
    
    def _handle_share(
        self,
        user_id: UUID,
        user_lang: Optional[str],
        start_param: Optional[str]
    ) -> Dict[str, Any]:
        """Handle /share command"""
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        lang = user_lang or user.language_code or 'en'
        lang = self.translation_service.detect_language(lang)
        
        # Get share content (TGR/Pro or Standard/Starter)
        referral_link, share_text = self._get_share_content(user, lang)
        
        # Message to user
        message = f"{share_text}\n{referral_link}"
        
        # Share button text (clean, no link)
        share_text_for_button = share_text.replace(referral_link, '').strip()
        
        # Get buttons from bot.config or use defaults
        buttons = self._get_buttons_for_command('share', lang, referral_link=referral_link, share_text=share_text_for_button)
        if not buttons:
            # Default buttons
            buttons = [[{
                'text': self.translation_service.get_translation('share_button', lang),
                'url': f"https://t.me/share/url?url={quote(referral_link, safe='')}&text={quote(share_text_for_button, safe='')}"
            }]]
        
        return {
            'message': message,
            'buttons': buttons,
            'parse_mode': 'HTML'
        }
    
    def _handle_earnings(
        self,
        user_id: UUID,
        user_lang: Optional[str],
        start_param: Optional[str]
    ) -> Dict[str, Any]:
        """Handle /earnings command"""
        logger.info(f"_handle_earnings: user_id={user_id}, lang={user_lang}")
        
        # Get user object (needed for _get_share_content)
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        try:
            logger.info(f"_handle_earnings: calling build_earnings_message")
            earnings_data = self.earnings_service.build_earnings_message(user_id, user_lang)
            logger.info(f"_handle_earnings: build_earnings_message completed, has_text={bool(earnings_data.get('text'))}")
        except Exception as e:
            logger.error(f"_handle_earnings: error in build_earnings_message: {e}", exc_info=True)
            raise
        
        # Get language from earnings_data (now included in response)
        lang = earnings_data.get('lang', user_lang or 'en')
        
        # Refresh user to get latest custom_data (e.g. tgr_link updated from Mini App)
        self.db.refresh(user)
        
        # Get share content (TGR/Pro or Standard/Starter)
        referral_link, share_text = self._get_share_content(user, lang)
        
        if referral_link in share_text:
            share_text = share_text.replace(referral_link, '').strip()
        
        # Get buttons from bot.config or use defaults
        buy_top_price = self._get_buy_top_price(lang)
        buttons = self._get_buttons_for_command('earnings', lang, referral_link=referral_link, share_text=share_text, buy_top_price=buy_top_price)
        if not buttons:
            # Default buttons
            buttons = [
                [{'text': self.translation_service.get_translation('share_button', lang), 'url': f"https://t.me/share/url?url={quote(referral_link, safe='')}&text={quote(share_text, safe='')}"}],
                [
                    {'text': self.translation_service.get_translation('earnings_btn_unlock_top', lang, {'price': buy_top_price, 'buy_top_price': buy_top_price}), 'callback_data': 'buy_top'},
                    {'text': self.translation_service.get_translation('earnings_btn_top_partners', lang), 'callback_data': '=/top'}
                ],
                [{'text': self.translation_service.get_translation('earnings_btn_activate_7', lang), 'callback_data': 'activate_7'}],
            ]
        
        return {
            'message': earnings_data['text'],
            'buttons': buttons,
            'parse_mode': 'HTML'
        }
    
    def _handle_info(
        self,
        user_id: UUID,
        user_lang: Optional[str],
        start_param: Optional[str]
    ) -> Dict[str, Any]:
        """Handle /info command"""
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        lang = user_lang or user.language_code or 'en'
        lang = self.translation_service.detect_language(lang)
        
        # Get bot username for translation variables
        bot_username = self._get_bot_username() or ''
        
        message = self.translation_service.get_translation('info_main', lang, {
            'bot_username': bot_username
        })
        
        return {
            'message': message,
            'parse_mode': 'HTML'
        }
    
    def _handle_start(
        self,
        user_id: UUID,
        user_lang: Optional[str],
        start_param: Optional[str]
    ) -> Dict[str, Any]:
        """Handle /start command"""
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        lang = user_lang or user.language_code or 'en'
        lang = self.translation_service.detect_language(lang)
        
        # Note: Referral logging is handled in webhook handler (_handle_message)
        # to avoid double logging when /start command is processed
        
        # Get bot username for translation variables
        bot_username = self._get_bot_username() or ''
        
        message = self.translation_service.get_translation('welcome', lang, {
            'bot_username': bot_username
        })
        
        return {
            'message': message,
            'parse_mode': 'HTML'
        }

