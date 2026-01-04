"""
Partner Service - Multi-tenant partner bot management
Handles TOP partners, regular partners, filtering, sorting
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from uuid import UUID
import logging

from app.models.business_data import BusinessData
from app.models.bot import Bot

logger = logging.getLogger(__name__)


class PartnerService:
    """
    Multi-tenant partner service.
    Manages partner bots catalog (replaces Partners_Settings Google Sheets).
    """
    
    def __init__(self, db: Session, bot_id: UUID):
        self.db = db
        self.bot_id = bot_id
        self._bot_config = None  # Lazy load bot.config
    
    def _get_bot_config(self) -> dict:
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
    
    def _is_partners_enabled(self) -> bool:
        """
        Check if partners are enabled for this bot.
        
        Returns:
            True if partners are enabled, False otherwise
        """
        config = self._get_bot_config()
        partners_config = config.get('partners', {})
        return partners_config.get('enabled', True)  # Default: enabled
    
    async def get_top_partners(
        self,
        limit: int = 50,
        user_lang: str = 'en'
    ) -> List[Dict[str, Any]]:
        """
        Get TOP partners (requires unlock).
        Replaces /top Google Sheets query + Format_TopBots_Message.
        
        Args:
            limit: Maximum number of partners to return (overridden by bot.config if set)
            user_lang: User's language for descriptions
        
        Returns:
            List of partner dictionaries
        """
        # Check if partners are enabled
        if not self._is_partners_enabled():
            logger.info(f"get_top_partners: Partners disabled for bot {self.bot_id}")
            return []
        
        # Get limit from bot.config or use provided
        config = self._get_bot_config()
        partners_config = config.get('partners', {})
        top_config = partners_config.get('top', {})
        if top_config.get('limit'):
            limit = int(top_config['limit'])
        
        # Get min_commission filter
        min_commission = top_config.get('min_commission', 0)
        
        # Optimized: Filter in SQL using JSONB operators (PostgreSQL)
        # This avoids loading all partners and filtering in Python
        from sqlalchemy import text
        
        partners = self.db.query(BusinessData).filter(
            and_(
                BusinessData.bot_id == self.bot_id,
                BusinessData.data_type == 'partner',
                BusinessData.deleted_at.is_(None),  # Exclude soft-deleted
                # Filter by JSONB fields directly in SQL using PostgreSQL JSONB operators
                text("(data->>'category') = 'TOP'"),
                text("(data->>'active') = 'Yes'"),
                text("(data->>'verified') = 'Yes'")
            )
        ).limit(limit * 2).all()  # Get a bit more for sorting, then limit
        
        logger.info(f"get_top_partners: Found {len(partners)} TOP partners (filtered in SQL) for bot {self.bot_id}")
        
        # Convert to dicts and sort by ROI Score
        partner_list = []
        for partner in partners:
            data = partner.data
            roi_score = float(data.get('roi_score', 0))
            referral_link = data.get('referral_link', '')
            
            # Auto-detect bot icon from Telegram if referral_link is a t.me bot link
            icon_url = data.get('icon', '') or data.get('image', '')
            
            # If no custom icon and referral_link is a Telegram bot link, try to get bot avatar
            if not icon_url and referral_link:
                import re
                # Extract bot username from t.me/botname or t.me/botname?start=...
                match = re.search(r't\.me/([a-zA-Z0-9_]+)', referral_link)
                if match:
                    bot_username = match.group(1)
                    try:
                        from app.adapters.telegram import TelegramAdapter
                        adapter = TelegramAdapter()
                        # Use our bot's token to fetch partner bot's avatar
                        avatar_url = await adapter.get_bot_avatar_url(self.bot_id, bot_username)
                        if avatar_url:
                            icon_url = avatar_url
                            logger.info(f"Auto-fetched avatar for TOP bot @{bot_username}: {icon_url[:50]}...")
                    except Exception as e:
                        logger.warning(f"Could not auto-fetch avatar for @{bot_username}: {e}")
            
            partner_list.append({
                'id': str(partner.id),
                'name': data.get('bot_name', 'Bot'),  # Use 'name' for frontend compatibility
                'bot_name': data.get('bot_name', 'Bot'),  # Keep for backward compatibility
                'description': self._get_localized_description(data, user_lang),
                'referral_link': referral_link,
                'commission': float(data.get('commission', 0)),
                'roi_score': roi_score,
                'category': data.get('category', 'TOP'),
                'active': data.get('active', 'Yes'),
                'verified': data.get('verified', 'Yes'),
                'icon': icon_url,  # Auto-fetched from Telegram or custom
                'image': icon_url,  # Same as icon for backward compatibility
            })
        
        # Sort by ROI Score (descending)
        partner_list.sort(key=lambda x: x['roi_score'], reverse=True)
        
        return partner_list[:limit]
    
    async def get_partners(
        self,
        limit: int = 100,
        user_lang: str = 'en'
    ) -> List[Dict[str, Any]]:
        """
        Get regular partners (not TOP).
        Replaces /partners Google Sheets query.
        
        Args:
            limit: Maximum number of partners (overridden by bot.config if set)
            user_lang: User's language for descriptions
        
        Returns:
            List of partner dictionaries
        """
        # Check if partners are enabled
        if not self._is_partners_enabled():
            logger.info(f"get_partners: Partners disabled for bot {self.bot_id}")
            return []
        
        # Get limit from bot.config or use provided
        config = self._get_bot_config()
        partners_config = config.get('partners', {})
        if partners_config.get('max_partners'):
            limit = int(partners_config['max_partners'])
        
        # Optimized: Filter in SQL using JSONB operators (PostgreSQL)
        # This avoids loading all partners and filtering in Python
        from sqlalchemy import text, or_
        
        partners = self.db.query(BusinessData).filter(
            and_(
                BusinessData.bot_id == self.bot_id,
                BusinessData.data_type == 'partner',
                BusinessData.deleted_at.is_(None),  # Exclude soft-deleted
                # Filter by JSONB fields directly in SQL using PostgreSQL JSONB operators
                # category != 'TOP' OR category is NULL (for old records)
                or_(
                    text("(data->>'category') != 'TOP'"),
                    text("(data->>'category') IS NULL")
                ),
                text("(data->>'active') = 'Yes'"),
                text("(data->>'verified') = 'Yes'")
            )
        ).limit(limit * 2).all()  # Get a bit more for sorting, then limit
        
        logger.info(f"get_partners: Found {len(partners)} partners (filtered in SQL) for bot {self.bot_id}")
        
        partner_list = []
        for partner in partners:
            data = partner.data
            referral_link = data.get('referral_link', '')
            
            # Auto-detect bot icon from Telegram if referral_link is a t.me bot link
            icon_url = data.get('icon', '') or data.get('image', '')
            
            # If no custom icon and referral_link is a Telegram bot link, try to get bot avatar
            if not icon_url and referral_link:
                import re
                # Extract bot username from t.me/botname or t.me/botname?start=...
                match = re.search(r't\.me/([a-zA-Z0-9_]+)', referral_link)
                if match:
                    bot_username = match.group(1)
                    try:
                        from app.adapters.telegram import TelegramAdapter
                        adapter = TelegramAdapter()
                        # Use our bot's token to fetch partner bot's avatar
                        avatar_url = await adapter.get_bot_avatar_url(self.bot_id, bot_username)
                        if avatar_url:
                            icon_url = avatar_url
                            logger.info(f"Auto-fetched avatar for bot @{bot_username}: {icon_url[:50]}...")
                    except Exception as e:
                        logger.warning(f"Could not auto-fetch avatar for @{bot_username}: {e}")
            
            partner_list.append({
                'id': str(partner.id),
                'name': data.get('bot_name', 'Bot'),  # Use 'name' for frontend compatibility
                'bot_name': data.get('bot_name', 'Bot'),  # Keep for backward compatibility
                'description': self._get_localized_description(data, user_lang),
                'referral_link': referral_link,
                'commission': float(data.get('commission', 0)),
                'category': data.get('category', 'NEW'),
                'icon': icon_url,  # Auto-fetched from Telegram or custom
                'image': icon_url,  # Same as icon for backward compatibility
            })
        
        return partner_list[:limit]
    
    def _get_localized_description(
        self,
        partner_data: Dict[str, Any],
        lang: str
    ) -> str:
        """
        Get localized description for partner.
        Falls back to base description if localized not available.
        
        Args:
            partner_data: Partner data dictionary
            lang: Language code (uk, en, ru, de, es)
        
        Returns:
            Localized description
        """
        # For Ukrainian (uk), use base 'description' field
        if lang == 'uk':
            desc = partner_data.get('description', '')
            if desc:
                return desc
            # Fallback to EN if UK not available
            desc = partner_data.get('description_en', '')
            if desc:
                return desc
        
        # For other languages, try description_{lang}
        localized_key = f'description_{lang}'
        if localized_key in partner_data:
            desc = partner_data[localized_key]
            if desc:
                return desc
        
        # Fallback chain: base description -> description_en -> empty
        desc = partner_data.get('description', '')
        if desc:
            return desc
        
        desc = partner_data.get('description_en', '')
        if desc:
            return desc
        
        return ''
    
    def personalize_referral_link(
        self,
        referral_link: str,
        referral_tag: str
    ) -> str:
        """
        Personalize referral link with user's tag.
        Replaces personalizeReferral logic from Format_TopBots_Message.
        
        IMPORTANT: For partner links, we use same format as /share: just {userId} (no _tgr_ prefix).
        This matches the main referral links format for consistency.
        
        Args:
            referral_link: Base referral link (from partner)
            referral_tag: User's referral tag (user.external_id, e.g. "380927579")
        
        Returns:
            Personalized referral link
        """
        if not referral_link:
            return ''
        
        import re
        
        # For partner links, use same format as /share: just {userId} (no _tgr_ prefix)
        # referral_tag is already user.external_id (e.g. "380927579")
        partner_tag = referral_tag
        
        # Replace placeholders first
        link = referral_link
        link = link.replace('{TGR}', partner_tag)
        
        # Replace existing _tgr_XXX with new partner_tag (personalize the link)
        # This handles cases like: https://t.me/boinker_bot?start=_tgr_qEfhJpQxZGQy
        # Will become: https://t.me/boinker_bot?start=_tgr_{userId}
        link = re.sub(
            r'(\?|&)start=_?tgr_[^&]*',
            f'\\1start={partner_tag}',
            link,
            flags=re.IGNORECASE
        )
        
        # Also replace any remaining _tgr_ in the link (for placeholders)
        if '{TGR}' not in link and '_tgr_' in link:
            # Only replace if it's not already replaced above
            link = link.replace('_tgr_', partner_tag)
        
        # Replace start=share with user's tag (use _tgr_ format for partners)
        link = re.sub(
            r'(\?|&)(start|payload)=share\b',
            f'\\1\\2={partner_tag}',
            link,
            flags=re.IGNORECASE
        )
        
        # If no start parameter, add it (use _tgr_ format for partners)
        if not re.search(r'(\?|&)start=', link):
            separator = '&' if '?' in link else '?'
            link = f"{link}{separator}start={partner_tag}"
        
        return link
    
    def format_top_message(
        self,
        partners: List[Dict[str, Any]],
        referral_tag: str,
        user_lang: str = 'en',
        max_length: int = 3900,
        translation_service = None
    ) -> str:
        """
        Format TOP partners list as message.
        Replaces Format_TopBots_Message Code node logic.
        
        Args:
            partners: List of partner dictionaries
            referral_tag: User's referral tag
            user_lang: User's language
            max_length: Maximum message length
            translation_service: TranslationService instance for getting translations
        
        Returns:
            Formatted message text
        """
        if not partners:
            logger.warning(f"format_top_message: No partners provided for formatting")
            # Return empty message (will be handled by caller)
            return ''
        
        # Get intro text from translations
        if translation_service:
            intro = translation_service.get_translation('top_partners_intro', user_lang)
            if not intro or intro == 'top_partners_intro':
                # Fallback if translation not found
                intro_map = {
                    'uk': '🔥 ТОП партнери з найкращим заробітком:\n\n',
                    'en': '🔥 TOP partners with the best earning potential:\n\n',
                    'ru': '🔥 ТОП партнёры с лучшим заработком:\n\n',
                    'de': '🔥 TOP-Partner mit dem besten Verdienstpotenzial:\n\n',
                    'es': '🔥 Socios TOP con el mejor potencial de ganancias:\n\n',
                }
                intro = intro_map.get(user_lang, intro_map['en'])
        else:
            # Fallback if no translation service
            intro = "🔥 TOP partners with the best earning potential:\n\n"
        
        # Get labels from translations
        if translation_service:
            bonus_label = translation_service.get_translation('bonus_program_label', user_lang)
            if not bonus_label or bonus_label == 'bonus_program_label':
                bonus_label_map = {
                    'uk': 'Бонусна програма:',
                    'en': 'Bonus program:',
                    'ru': 'Бонусная программа:',
                    'de': 'Bonusprogramm:',
                    'es': 'Programa de bonificación:',
                }
                bonus_label = bonus_label_map.get(user_lang, bonus_label_map['en'])
            
            open_label = translation_service.get_translation('open_label', user_lang)
            if not open_label or open_label == 'open_label':
                open_label_map = {
                    'uk': 'Відкрити',
                    'en': 'Open',
                    'ru': 'Открыть',
                    'de': 'Öffnen',
                    'es': 'Abrir',
                }
                open_label = open_label_map.get(user_lang, open_label_map['en'])
        else:
            bonus_label = 'Bonus program:'
            open_label = 'Open'
        
        message_parts = []
        current_length = len(intro)
        
        for partner in partners:
            name = partner['bot_name']
            desc = partner['description']
            commission = partner['commission']
            # Use partner link as-is from database (no personalization)
            link = partner['referral_link']
            
            # Format partner block with translations
            block = f"🤖 <b>{name}</b>\n{desc}\n🪙 {bonus_label} {commission}%\n👉 <a href=\"{link}\">{open_label}</a>"
            
            # Check if adding this block would exceed limit
            block_length = len(block) + 2  # +2 for \n\n
            if current_length + block_length > max_length:
                break
            
            message_parts.append(block)
            current_length += block_length
        
        if not message_parts:
            return intro.strip()
        
        return intro + "\n\n".join(message_parts)
    
    def create_partner(
        self,
        bot_name: str,
        description: str,
        referral_link: str,
        commission: float,
        category: str = "NEW",  # 'TOP' or 'NEW'
        active: str = "Yes",
        verified: str = "Yes",
        descriptions: Optional[Dict[str, str]] = None,  # {lang: description}
        roi_score: float = 0.0
    ) -> BusinessData:
        """
        Create new partner bot.
        For admin use.
        
        Args:
            bot_name: Partner bot name
            description: Base description
            referral_link: Referral link template
            commission: Commission percentage
            category: Category (TOP/NEW)
            active: Active status (Yes/No)
            verified: Verified status (Yes/No)
            descriptions: Localized descriptions {lang: text}
            roi_score: ROI score for sorting
        
        Returns:
            Created BusinessData record
        """
        data = {
            'bot_name': bot_name,
            'description': description,
            'referral_link': referral_link,
            'commission': commission,
            'category': category,
            'active': active,
            'verified': verified,
            'roi_score': roi_score,
        }
        
        # Add localized descriptions
        if descriptions:
            for lang, desc in descriptions.items():
                data[f'description_{lang}'] = desc
        
        partner = BusinessData(
            bot_id=self.bot_id,
            data_type='partner',
            data=data
        )
        
        self.db.add(partner)
        self.db.commit()
        self.db.refresh(partner)
        
        return partner

