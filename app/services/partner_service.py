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

logger = logging.getLogger(__name__)


class PartnerService:
    """
    Multi-tenant partner service.
    Manages partner bots catalog (replaces Partners_Settings Google Sheets).
    """
    
    def __init__(self, db: Session, bot_id: UUID):
        self.db = db
        self.bot_id = bot_id
    
    def get_top_partners(
        self,
        limit: int = 50,
        user_lang: str = 'en'
    ) -> List[Dict[str, Any]]:
        """
        Get TOP partners (requires unlock).
        Replaces /top Google Sheets query + Format_TopBots_Message.
        
        Args:
            limit: Maximum number of partners to return
            user_lang: User's language for descriptions
        
        Returns:
            List of partner dictionaries
        """
        # Query all partners (exclude soft-deleted), filter in Python to avoid JSONB query issues
        all_partners = self.db.query(BusinessData).filter(
            and_(
                BusinessData.bot_id == self.bot_id,
                BusinessData.data_type == 'partner',
                BusinessData.deleted_at.is_(None)  # Exclude soft-deleted
            )
        ).all()
        
        # Filter in Python
        partners = []
        for p in all_partners:
            data = p.data or {}
            category = data.get('category', '')
            active = data.get('active', '')
            verified = data.get('verified', '')
            
            # Log filtering for debugging
            if category != 'TOP':
                logger.debug(f"TOP Partner {data.get('bot_name', 'Unknown')} filtered: category={category} (not TOP)")
            elif active != 'Yes':
                logger.debug(f"TOP Partner {data.get('bot_name', 'Unknown')} filtered: active={active}")
            elif verified != 'Yes':
                logger.debug(f"TOP Partner {data.get('bot_name', 'Unknown')} filtered: verified={verified}")
            
            if (category == 'TOP' and 
                active == 'Yes' and 
                verified == 'Yes'):
                partners.append(p)
        
        logger.info(f"get_top_partners: Found {len(partners)} TOP partners (from {len(all_partners)} total) for bot {self.bot_id}")
        
        # Convert to dicts and sort by ROI Score
        partner_list = []
        for partner in partners:
            data = partner.data
            roi_score = float(data.get('roi_score', 0))
            
            partner_list.append({
                'id': str(partner.id),
                'bot_name': data.get('bot_name', 'Bot'),
                'description': self._get_localized_description(data, user_lang),
                'referral_link': data.get('referral_link', ''),
                'commission': float(data.get('commission', 0)),
                'roi_score': roi_score,
                'category': data.get('category', 'TOP'),
                'active': data.get('active', 'Yes'),
                'verified': data.get('verified', 'Yes'),
            })
        
        # Sort by ROI Score (descending)
        partner_list.sort(key=lambda x: x['roi_score'], reverse=True)
        
        return partner_list[:limit]
    
    def get_partners(
        self,
        limit: int = 100,
        user_lang: str = 'en'
    ) -> List[Dict[str, Any]]:
        """
        Get regular partners (not TOP).
        Replaces /partners Google Sheets query.
        
        Args:
            limit: Maximum number of partners
            user_lang: User's language for descriptions
        
        Returns:
            List of partner dictionaries
        """
        # Query all partners (exclude soft-deleted), filter in Python to avoid JSONB query issues
        all_partners = self.db.query(BusinessData).filter(
            and_(
                BusinessData.bot_id == self.bot_id,
                BusinessData.data_type == 'partner',
                BusinessData.deleted_at.is_(None)  # Exclude soft-deleted
            )
        ).all()
        
        # Filter in Python
        partners = []
        for p in all_partners:
            data = p.data or {}
            category = data.get('category', '')
            active = data.get('active', '')
            verified = data.get('verified', '')
            
            # Log filtering for debugging
            if category == 'TOP':
                logger.debug(f"Partner {data.get('bot_name', 'Unknown')} filtered: category=TOP")
            elif active != 'Yes':
                logger.debug(f"Partner {data.get('bot_name', 'Unknown')} filtered: active={active}")
            elif verified != 'Yes':
                logger.debug(f"Partner {data.get('bot_name', 'Unknown')} filtered: verified={verified}")
            
            if (category != 'TOP' and 
                active == 'Yes' and 
                verified == 'Yes'):
                partners.append(p)
        
        logger.info(f"get_partners: Found {len(partners)} partners (from {len(all_partners)} total) for bot {self.bot_id}")
        
        partner_list = []
        for partner in partners:
            data = partner.data
            
            partner_list.append({
                'id': str(partner.id),
                'bot_name': data.get('bot_name', 'Bot'),
                'description': self._get_localized_description(data, user_lang),
                'referral_link': data.get('referral_link', ''),
                'commission': float(data.get('commission', 0)),
                'category': data.get('category', 'NEW'),
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
        
        Args:
            referral_link: Base referral link
            referral_tag: User's referral tag (e.g., '_tgr_123456')
        
        Returns:
            Personalized referral link
        """
        if not referral_link:
            return ''
        
        import re
        
        # If already has _tgr_ or tgr_ tag, keep it
        if re.search(r'(\?|&)start=(?:_?tgr_)', referral_link, re.IGNORECASE):
            return referral_link
        
        # Replace placeholders
        link = referral_link
        link = link.replace('{TGR}', referral_tag)
        link = link.replace('_tgr_', referral_tag)
        
        # Replace start=share with user's tag
        link = re.sub(
            r'(\?|&)(start|payload)=share\b',
            f'\\1\\2={referral_tag}',
            link,
            flags=re.IGNORECASE
        )
        
        # If no start parameter, add it
        if not re.search(r'(\?|&)start=', link):
            separator = '&' if '?' in link else '?'
            link = f"{link}{separator}start={referral_tag}"
        
        return link
    
    def format_top_message(
        self,
        partners: List[Dict[str, Any]],
        referral_tag: str,
        user_lang: str = 'en',
        max_length: int = 3900
    ) -> str:
        """
        Format TOP partners list as message.
        Replaces Format_TopBots_Message Code node logic.
        
        Args:
            partners: List of partner dictionaries
            referral_tag: User's referral tag
            user_lang: User's language
            max_length: Maximum message length
        
        Returns:
            Formatted message text
        """
        if not partners:
            # Return empty message (will be handled by caller)
            return ''
        
        # Intro text (will be from translations)
        # For now, placeholder
        intro = "🔥 TOP partners with the best earning potential:\n\n"
        
        message_parts = []
        current_length = len(intro)
        
        for partner in partners:
            name = partner['bot_name']
            desc = partner['description']
            commission = partner['commission']
            link = self.personalize_referral_link(
                partner['referral_link'],
                referral_tag
            )
            
            # Format partner block
            block = f"🤖 <b>{name}</b>\n{desc}\n🪙 Bonus program: {commission}%\n👉 <a href=\"{link}\">Open</a>"
            
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

