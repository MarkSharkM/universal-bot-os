"""
AI Service - Multi-tenant AI integration
Supports OpenAI and Anthropic with user language awareness
"""
from typing import Optional, Dict, Any, List, Union
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.services.translation_service import TranslationService
from app.models.message import Message
from app.models.bot import Bot

logger = logging.getLogger(__name__)


class AIService:
    """
    Multi-tenant AI service.
    Handles AI interactions with language awareness and context management.
    """
    
    def __init__(
        self,
        db: Session,
        bot_id: UUID,
        translation_service: TranslationService
    ):
        self.db = db
        self.bot_id = bot_id
        self.translation_service = translation_service
    
    def get_ai_config(self) -> Dict[str, Any]:
        """
        Get AI configuration from bot config.
        Falls back to environment variables if not set in bot config.
        
        Returns:
            Dictionary with AI settings (provider, model, api_key, etc.)
        """
        from app.core.config import settings
        
        bot = self.db.query(Bot).filter(Bot.id == self.bot_id).first()
        if not bot:
            raise ValueError(f"Bot {self.bot_id} not found")
        
        ai_config = bot.config.get('ai', {})
        
        # API key: спочатку з bot config, потім fallback на env vars
        api_key = ai_config.get('api_key', '')
        if not api_key:
            # Fallback на глобальні змінні оточення (для сумісності)
            provider = ai_config.get('provider', 'openai')
            if provider == 'anthropic':
                api_key = settings.ANTHROPIC_API_KEY or ''
            else:
                api_key = settings.OPENAI_API_KEY or ''
        
        return {
            'provider': ai_config.get('provider', 'openai'),  # openai, anthropic
            'model': ai_config.get('model', 'gpt-4o-mini'),
            'api_key': api_key,  # З bot config або env vars
            'temperature': ai_config.get('temperature', 0.7),
            'max_tokens': ai_config.get('max_tokens', 2000),
            'system_prompt': ai_config.get('system_prompt', ''),
            'language': ai_config.get('language', 'uk'),
        }
    
    def build_system_prompt(
        self,
        user_lang: str,
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        Build system prompt with language awareness.
        
        Args:
            user_lang: User's language code
            custom_prompt: Custom prompt from bot config
        
        Returns:
            System prompt string
        """
        if custom_prompt:
            return custom_prompt
        
        # Default system prompt based on language
        lang_prompts = {
            'uk': """Ти корисний асистент Telegram бота. Відповідай українською мовою, бути дружнім та професійним.""",
            'en': """You are a helpful Telegram bot assistant. Respond in English, be friendly and professional.""",
            'ru': """Ты полезный ассистент Telegram бота. Отвечай на русском языке, будь дружелюбным и профессиональным.""",
            'de': """Du bist ein hilfreicher Telegram-Bot-Assistent. Antworte auf Deutsch, sei freundlich und professionell.""",
            'es': """Eres un asistente útil del bot de Telegram. Responde en español, sé amigable y profesional.""",
        }
        
        lang = self.translation_service.detect_language(user_lang)
        return lang_prompts.get(lang, lang_prompts['en'])
    
    def get_message_history(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get message history for AI context.
        
        Args:
            user_id: User UUID
            limit: Number of recent messages to retrieve
        
        Returns:
            List of messages in OpenAI format
        """
        messages = self.db.query(Message).filter(
            Message.user_id == user_id,
            Message.bot_id == self.bot_id
        ).order_by(Message.timestamp.desc()).limit(limit).all()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))
        
        # Format for OpenAI
        formatted = []
        for msg in messages:
            formatted.append({
                'role': msg.role,  # user, assistant, system
                'content': msg.content
            })
        
        return formatted
    
    async def generate_response(
        self,
        user_id: UUID,
        user_message: str,
        user_lang: Optional[str] = None,
        image_url: Optional[Union[str, List[str]]] = None
    ) -> str:
        """
        Generate AI response with context and language awareness.
        Supports Vision (image analysis) if image_url is provided.
        
        Args:
            user_id: User UUID
            user_message: User's message
            user_lang: User's language code
            image_url: Optional URL(s) to image(s) for analysis (str or list of str)
        
        Returns:
            AI-generated response
        """
        # Get AI config
        ai_config = self.get_ai_config()
        provider = ai_config['provider']
        
        # Get user language
        if not user_lang:
            user = self.db.query(User).filter(
                User.id == user_id,
                User.bot_id == self.bot_id
            ).first()
            user_lang = user.language_code if user else 'uk'
        
        lang = self.translation_service.detect_language(user_lang)
        
        # Build system prompt
        system_prompt = self.build_system_prompt(
            lang,
            ai_config.get('system_prompt')
        )
        
        # Get message history (skip for Vision requests to keep context clean/cheap?)
        # For now, include history unless it's a vision request which is usually standalone
        history = self.get_message_history(user_id) if not image_url else []
        
        # Build new user message content
        if image_url:
            # Support both single URL (str) and multiple URLs (list)
            if isinstance(image_url, list):
                user_content = [{"type": "text", "text": user_message}]
                for url in image_url:
                    user_content.append({"type": "image_url", "image_url": {"url": url}})
            else:
                user_content = [
                    {"type": "text", "text": user_message},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
        else:
            user_content = user_message
        
        # Build messages for API
        messages = [
            {'role': 'system', 'content': system_prompt}
        ] + history + [
            {'role': 'user', 'content': user_content}
        ]
        
        # Call AI provider
        if provider == 'openai':
            response = await self._call_openai(messages, ai_config)
        elif provider == 'anthropic':
            response = await self._call_anthropic(messages, ai_config)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
        
        # Save messages to history
        # For vision, save a text representation
        db_content = user_message
        if image_url:
            db_content += f" [Image: {image_url}]"
            
        self._save_message(user_id, 'user', db_content)
        self._save_message(user_id, 'assistant', response)
        
        return response
    
    async def _call_openai(
        self,
        messages: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> str:
        """Call OpenAI API"""
        try:
            import openai
            
            client = openai.AsyncOpenAI(api_key=config['api_key'])
            
            # OpenAI requires a slightly different format for system prompt if using O1 or some models,
            # but standard GPT-4/o works with system messages.
            # Structured Outputs (response_format) is supported in newer models.
            
            # Check if we should enforce JSON object
            kwargs = {}
            if "json" in config.get('system_prompt', '').lower():
                kwargs['response_format'] = {"type": "json_object"}
            
            response = await client.chat.completions.create(
                model=config['model'],
                messages=messages,
                temperature=config['temperature'],
                max_tokens=config['max_tokens'],
                **kwargs
            )
            
            return response.choices[0].message.content.strip()
            
        except ImportError:
            logger.error("OpenAI library not installed. Install with: pip install openai")
            raise
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _call_anthropic(
        self,
        messages: List[Dict[str, str]],
        config: Dict[str, Any]
    ) -> str:
        """Call Anthropic API"""
        try:
            from anthropic import AsyncAnthropic
            
            client = AsyncAnthropic(api_key=config['api_key'])
            
            # Anthropic uses different message format
            system_message = messages[0]['content'] if messages[0]['role'] == 'system' else ''
            conversation = [m for m in messages if m['role'] != 'system']
            
            response = await client.messages.create(
                model=config['model'],
                max_tokens=config['max_tokens'],
                temperature=config['temperature'],
                system=system_message,
                messages=conversation
            )
            
            return response.content[0].text.strip()
            
        except ImportError:
            logger.error("Anthropic library not installed. Install with: pip install anthropic")
            raise
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def _save_message(
        self,
        user_id: UUID,
        role: str,
        content: str
    ):
        """Save message to history"""
        message = Message(
            user_id=user_id,
            bot_id=self.bot_id,
            role=role,
            content=content
        )
        self.db.add(message)
        self.db.commit()
    
    def update_ai_config(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Update AI configuration for bot.
        For admin use.
        
        Args:
            provider: AI provider (openai/anthropic)
            model: Model name
            api_key: API key
            temperature: Temperature setting
            system_prompt: Custom system prompt
        """
        bot = self.db.query(Bot).filter(Bot.id == self.bot_id).first()
        if not bot:
            raise ValueError(f"Bot {self.bot_id} not found")
        
        if 'ai' not in bot.config:
            bot.config['ai'] = {}
        
        ai_config = bot.config['ai']
        
        if provider:
            ai_config['provider'] = provider
        if model:
            ai_config['model'] = model
        if api_key:
            ai_config['api_key'] = api_key
        if temperature is not None:
            ai_config['temperature'] = temperature
        if system_prompt:
            ai_config['system_prompt'] = system_prompt
        
        self.db.commit()


# Import User here to avoid circular import
from app.models.user import User

