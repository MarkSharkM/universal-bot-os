"""
Command Service - Multi-tenant command router
Routes bot commands to appropriate handlers (replaces Switch_Commands logic)
"""
from typing import Dict, Any, Optional, Callable
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
        logger.info(f"handle_command: command={command}, user_id={user_id}, lang={user_lang}, start_param={start_param}")
        
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
            partners = self.partner_service.get_top_partners(limit=20, user_lang=lang)
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
                lang
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
                }
                error_msg = error_msg_map.get(lang, error_msg_map['en'])
            message = error_msg
        
        referral_link = self.referral_service.generate_referral_link(user_id)
        buttons = [[{
            'text': self.translation_service.get_translation('share_button', lang),
            'url': f"https://t.me/share/url?url={quote(referral_link, safe='')}"
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
        logger.info(f"_handle_partners: user_id={user_id}, lang={user_lang}")
        
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found in _handle_partners")
            raise ValueError(f"User {user_id} not found")
        
        lang = user_lang or user.language_code or 'en'
        lang = self.translation_service.detect_language(lang)
        logger.info(f"_handle_partners: detected lang={lang}")
        
        try:
            partners = self.partner_service.get_partners(limit=50, user_lang=lang)
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
                # Use partner link as-is from database (no personalization)
                line = f"⭐ <b>{i}. {partner['bot_name']}</b>\n{partner['description']}\n🔗 <a href=\"{partner['referral_link']}\">{launch_label}</a>"
                partner_lines.append(line)
            
            message = f"{intro}\n\n" + "\n\n".join(partner_lines)
        
        # Generate referral link for share button
        referral_link = self.referral_service.generate_referral_link(user_id)
        share_text = self.translation_service.get_translation('share_referral', lang, {
            'referralLink': referral_link
        })
        
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
        
        referral_link = self.referral_service.generate_referral_link(user_id)
        
        message = self.translation_service.get_translation(
            'share_referral',
            lang,
            {'referralLink': referral_link}
        )
        
        # For share button text, use text WITHOUT URL to avoid duplicate links
        # URL is already in the 'url' parameter, Telegram will add preview automatically
        share_text_without_url = self.translation_service.get_translation('share_referral_text', lang, {})
        if not share_text_without_url or share_text_without_url == 'share_referral_text':
            # Fallback: use share_referral but remove URL part
            share_text_full = self.translation_service.get_translation('share_referral', lang, {
                'referralLink': referral_link
            })
            # Remove the URL line if it exists
            share_text_without_url = '\n'.join([line for line in share_text_full.split('\n') if not line.startswith('http')])
        
        buttons = [[{
            'text': self.translation_service.get_translation('share_button', lang),
            'url': f"https://t.me/share/url?url={quote(referral_link, safe='')}&text={quote(share_text_without_url, safe='')}"
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
        
        try:
            logger.info(f"_handle_earnings: calling build_earnings_message")
            earnings_data = self.earnings_service.build_earnings_message(user_id, user_lang)
            logger.info(f"_handle_earnings: build_earnings_message completed, has_text={bool(earnings_data.get('text'))}")
        except Exception as e:
            logger.error(f"_handle_earnings: error in build_earnings_message: {e}", exc_info=True)
            raise
        
        # Get language from earnings_data (now included in response)
        lang = earnings_data.get('lang', user_lang or 'en')
        
        # Generate referral link for share button
        referral_link = earnings_data.get('referral_link') or self.referral_service.generate_referral_link(user_id)
        share_text = self.translation_service.get_translation('share_referral', lang, {
            'referralLink': referral_link
        })
        
        buttons = [
            [{'text': self.translation_service.get_translation('share_button', lang), 'url': f"https://t.me/share/url?url={quote(referral_link, safe='')}&text={quote(share_text, safe='')}"}],
            [
                {'text': self.translation_service.get_translation('earnings_btn_unlock_top', lang, {'buy_top_price': 1}), 'callback_data': 'buy_top'},
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
        
        # Note: Referral logging is handled in webhook handler (_handle_message)
        # to avoid double logging when /start command is processed
        
        message = self.translation_service.get_translation('welcome', lang)
        
        return {
            'message': message,
            'parse_mode': 'HTML'
        }

