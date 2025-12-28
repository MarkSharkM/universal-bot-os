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
        Format: _tgr_{userId}
        
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
        
        return f"_tgr_{user.external_id}"
    
    def generate_referral_link(
        self,
        user_id: UUID,
        bot_username: Optional[str] = None
    ) -> str:
        """
        Generate referral link for user.
        
        Args:
            user_id: User UUID
            bot_username: Bot username (e.g., 'HubAggregatorBot')
        
        Returns:
            Full referral URL
        """
        tag = self.generate_referral_tag(user_id)
        bot_username = bot_username or "HubAggregatorBot"
        
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
        
        # Special case: GPT Store traffic
        if ref_param.lower() in ['_tgr_gptstore', 'tgr_gptstore']:
            return False, None, 'gptstore'
        
        # Validate format: _tgr_{userId} or tgr_{userId}
        import re
        pattern = r'^_?tgr_([a-z0-9-]+)$'
        match = re.match(pattern, ref_param, re.IGNORECASE)
        
        if not match:
            return False, None, None
        
        inviter_external_id = match.group(1)
        return True, inviter_external_id, ref_param
    
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
        
        # Get all referral logs for this inviter
        referral_logs = self.db.query(BusinessData).filter(
            and_(
                BusinessData.bot_id == self.bot_id,
                BusinessData.data_type == 'log',
                BusinessData.data['inviter_external_id'].astext == inviter.external_id,
                BusinessData.data['is_referral'].astext == 'true'
            )
        ).all()
        
        # Get unique referred users
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
        
        if not user.metadata:
            user.metadata = {}
        
        user.metadata['total_invited'] = total_invited
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
        
        if user.metadata:
            return user.metadata.get('total_invited', 0)
        
        return 0
    
    def check_top_unlock_eligibility(self, user_id: UUID) -> Tuple[bool, int]:
        """
        Check if user can unlock TOP.
        
        Args:
            user_id: User UUID
        
        Returns:
            Tuple of (can_unlock, invites_needed)
        """
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.bot_id == self.bot_id
            )
        ).first()
        
        if not user:
            return False, self.REQUIRED_INVITES
        
        # Check if already unlocked
        top_status = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.bot_id == self.bot_id
            )
        ).first()
        
        if top_status and top_status.metadata:
            if top_status.metadata.get('top_status') == 'open':
                return True, 0
        
        # Check invites
        total_invited = self.get_total_invited(user_id)
        
        if total_invited >= self.REQUIRED_INVITES:
            return True, 0
        
        invites_needed = self.REQUIRED_INVITES - total_invited
        return False, invites_needed

