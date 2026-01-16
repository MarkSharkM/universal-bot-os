-- Update share_referral translations to use unified message
-- Remove old "7% RevShare" text and use new unified message

-- Ukrainian
INSERT INTO translations (key, lang, text, created_at, updated_at)
VALUES ('share_text_pro', 'uk', '🚀 Долучайся до EarnHubAggregatorBot — отримуй зірки за активність!', NOW(), NOW())
ON CONFLICT (key, lang) DO UPDATE SET text = EXCLUDED.text, updated_at = NOW();

-- English  
INSERT INTO translations (key, lang, text, created_at, updated_at)
VALUES ('share_text_pro', 'en', '🚀 Join EarnHubAggregatorBot — earn Stars for your activity!', NOW(), NOW())
ON CONFLICT (key, lang) DO UPDATE SET text = EXCLUDED.text, updated_at = NOW();

-- Russian
INSERT INTO translations (key, lang, text, created_at, updated_at)
VALUES ('share_text_pro', 'ru', '🚀 Присоединяйся к EarnHubAggregatorBot — получай звёзды за активность!', NOW(), NOW())
ON CONFLICT (key, lang) DO UPDATE SET text = EXCLUDED.text, updated_at = NOW();

-- German
INSERT INTO translations (key, lang, text, created_at, updated_at)
VALUES ('share_text_pro', 'de', '🚀 Tritt EarnHubAggregatorBot bei — sammle Stars für deine Aktivität!', NOW(), NOW())
ON CONFLICT (key, lang) DO UPDATE SET text = EXCLUDED.text, updated_at = NOW();

-- Spanish
INSERT INTO translations (key, lang, text, created_at, updated_at)
VALUES ('share_text_pro', 'es', '🚀 ¡Únete a EarnHubAggregatorBot — gana Stars por tu actividad!', NOW(), NOW())
ON CONFLICT (key, lang) DO UPDATE SET text = EXCLUDED.text, updated_at = NOW();

-- Also update share_referral to remove old "7% RevShare" text
-- Ukrainian
UPDATE translations 
SET text = '🚀 Долучайся до EarnHubAggregatorBot — отримуй зірки за активність!', updated_at = NOW()
WHERE key = 'share_referral' AND lang = 'uk';

-- English
UPDATE translations 
SET text = '🚀 Join EarnHubAggregatorBot — earn Stars for your activity!', updated_at = NOW()
WHERE key = 'share_referral' AND lang = 'en';

-- Russian
UPDATE translations 
SET text = '🚀 Присоединяйся к EarnHubAggregatorBot — получай звёзды за активность!', updated_at = NOW()
WHERE key = 'share_referral' AND lang = 'ru';

-- German
UPDATE translations 
SET text = '🚀 Tritt EarnHubAggregatorBot bei — sammle Stars für deine Aktivität!', updated_at = NOW()
WHERE key = 'share_referral' AND lang = 'de';

-- Spanish
UPDATE translations 
SET text = '🚀 ¡Únete a EarnHubAggregatorBot — gana Stars por tu actividad!', updated_at = NOW()
WHERE key = 'share_referral' AND lang = 'es';
