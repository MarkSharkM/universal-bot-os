
import asyncio
from unittest.mock import MagicMock
from app.services.translation_service import TranslationService

async def test_translation():
    mock_db = MagicMock()
    # Mock execute result to return None (simulate no DB translation found)
    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        return mock_result
    mock_db.execute = mock_execute
    
    service = TranslationService(mock_db)
    
    # Test UK
    text_uk = await service.get_translation('welcome_message', 'uk')
    print(f"UK Translation: {text_uk[:50]}...")
    
    # Test EN
    text_en = await service.get_translation('welcome_message', 'en')
    print(f"EN Translation: {text_en[:50]}...")
    
    # Test Fallback sanity
    text_missing = await service.get_translation('missing_key_xyz', 'en')
    print(f"Missing Key: {text_missing}")

if __name__ == "__main__":
    asyncio.run(test_translation())
