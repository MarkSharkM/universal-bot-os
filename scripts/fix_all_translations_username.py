#!/usr/bin/env python3
"""
Fix all translations with hardcoded username - replace with {{bot_username}} placeholder
Updates via API (no DB access needed)
"""
import httpx
from urllib.parse import quote
import sys

BASE_URL = "https://api-production-57e8.up.railway.app/api/v1/admin"

# Translations that need to be fixed
TRANSLATIONS_TO_FIX = {
    # earnings_block2_how_it_works
    'earnings_block2_how_it_works': {
        'ru': 'Когда люди заходят по твоей ссылке, запускают {{bot_username}} и покупают ⭐ — Telegram делится с тобой доходом (~7%).',
        'de': 'Wenn Leute über deinen Link kommen, {{bot_username}} starten und ⭐ kaufen, teilt Telegram ~7 % der Einnahmen mit dir.',
        'es': 'Cuando la gente entra con tu enlace, inicia {{bot_username}} y compra ⭐, Telegram comparte contigo ~7 % de los ingresos.'
    },
    # earnings_7_instructions
    'earnings_7_instructions': {
        'ru': '💸 Как включить 7% (один раз и навсегда):\n\n1️⃣ Открой профиль бота @{{bot_username}} (нажми на название бота вверху)\n2️⃣ «Партнёрская программа»\n3️⃣ «Присоединиться»\n→ 7% активируются навсегда',
        'de': '💸 So aktivierst du 7 % (einmal, für immer):\n\n1️⃣ Öffne das Bot-Profil @{{bot_username}} (tippe oben auf den Bot-Namen)\n2️⃣ „Partnerprogramm"\n3️⃣ „Beitreten"\n→ 7 % bleiben dauerhaft aktiv',
        'es': '💸 Cómo activar el 7 % (una vez y para siempre):\n\n1️⃣ Abre el perfil del bot @{{bot_username}} (toca el nombre del bot arriba)\n2️⃣ «Programa de afiliados»\n3️⃣ «Unirse»\n→ El 7 % quedará activo para siempre'
    },
    # info_main
    'info_main': {
        'de': '👋 Das ist {{bot_username}} — ein Aggregator der profitabelsten Telegram-Mini-Apps und Bots, um Stars zu sammeln.\n\n🎯 Was wir tun:\n• Wir sammeln die besten Mini-Apps und Bots\n• Wir zeigen dir, wie du Stars verdienst\n• Wir helfen dir, deine Belohnungen zu maximieren\n\n🚀 Starte jetzt und sammle Stars!',
        'es': '👋 Este es {{bot_username}} — un agregador de las mini apps y bots de Telegram más rentables para ganar Stars.\n\n🎯 Lo que hacemos:\n• Recopilamos las mejores mini apps y bots\n• Te mostramos cómo ganar Stars\n• Te ayudamos a maximizar tus recompensas\n\n🚀 ¡Comienza ahora y gana Stars!'
    },
    # share_referral
    'share_referral': {
        'de': '🚀 Tritt {{bot_username}} bei — sammle Stars für deine Aktivität!\nHier ist dein Empfehlungslink:\n[[referralLink]]',
        'es': '🚀 Únete a {{bot_username}} — ¡gana Stars por tu actividad!\nAquí tienes tu enlace de referido:\n[[referralLink]]'
    },
    # earnings_enable_7_steps
    'earnings_enable_7_steps': {
        'de': '1️⃣ Öffne @{{bot_username}}\n2️⃣ „Partnerprogramm"\n3️⃣ „Beitreten"\n→ 7 % bleiben dauerhaft aktiv',
        'es': '1️⃣ Abre @{{bot_username}}\n2️⃣ «Programa de afiliados»\n3️⃣ «Unirse»\n→ El 7 % quedará activo para siempre'
    }
}

def update_translation(key: str, lang: str, text: str) -> bool:
    """Update translation via API"""
    try:
        url = f"{BASE_URL}/translations/{key}/{lang}?text={quote(text)}"
        r = httpx.put(url, timeout=10)
        if r.status_code == 200:
            print(f"✅ {key} ({lang})")
            return True
        else:
            print(f"❌ {key} ({lang}): {r.status_code} - {r.text[:100]}")
            return False
    except Exception as e:
        print(f"❌ {key} ({lang}): {e}")
        return False

def main():
    print("🔧 Оновлення перекладів з hardcoded username...")
    print()
    
    total = 0
    success = 0
    
    for key, langs in TRANSLATIONS_TO_FIX.items():
        for lang, text in langs.items():
            total += 1
            if update_translation(key, lang, text):
                success += 1
    
    print()
    print(f"📊 Результат: {success}/{total} оновлено")
    
    if success == total:
        print("✅ Всі переклади оновлено!")
        return 0
    else:
        print(f"⚠️ {total - success} перекладів не оновлено")
        return 1

if __name__ == "__main__":
    sys.exit(main())
