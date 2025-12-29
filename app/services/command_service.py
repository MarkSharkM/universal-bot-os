"""
Command Service - Multi-tenant command router
Routes bot commands to appropriate handlers (replaces Switch_Commands logic)
"""
from typing import Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from uuid import UUID
import re

from app.services.user_service import UserService
from app.services.translation_service import TranslationService
from app.services.partner_service import PartnerService
from app.services.referral_service import ReferralService
from app.services.earnings_service import EarningsService


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
        'earnings': r'^/(?:start\s+)?earnings\b',
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
        
        # Check each pattern
        for cmd, pattern in self.COMMAND_PATTERNS.items():
            if re.match(pattern, text, re.IGNORECASE):
                return cmd
        
        return None
    
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
    
    def handle_command(
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
            return {'error': f'Unknown command: {command}'}
        
        return handler(user_id, user_lang, start_param)
    
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
            # No wallet
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
    
    def _handle_top(
        self,
        user_id: UUID,
        user_lang: Optional[str],
        start_param: Optional[str]
    ) -> Dict[str, Any]:
        """Handle /top command"""
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        lang = user_lang or user.language_code or 'en'
        lang = self.translation_service.detect_language(lang)
        
        # Check TOP unlock status
        can_unlock, invites_needed = self.referral_service.check_top_unlock_eligibility(user_id)
        top_status = self.user_service.get_top_status(user_id)
        
        if top_status == 'locked' and not can_unlock:
            # TOP is locked - use translations from database
            referral_tag = self.referral_service.generate_referral_tag(user_id)
            referral_link = self.referral_service.generate_referral_link(user_id)
            
            # Get total invited count
            total_invited = self.referral_service.get_total_invited(user_id)
            
            # Get buy_top_price from translations
            buy_top_price = self.translation_service.get_translation('buy_top_price', lang) or '1'
            try:
                buy_top_price = int(buy_top_price)
            except:
                buy_top_price = 1
            
            # Use translation key for locked message (with needed parameter)
            # Use top_locked_message for /top command (full message with share prompt)
            # earnings_step1_locked is shorter and used in /earnings
            message = self.translation_service.get_translation(
                'top_locked_message',
                lang,
                {'needed': invites_needed}
            )
            
            # Fallback to earnings_step1_locked if top_locked_message not found
            if not message or message == 'top_locked_message':
                message = self.translation_service.get_translation(
                    'earnings_step1_locked',
                    lang,
                    {'needed': invites_needed}
                )
            
            # Get share text for button URL only (not in message)
            share_text = self.translation_service.get_translation('share_referral', lang, {
                'referralLink': referral_link
            })
            
            buttons = [[
                {
                    'text': self.translation_service.get_translation('share_button', lang),
                    'url': f"https://t.me/share/url?url={referral_link}&text={share_text}"
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
        partners = self.partner_service.get_top_partners(limit=20, user_lang=lang)
        referral_tag = self.referral_service.generate_referral_tag(user_id)
        
        message = self.partner_service.format_top_message(
            partners,
            referral_tag,
            lang
        )
        
        if not message:
            message = self.translation_service.get_translation('errorEmptyTopByLang', lang)
        
        buttons = [[{
            'text': self.translation_service.get_translation('share_button', lang),
            'url': f"https://t.me/share/url?url={self.referral_service.generate_referral_link(user_id)}"
        }]]
        
        return {
            'message': message,
            'buttons': buttons,
            'parse_mode': 'HTML',
            'top_status': 'open'
        }
    
    def _handle_partners(
        self,
        user_id: UUID,
        user_lang: Optional[str],
        start_param: Optional[str]
    ) -> Dict[str, Any]:
        """Handle /partners command"""
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        lang = user_lang or user.language_code or 'en'
        lang = self.translation_service.detect_language(lang)
        
        partners = self.partner_service.get_partners(limit=50, user_lang=lang)
        
        # Build message
        intro = self.translation_service.get_translation('partners_intro', lang)
        if not intro or intro == 'partners_intro':  # Fallback if translation not found
            intro_map = {
                'uk': "🤖 <b>Перевірені Telegram-боти, які дають зірки за активність</b>\nОбери будь-який — запускай та прокачуйся! 💪",
                'en': "🤖 <b>Verified Telegram bots that give you Stars for actions</b>\nPick any — launch and level up! 💪",
                'ru': "🤖 <b>Проверенные Telegram-боты, которые дают звезды за активность</b>\nВыбери любой — запускай и прокачивайся! 💪",
            }
            intro = intro_map.get(lang, intro_map['en'])
        
        if not partners:
            empty_msg = self.translation_service.get_translation('partners_empty', lang)
            if not empty_msg or empty_msg == 'partners_empty':
                empty_msg = "Поки що немає доступних партнерів." if lang == 'uk' else "No partners available yet."
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
                line = f"⭐ <b>{i}. {partner['bot_name']}</b>\n{partner['description']}\n🔗 <a href=\"{partner['referral_link']}\">{launch_label}</a>"
                partner_lines.append(line)
            
            message = f"{intro}\n\n" + "\n\n".join(partner_lines)
        
        buttons = [
            [{'text': self.translation_service.get_translation('share_button', lang), 'callback_data': 'share_from_partners'}],
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
        
        referral_link = self.referral_service.generate_referral_link(user_id)
        
        message = self.translation_service.get_translation(
            'share_referral',
            lang,
            {'referralLink': referral_link}
        )
        
        share_text = self.translation_service.get_translation('share_referral', lang, {
            'referralLink': referral_link
        })
        
        buttons = [[{
            'text': self.translation_service.get_translation('share_button', lang),
            'url': f"https://t.me/share/url?url={referral_link}&text={share_text}"
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
        earnings_data = self.earnings_service.build_earnings_message(user_id, user_lang)
        
        buttons = [
            [{'text': self.translation_service.get_translation('share_button', earnings_data.get('lang', 'en')), 'callback_data': 'share_from_earnings'}],
            [
                {'text': self.translation_service.get_translation('earnings_btn_unlock_top', earnings_data.get('lang', 'en'), {'buy_top_price': 1}), 'callback_data': 'buy_top'},
                {'text': self.translation_service.get_translation('earnings_btn_top_partners', earnings_data.get('lang', 'en')), 'callback_data': '=/top'}
            ],
            [{'text': self.translation_service.get_translation('earnings_btn_activate_7', earnings_data.get('lang', 'en')), 'callback_data': 'activate_7'}],
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
        
        message = self.translation_service.get_translation('info_main', lang)
        
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
        
        # If has start_param, might be referral
        if start_param:
            is_referral, inviter_external_id, ref_tag = self.referral_service.parse_referral_parameter(start_param)
            if is_referral:
                # Log referral event
                self.referral_service.log_referral_event(
                    user_id,
                    start_param,
                    event_type='start',
                    click_type='Referral'
                )
        
        message = self.translation_service.get_translation('welcome', lang)
        
        return {
            'message': message,
            'parse_mode': 'HTML'
        }

