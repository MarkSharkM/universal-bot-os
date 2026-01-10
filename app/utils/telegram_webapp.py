"""
Telegram WebApp utilities - validation of initData
"""
import hmac
import hashlib
from urllib.parse import parse_qs, unquote
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def validate_telegram_init_data(init_data: str, bot_token: str) -> bool:
    """
    Validate Telegram WebApp initData signature.
    
    Telegram sends initData as URL-encoded query string with 'hash' parameter.
    The hash is HMAC-SHA256 of all other parameters sorted alphabetically.
    
    Args:
        init_data: Raw initData string from Telegram (URL-encoded)
        bot_token: Bot token for signature verification
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Parse query string
        parsed = parse_qs(init_data, keep_blank_values=True)
        
        # Extract hash
        hash_value = parsed.get('hash', [None])[0]
        if not hash_value:
            logger.warning("No hash in initData")
            return False
        
        # Remove hash from parameters
        data_check_string_parts = []
        for key, value_list in sorted(parsed.items()):
            if key == 'hash':
                continue
            # Each parameter can have multiple values, join them
            for value in value_list:
                data_check_string_parts.append(f"{key}={value}")
        
        data_check_string = "\n".join(data_check_string_parts)
        
        # Create secret key from bot token
        secret_key = hmac.new(
            "WebAppData".encode(),
            bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Calculate HMAC-SHA256
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare hashes (constant-time comparison)
        return hmac.compare_digest(calculated_hash, hash_value)
        
    except Exception as e:
        logger.error(f"Error validating initData: {e}", exc_info=True)
        return False


def parse_init_data(init_data: str) -> Dict[str, Any]:
    """
    Parse Telegram WebApp initData and extract user info.
    
    Args:
        init_data: Raw initData string from Telegram (URL-encoded)
    
    Returns:
        Dictionary with parsed data (user, auth_date, etc.)
    """
    try:
        parsed = parse_qs(init_data, keep_blank_values=True)
        result = {}
        
        # Parse user (JSON string)
        if 'user' in parsed:
            import json
            user_str = parsed['user'][0]
            result['user'] = json.loads(unquote(user_str))
        
        # Parse other fields
        if 'auth_date' in parsed:
            result['auth_date'] = int(parsed['auth_date'][0])
        
        if 'hash' in parsed:
            result['hash'] = parsed['hash'][0]
        
        if 'query_id' in parsed:
            result['query_id'] = parsed['query_id'][0]
            
        if 'start_param' in parsed:
            result['start_param'] = parsed['start_param'][0]
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing initData: {e}", exc_info=True)
        return {}


def get_start_param_from_init_data(init_data: str) -> Optional[str]:
    """
    Extract start_param from Telegram WebApp initData.
    
    Args:
        init_data: Raw initData string from Telegram (URL-encoded)
    
    Returns:
        start_param string, or None if not found
    """
    try:
        parsed = parse_init_data(init_data)
        return parsed.get('start_param')
    except Exception as e:
        logger.error(f"Error extracting start_param from initData: {e}", exc_info=True)
        return None


def get_user_id_from_init_data(init_data: str) -> Optional[str]:
    """
    Extract user_id from Telegram WebApp initData.
    
    Args:
        init_data: Raw initData string from Telegram (URL-encoded)
    
    Returns:
        User ID as string, or None if not found
    """
    try:
        parsed = parse_init_data(init_data)
        user = parsed.get('user', {})
        return str(user.get('id')) if user else None
    except Exception as e:
        logger.error(f"Error extracting user_id from initData: {e}", exc_info=True)
        return None

