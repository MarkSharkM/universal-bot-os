"""
Translation Service - Multi-tenant i18n support
Supports 5+ languages (uk, en, ru, de, es) with fallback logic
Supports per-bot custom translations via bot.config
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID

from app.models.translation import Translation
from app.models.bot import Bot
from app.core.database import get_db


class TranslationService:
    """
    Multi-tenant translation service.
    Works with bot_id for isolation, supports language detection and fallback.
    Supports per-bot custom translations via bot.config.translations.custom
    """
    
    SUPPORTED_LANGUAGES = ['uk', 'en', 'ru', 'de', 'es']
    FALLBACK_LANG = 'en'
    DEFAULT_LANG = 'uk'
    
    def __init__(self, db: Session, bot_id: Optional[UUID] = None):
        self.db = db
        self.bot_id = bot_id
        self._bot_config: Optional[Dict[str, Any]] = None  # Cache bot config
    
    def detect_language(
        self,
        language_code: Optional[str] = None,
        user_lang: Optional[str] = None
    ) -> str:
        """
        Detect and normalize language code.
        
        Args:
            language_code: Full language code from Telegram (e.g., 'en-US', 'uk-UA')
            user_lang: User's saved language preference
        
        Returns:
            Normalized 2-letter language code (uk, en, ru, de, es)
        """
        # Priority: user_lang > language_code > default
        raw = user_lang or language_code or ''
        
        # Normalize to 2-letter code
        base_lang = raw.split('-')[0].lower().strip() if raw else ''
        
        # Map variations
        lang_map = {
            'ua': 'uk',
            'uk': 'uk',
            'ru': 'ru',
            'en': 'en',
            'de': 'de',
            'es': 'es',
        }
        
        normalized = lang_map.get(base_lang, self.FALLBACK_LANG)
        
        # Ensure it's supported
        if normalized not in self.SUPPORTED_LANGUAGES:
            return self.FALLBACK_LANG
        
        return normalized
    
    def _get_bot_config(self) -> Dict[str, Any]:
        """
        Get bot configuration (lazy load).
        
        Returns:
            Bot config dictionary
        """
        if self._bot_config is None:
            if self.bot_id:
                bot = self.db.query(Bot).filter(Bot.id == self.bot_id).first()
                if bot:
                    self._bot_config = bot.config or {}
                else:
                    self._bot_config = {}
            else:
                self._bot_config = {}
        return self._bot_config
    
    def _get_custom_translation(self, key: str, lang: str) -> Optional[str]:
        """
        Get custom translation from bot.config if available.
        
        Args:
            key: Translation key
            lang: Language code
        
        Returns:
            Custom translation text or None
        """
        if not self.bot_id:
            return None
        
        config = self._get_bot_config()
        translations_config = config.get('translations', {})
        
        # Check if custom translations are enabled
        use_custom = translations_config.get('use_custom', False)
        if not use_custom:
            return None
        
        # Get custom translations
        custom = translations_config.get('custom', {})
        lang_translations = custom.get(lang, {})
        
        # Return custom translation if exists
        if key in lang_translations:
            return lang_translations[key]
        
        return None
    
    def get_translation(
        self,
        key: str,
        lang: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get translation by key with variable substitution.
        Priority: bot.config.translations.custom > database translations
        
        Args:
            key: Translation key (e.g., 'welcome', 'wallet_saved')
            lang: Language code (defaults to FALLBACK_LANG)
            variables: Variables for substitution (e.g., {'wallet': 'EQ123...'})
        
        Returns:
            Translated text with variables substituted
        """
        lang = lang or self.FALLBACK_LANG
        variables = variables or {}
        
        # First, try custom translation from bot.config
        custom_text = self._get_custom_translation(key, lang)
        if custom_text:
            text = custom_text
        else:
            # Fallback to database translations
            # Try requested language
            translation = self.db.query(Translation).filter(
                and_(
                    Translation.key == key,
                    Translation.lang == lang
                )
            ).first()
            
            # Fallback chain: requested -> en -> uk
            if not translation:
                translation = self.db.query(Translation).filter(
                    and_(
                        Translation.key == key,
                        Translation.lang == self.FALLBACK_LANG
                    )
                ).first()
            
            if not translation:
                translation = self.db.query(Translation).filter(
                    and_(
                        Translation.key == key,
                        Translation.lang == self.DEFAULT_LANG
                    )
                ).first()
            
            # If still not found, return key
            if not translation:
                return key
            
            text = translation.text
        
        # Substitute variables {{variable}}
        for var_key, var_value in variables.items():
            text = text.replace(f'{{{{{var_key}}}}}', str(var_value))
        
        # Also support [[variable]] format (legacy from n8n)
        for var_key, var_value in variables.items():
            text = text.replace(f'[[{var_key}]]', str(var_value))
        
        return text
    
    def get_all_translations(
        self,
        lang: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get all translations for a language.
        Useful for bulk operations (like n8n Translator node).
        
        Args:
            lang: Language code
        
        Returns:
            Dictionary of {key: translated_text}
        """
        lang = lang or self.FALLBACK_LANG
        
        translations = self.db.query(Translation).filter(
            Translation.lang == lang
        ).all()
        
        return {t.key: t.text for t in translations}
    
    def translate_message(
        self,
        message_key: str,
        language_code: Optional[str] = None,
        user_lang: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        High-level method: detect language and get translation.
        
        Args:
            message_key: Translation key
            language_code: Telegram language code
            user_lang: User's saved language
            variables: Variables for substitution
        
        Returns:
            Translated message
        """
        lang = self.detect_language(language_code, user_lang)
        return self.get_translation(message_key, lang, variables)

