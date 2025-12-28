"""
Earnings Service - Multi-tenant earnings center
Handles earnings display, progress tracking, 7% program info
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.services.user_service import UserService
from app.services.referral_service import ReferralService
from app.services.translation_service import TranslationService


class EarningsService:
    """
    Multi-tenant earnings service.
    Builds earnings center messages with progress, TOP status, 7% info.
    """
    
    REQUIRED_INVITES = 5
    
    def __init__(
        self,
        db: Session,
        bot_id: UUID,
        user_service: UserService,
        referral_service: ReferralService,
        translation_service: TranslationService
    ):
        self.db = db
        self.bot_id = bot_id
        self.user_service = user_service
        self.referral_service = referral_service
        self.translation_service = translation_service
    
    def build_earnings_message(
        self,
        user_id: UUID,
        user_lang: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build earnings center message.
        Replaces Build_Earnings_Message Code node logic.
        
        Args:
            user_id: User UUID
            user_lang: User's language code
        
        Returns:
            Dictionary with message text, referral_link, and metadata
        """
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        lang = user_lang or user.language_code or 'en'
        lang = self.translation_service.detect_language(lang)
        
        # Get user data
        wallet = self.user_service.get_wallet(user_id)
        earned = float(user.balance) if user.balance else 0.0
        total_invited = self.referral_service.get_total_invited(user_id)
        top_status = self.user_service.get_top_status(user_id)
        
        # Generate referral link
        referral_tag = self.referral_service.generate_referral_tag(user_id)
        referral_link = self.referral_service.generate_referral_link(user_id)
        
        # Check TOP unlock eligibility
        can_unlock, invites_needed = self.referral_service.check_top_unlock_eligibility(user_id)
        
        # Build message parts
        message_parts = []
        
        # Header
        if wallet and earned > 0:
            header = self.translation_service.get_translation(
                'earnings_has_income',
                lang,
                {'wallet': wallet, 'earned': earned}
            )
        else:
            header = self.translation_service.get_translation('earnings_no_income', lang)
        
        title = self.translation_service.get_translation('earnings_title', lang)
        message_parts.append(f"<b>{title}</b>\n\n{header}\n")
        
        # Block 1: TOP unlock progress
        block1 = self._build_top_block(lang, total_invited, invites_needed, referral_link, can_unlock)
        message_parts.append(block1)
        
        # Block 2: 7% program
        block2 = self._build_7percent_block(lang)
        message_parts.append(block2)
        
        # Block 3: What to do now
        block3 = self._build_action_block(lang, can_unlock, invites_needed)
        message_parts.append(block3)
        
        message_text = "\n\n".join(message_parts)
        
        return {
            'text': message_text,
            'referral_link': referral_link,
            'invites': total_invited,
            'needed': invites_needed,
            'wallet': wallet or '',
            'earned': earned,
            'top_status': top_status,
        }
    
    def _build_top_block(
        self,
        lang: str,
        total_invited: int,
        invites_needed: int,
        referral_link: str,
        can_unlock: bool
    ) -> str:
        """Build TOP unlock progress block"""
        block_title = self.translation_service.get_translation('earnings_block1_title', lang)
        
        # Progress bar
        total_steps = self.REQUIRED_INVITES
        filled = min(total_invited, total_steps)
        bar_filled = '🟩' * filled
        bar_empty = '⬜️' * (total_steps - filled)
        bar = bar_filled + bar_empty
        
        # Friends label (language-specific)
        friends_map = {
            'uk': 'друзів',
            'en': 'friends',
            'ru': 'друзей',
            'de': 'Freunde',
            'es': 'amigos',
        }
        friends_label = friends_map.get(lang, 'friends')
        
        # To TOP label
        to_top_map = {
            'uk': 'до TOP',
            'en': 'to TOP',
            'ru': 'до TOP',
            'de': 'bis TOP',
            'es': 'hasta TOP',
        }
        to_top_label = to_top_map.get(lang, 'to TOP')
        
        line1 = self.translation_service.get_translation('earnings_block1_line1', lang)
        benefit1 = self.translation_service.get_translation('earnings_block1_benefit1', lang)
        benefit2 = self.translation_service.get_translation('earnings_block1_benefit2', lang)
        benefit3 = self.translation_service.get_translation('earnings_block1_benefit3', lang)
        
        ref_label_map = {
            'uk': '🔗 Твоя реферальна лінка:',
            'en': '🔗 Your referral link:',
            'ru': '🔗 Твоя реферальная ссылка:',
            'de': '🔗 Dein Empfehlungslink:',
            'es': '🔗 Tu enlace de referido:',
        }
        ref_label = ref_label_map.get(lang, '🔗 Your referral link:')
        
        block = f"""━━━━━━━━━━
<b>{block_title}</b>

👥 {total_invited} / {total_steps} {friends_label}
{bar}  +{invites_needed} {to_top_label}
({self.translation_service.get_translation('earnings_btn_unlock_top', lang, {'buy_top_price': 1})})

{ref_label}
{referral_link}

{line1}
{benefit1}
{benefit2}
{benefit3}"""
        
        return block
    
    def _build_7percent_block(self, lang: str) -> str:
        """Build 7% Telegram partner program block"""
        block_title = self.translation_service.get_translation('earnings_block2_title', lang)
        how_it_works = self.translation_service.get_translation('earnings_block2_how_it_works', lang)
        examples = self.translation_service.get_translation('earnings_block2_examples', lang)
        enable_title = self.translation_service.get_translation('earnings_enable_7_title', lang)
        enable_steps = self.translation_service.get_translation('earnings_enable_7_steps', lang)
        
        block = f"""━━━━━━━━━━
<b>{block_title}</b>

{how_it_works}

{examples}

<b>{enable_title}</b>
{enable_steps}"""
        
        return block
    
    def _build_action_block(
        self,
        lang: str,
        can_unlock: bool,
        invites_needed: int
    ) -> str:
        """Build 'What to do now' block"""
        block_title = self.translation_service.get_translation('earnings_block3_title', lang)
        
        if can_unlock:
            step1 = self.translation_service.get_translation('earnings_step1_open', lang)
        else:
            step1 = self.translation_service.get_translation(
                'earnings_step1_locked',
                lang,
                {'needed': invites_needed}
            )
        
        step2 = self.translation_service.get_translation('earnings_step2', lang)
        step3 = self.translation_service.get_translation('earnings_step3', lang)
        step4 = self.translation_service.get_translation('earnings_step4', lang)
        auto_stats = self.translation_service.get_translation('earnings_auto_stats', lang)
        
        block = f"""━━━━━━━━━━
<b>{block_title}</b>

{step1}
{step2}
{step3}
{step4}

{auto_stats}"""
        
        return block

