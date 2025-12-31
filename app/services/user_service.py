"""
User Service - Multi-tenant user management
Handles user creation, wallet management, referral tracking
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID

from app.models.user import User
from app.models.business_data import BusinessData


class UserService:
    """
    Multi-tenant user service.
    All operations are scoped by bot_id for isolation.
    """
    
    def __init__(self, db: Session, bot_id: UUID):
        self.db = db
        self.bot_id = bot_id
    
    def get_or_create_user(
        self,
        external_id: str,
        platform: str = "telegram",
        language_code: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """
        Get existing user or create new one.
        
        Args:
            external_id: Platform-specific user ID (e.g., Telegram chat_id)
            platform: Platform name (telegram, web, etc.)
            language_code: User's language preference
            username: Username
            first_name: First name
            last_name: Last name
        
        Returns:
            User object
        """
        user = self.db.query(User).filter(
            and_(
                User.bot_id == self.bot_id,
                User.external_id == str(external_id),
                User.platform == platform
            )
        ).first()
        
        if not user:
            user = User(
                bot_id=self.bot_id,
                external_id=str(external_id),
                platform=platform,
                language_code=language_code or 'uk',
                custom_data={
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        else:
            # Update custom_data if provided
            if username or first_name or last_name:
                if not user.custom_data:
                    user.custom_data = {}
                if username:
                    user.custom_data['username'] = username
                if first_name:
                    user.custom_data['first_name'] = first_name
                if last_name:
                    user.custom_data['last_name'] = last_name
                if language_code:
                    user.language_code = language_code
                self.db.commit()
        
        return user
    
    def get_user(self, external_id: str, platform: str = "telegram") -> Optional[User]:
        """Get user by external_id and platform"""
        return self.db.query(User).filter(
            and_(
                User.bot_id == self.bot_id,
                User.external_id == str(external_id),
                User.platform == platform
            )
        ).first()
    
    def update_wallet(
        self,
        user_id: UUID,
        wallet_address: str
    ) -> User:
        """
        Update user's TON wallet address.
        Stores in business_data with data_type='wallet'.
        
        Args:
            user_id: User UUID
            wallet_address: TON wallet address
        
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
        
        # Store wallet in business_data
        wallet_data = BusinessData(
            bot_id=self.bot_id,
            data_type='wallet',
            data={
                'user_id': str(user_id),
                'wallet_address': wallet_address,
                'external_id': user.external_id,
            }
        )
        self.db.add(wallet_data)
        
        # Also store in user custom_data for quick access
        if not user.custom_data:
            user.custom_data = {}
        user.custom_data['wallet_address'] = wallet_address
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_wallet(self, user_id: UUID) -> Optional[str]:
        """Get user's wallet address"""
        # First check user custom_data (fastest, no DB query needed if user already loaded)
        user = self.get_user_by_id(user_id)
        if user and user.custom_data:
            wallet = user.custom_data.get('wallet_address')
            if wallet:
                return wallet
        
        # If not in custom_data, check business_data (wallet records)
        # Optimized: query with JSONB filter to avoid loading all wallets
        from sqlalchemy import cast, String
        from sqlalchemy.dialects.postgresql import JSONB
        
        wallet_data = self.db.query(BusinessData).filter(
            and_(
                BusinessData.bot_id == self.bot_id,
                BusinessData.data_type == 'wallet',
                cast(BusinessData.data['user_id'], String) == str(user_id)
            )
        ).order_by(BusinessData.created_at.desc()).first()
        
        if wallet_data and wallet_data.data:
            return wallet_data.data.get('wallet_address')
        
        return None
    
    def update_top_status(
        self,
        user_id: UUID,
        status: str,  # 'locked' or 'open'
        unlock_method: Optional[str] = None  # 'payment' or 'invites'
    ) -> User:
        """
        Update user's TOP access status.
        
        Args:
            user_id: User UUID
            status: 'locked' or 'open'
            unlock_method: 'payment' (paid 1⭐) or 'invites' (invited 5+ friends)
        """
        from sqlalchemy.orm.attributes import flag_modified
        
        user = self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.bot_id == self.bot_id
            )
        ).first()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if not user.custom_data:
            user.custom_data = {}
        
        user.custom_data['top_status'] = status
        if unlock_method:
            user.custom_data['top_unlock_method'] = unlock_method
        flag_modified(user, 'custom_data')  # Mark JSONB field as modified
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def get_top_status(self, user_id: UUID) -> str:
        """Get user's TOP status (locked/open)"""
        user = self.get_user_by_id(user_id)
        if not user:
            return 'locked'
        
        return user.custom_data.get('top_status', 'locked') if user.custom_data else 'locked'
    
    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by UUID"""
        return self.db.query(User).filter(
            and_(
                User.id == user_id,
                User.bot_id == self.bot_id
            )
        ).first()
    
    def update_balance(
        self,
        user_id: UUID,
        amount: float,
        operation: str = "add"  # 'add' or 'set'
    ) -> User:
        """Update user balance"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if operation == "add":
            user.balance += amount
        else:
            user.balance = amount
        
        self.db.commit()
        self.db.refresh(user)
        
        return user

