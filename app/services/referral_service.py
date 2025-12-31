"""
Referral Service - Multi-tenant referral tracking
Handles referral links, counting invites, referral validation
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, distinct
from uuid import UUID

from app.models.user import User
from app.models.message import Message
from app.models.business_data import BusinessData
from app.models.bot import Bot


class ReferralService:
    """
    Multi-tenant referral service.
    Handles referral tracking, counting, and validation.
    """
    
    REQUIRED_INVITES = 5  # Can be configured per bot
    
    def __init__(self, db: Session, bot_id: UUID):
        self.db = db
        self.bot_id = bot_id
    
    def generate_referral_tag(self, user_id: UUID) -> str:
        """
        Generate referral tag for user.
        Format: {userId} (changed from _tgr_{userId})
        
        Args:
            user_id: User UUID
        
        Returns:
            Referral tag string
        """
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.bot_id == self.bot_id
            )
        ).first()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        return str(user.external_id)
    
    def generate_referral_link(
        self,
        user_id: UUID,
        bot_username: Optional[str] = None
    ) -> str:
        """
        Generate referral link for user.
        
        Args:
            user_id: User UUID
            bot_username: Bot username (optional, will be fetched from bot.config if not provided)
        
        Returns:
            Full referral URL
        """
        tag = self.generate_referral_tag(user_id)
        
        # Get bot username from config if not provided
        if not bot_username:
            bot = self.db.query(Bot).filter(Bot.id == self.bot_id).first()
            if bot and bot.config and bot.config.get('username'):
                bot_username = bot.config['username']
            else:
                # Fallback: use correct production username
                # This should not happen if sync-username was called
                bot_username = "HubAggregatorBot"
        
        return f"https://t.me/{bot_username}?start={tag}"
    
    def parse_referral_parameter(
        self,
        ref_param: Optional[str]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Parse and validate referral parameter.
        
        Args:
            ref_param: Referral parameter from /start command
        
        Returns:
            Tuple of (is_valid, inviter_external_id, referral_tag)
        """
        if not ref_param:
            return False, None, None
        
        ref_param = ref_param.strip()
        
        # Reserved commands (not referrals)
        reserved = {
            'partners', 'top', 'wallet', 'earnings',
            'share', 'info', 'help', 'start', 'settings'
        }
        
        if ref_param.lower() in reserved:
            return False, None, None
        
        # Special case: GPT Store traffic (keep old format support)
        if ref_param.lower() in ['_tgr_gptstore', 'tgr_gptstore', 'gptstore']:
            return False, None, 'gptstore'
        
        # Support both old format (_tgr_{userId}) and new format ({userId})
        import re
        
        # New format: just {userId} (numeric or alphanumeric)
        # Check if it's a simple user ID (not a reserved command)
        if ref_param and not ref_param.lower() in reserved:
            # Try to match as direct user ID (numeric Telegram user ID)
            # Telegram user IDs are typically numeric, but can be alphanumeric
            if re.match(r'^[a-z0-9_-]+$', ref_param, re.IGNORECASE):
                # This looks like a user ID - treat as referral
                return True, ref_param, ref_param
        
        # Old format support: _tgr_{userId} or tgr_{userId} (for backward compatibility)
        pattern = r'^_?tgr_([a-z0-9-]+)$'
        match = re.match(pattern, ref_param, re.IGNORECASE)
        
        if match:
            inviter_external_id = match.group(1)
            return True, inviter_external_id, ref_param
        
        return False, None, None
    
    def log_referral_event(
        self,
        user_id: UUID,
        ref_param: Optional[str],
        event_type: str = "start",  # 'start', 'click', etc.
        click_type: str = "Organic"  # 'Organic', 'Referral', 'gptstore'
    ) -> BusinessData:
        """
        Log referral event to business_data.
        Replaces bot_log Google Sheets table.
        
        Args:
            user_id: User UUID
            ref_param: Referral parameter
            event_type: Type of event
            click_type: Type of click (Organic/Referral)
        
        Returns:
            Created BusinessData record
        """
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.bot_id == self.bot_id
            )
        ).first()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Parse referral
        is_referral, inviter_external_id, referral_tag = self.parse_referral_parameter(ref_param)
        
        if is_referral:
            click_type = "Referral"
        
        log_data = BusinessData(
            bot_id=self.bot_id,
            data_type='log',
            data={
                'user_id': str(user_id),
                'external_id': user.external_id,
                'ref_parameter': ref_param or 'NO_REF',
                'referral_tag': referral_tag,
                'inviter_external_id': inviter_external_id,
                'is_referral': is_referral,
                'click_type': click_type,
                'event_type': event_type,
            }
        )
        
        self.db.add(log_data)
        self.db.commit()
        self.db.refresh(log_data)
        
        # Update inviter's total_invited count if this is a referral
        if is_referral and inviter_external_id:
            inviter = self.db.query(User).filter(
                and_(
                    User.bot_id == self.bot_id,
                    User.external_id == inviter_external_id,
                    User.platform == 'telegram'
                )
            ).first()
            
            if inviter:
                # Update inviter's total_invited count
                self.update_total_invited(inviter.id)
        
        return log_data
    
    def count_referrals(self, inviter_user_id: UUID) -> int:
        """
        Count unique referrals for a user.
        Replaces Count Referrals logic from n8n.
        
        Args:
            inviter_user_id: User UUID of inviter
        
        Returns:
            Number of unique referrals
        """
        inviter = self.db.query(User).filter(
            and_(
                User.id == inviter_user_id,
                User.bot_id == self.bot_id
            )
        ).first()
        
        if not inviter:
            return 0
        
        # Get all referral logs, filter in Python to avoid JSONB query issues
        all_logs = self.db.query(BusinessData).filter(
            and_(
                BusinessData.bot_id == self.bot_id,
                BusinessData.data_type == 'log'
            )
        ).all()
        
        # Filter in Python - match by inviter_external_id
        referral_logs = []
        for log in all_logs:
            data = log.data or {}
            # Check if this log is for this inviter
            # is_referral can be boolean True or string 'true'
            is_referral_value = data.get('is_referral')
            is_valid_referral = (is_referral_value == True or 
                                (isinstance(is_referral_value, str) and is_referral_value.lower() == 'true'))
            
            if (data.get('inviter_external_id') == inviter.external_id and
                is_valid_referral):
                referral_logs.append(log)
        
        # Get unique referred users by ref_parameter
        unique_refs = set()
        for log in referral_logs:
            ref_param = log.data.get('ref_parameter', '')
            if ref_param and ref_param.upper() != 'NO_REF':
                unique_refs.add(ref_param)
        
        return len(unique_refs)
    
    def update_total_invited(self, user_id: UUID) -> User:
        """
        Update user's total invited count.
        Replaces Update Total Invited Google Sheets operation.
        
        Args:
            user_id: User UUID
        
        Returns:
            Updated User object
        """
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.bot_id == self.bot_id
            )
        ).first()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        total_invited = self.count_referrals(user_id)
        
        if not user.custom_data:
            user.custom_data = {}
        
        user.custom_data['total_invited'] = total_invited
        
        # Auto-unlock TOP if user invited 5+ friends and TOP is still locked
        if total_invited >= self.REQUIRED_INVITES:
            current_top_status = user.custom_data.get('top_status', 'locked')
            if current_top_status != 'open':
                # Unlock TOP via invites - update directly to avoid circular import
                user.custom_data['top_status'] = 'open'
                user.custom_data['top_unlock_method'] = 'invites'
        
        # Mark JSONB field as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, 'custom_data')
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_total_invited(self, user_id: UUID) -> int:
        """Get user's total invited count"""
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.bot_id == self.bot_id
            )
        ).first()
        
        if not user:
            return 0
        
        if user.custom_data:
            return user.custom_data.get('total_invited', 0)
        
        return 0
    
    def check_top_unlock_eligibility(self, user_id: UUID) -> Tuple[bool, int]:
        """
        Check if user can unlock TOP.
        
        Args:
            user_id: User UUID
        
        Returns:
            Tuple of (can_unlock, invites_needed)
        """
        # Single query instead of duplicate
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.bot_id == self.bot_id
            )
        ).first()
        
        if not user:
            return False, self.REQUIRED_INVITES
        
        # Check if already unlocked
        if user.custom_data:
            if user.custom_data.get('top_status') == 'open':
                return True, 0
        
        # Check invites
        total_invited = self.get_total_invited(user_id)
        
        if total_invited >= self.REQUIRED_INVITES:
            return True, 0
        
        invites_needed = self.REQUIRED_INVITES - total_invited
        return False, invites_needed

