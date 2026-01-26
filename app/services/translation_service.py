"""
Translation Service - Multi-tenant i18n support
Supports 5+ languages (uk, en, ru, de, es) with fallback logic
Supports per-bot custom translations via bot.config
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
import logging

from app.models.translation import Translation
from app.models.bot import Bot
from app.core.database import get_db
from app.core.redis import cache, cached

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Multi-tenant translation service.
    Works with bot_id for isolation, supports language detection and fallback.
    Supports per-bot custom translations via bot.config.translations.custom
    """
    
    SUPPORTED_LANGUAGES = ['uk', 'en', 'ru', 'de', 'es']
    FALLBACK_LANG = 'en'
    DEFAULT_LANG = 'en'
    
    # Global UI Defaults (Fallback if not in DB or bot.config)
    GLOBAL_UI_DEFAULTS = {
        'uk': {
            'nav_home': 'Головна',
            'nav_partners': 'Партнери',
            'nav_top': 'ТОП',
            'friends': 'Друзі',
            'top_activated': 'ТОП ПРОГРАМА АКТИВНА',
            'link_connected': 'Лінка підключена',
            'input_link_placeholder': 'Встав свою 7% лінку тут...',
            'save': 'Зберегти',
            'how_to_get_link': 'Де взяти лінку?',
            'unlock_top_title': 'Розблокувати ТОП статус',
            'unlock_top_subtitle': 'Запроси 5 друзів, щоб розблокувати ексклюзивні винагороди',
            'invited': 'запрошено',
            'goal': 'ЦІЛЬ',
            'invite_earn': 'ЗАПРОШУЙ ТА ЗАРОБЛЯЙ',
            'potential_earnings': 'Твій потенційний заробіток',
            'user_count_1': '1 ЮЗЕР',
            'user_count_10': '10 ЮЗЕРІВ',
            'user_count_100': '100 ЮЗЕРІВ',
            'estimates_disclaimer': 'Оцінки базуються на середній активності залучених користувачів.',
            'estimates_desc': 'Оцінки базуються на середній активності залучених користувачів.',
            'partners_title': 'Партнери',
            'partners_subtitle': 'Перевірені боти та заробіток зірок за дії',
            'top_bots_title': 'ТОП Боти',
            'top_bots_subtitle': 'Отримуй в x3-x7 більше зірок',
            'browse_btn': 'Переглянути',
            'stars_suffix': '+ ЗІРКИ',
            'x7_badge': '⚡ x7',
            'launch_btn': 'Запустити ↗',
            'open_btn': 'Відкрити ↗',
            'estimated_share': '{{percent}}% частка',
            'about_earnhub': 'Про {{platform_name}}',
            'footer_about_text': '{{platform_name}} — це агрегатор реферальних програм, що пропонує бонуси за ріст мережі. Отримуйте вигоду від 7% монетизації Telegram та максимізуйте прибутки через наших партнерських ботів.',
            'footer_disclaimer': 'Відмова від відповідальності: {{platform_name}} не є фінансовою установою.',
            'terms_of_use': 'Умови використання',
            'privacy_policy': 'Політика конфіденційності',
            'support': 'Підтримка',
            'badge_7_path': '7% шлях розпочато',
            'badge_top_member': 'ТОП учасник',
            'badge_super_sharer': 'Супер поширювач',
            'your_earnings': 'Ваш заробіток',
            'program_active': '✅ Програма 7% активна',
            'program_inactive': '❌ Програма 7% неактивна',
            'achievements': 'Досягнення',
            'unlock_top': 'Розблокувати ТОП',
            'to_pro': 'До Pro',
            'to_hub': 'До Hub',
            'max_level': 'Максимальний рівень',
            'started_path': '47 людей почали 7% шлях',
            'top_opened_today': 'ТОП відкривали 19 разів сьогодні',
            'partners_clicked_most': 'Найчастіше клікають партнерів',
            'share_popup_title': 'Поділися лінкою',
            'next_btn': 'Далі',
            'start_btn': 'Почати',
            'enter_wallet_error': 'Введіть адресу гаманця',
            'invalid_wallet_format': 'Невірний формат адреси гаманця',
            'wallet_saved_success': '✅ Гаманець збережено успішно!',
            'wallet_save_error': '❌ Помилка збереження: ',
            'top_locked_title': 'ТОП заблоковано',
            'top_locked_subtitle': 'Запроси ще {{count}} друзів, щоб розблокувати ТОП партнерів або купи доступ.',
            'top_locked_message': "🎯 ТОП боти відкриваються після перших <b>5 запрошень</b>.\n\n💬 Тобі залишилось запросити ще <b>{{needed}}</b> друзів, щоб розблокувати найвигідніші партнерки!\n\n💫 Також ти можеш відкрити TOP миттєво за <b>{{price}}⭐</b>.\n\n👇 Натисни, щоб поділитися посиланням:",
            'btn_unlock_top': 'Розблокувати за {{price}} зірок',
            'top_profits_title': 'ТОП партнери',
            'top_profits_subtitle': 'Найвигідніші пропозиції тижня',
            'no_partners_found': 'Партнерів не знайдено',
            'no_top_bots': 'TOP ботів поки немає',
            'ton_connect_help': 'TON Connect — це офіційний протокол для підключення TON гаманців у Telegram Mini Apps. Він дозволяє безпечно підключати гаманці без передачі приватних ключів.',
            'starter': 'Новачок',
            'pro': 'Профі',
            'hub': 'Хаб',
            'share_button': '🧡 Поділитись лінкою',
            'loading': 'Завантаження...',
            'retry_btn': 'Спробувати ще раз',
            'connect_telegram_wallet': 'Підключити гаманець у Telegram',
            'choose_other_wallet': 'Обрати інший застосунок',
            'view_all_wallets': 'Всі гаманці',
            'wallet_payouts_info': 'Потрібно лише для майбутніх виплат',
            'wallet_no_withdrawals': 'Ніколи не списуємо кошти',
            'how_to_find_address': 'Як знайти адресу гаманця:',
            'instruction_step_1': 'Відкрий свій TON гаманець (Tonkeeper, MyTonWallet, Tonhub)',
            'instruction_step_2': 'Знайди розділ "Receive" або "Отримати"',
            'instruction_step_3': 'Скопіюй адресу (починається з EQ, UQ, kQ або 0Q)',
            'wallet_input_label': 'Адреса TON гаманця:',
            'cancel': 'Скасувати',
            'onboarding_title_1': 'Тут заробляють на дії у Telegram',
            'onboarding_step_1': 'Активуй 7%',
            'onboarding_step_2': 'Поділись лінкою',
            'onboarding_step_3': 'Люди купують → ти отримуєш %',
            'creating_invoice': 'Створюємо рахунок...',
            'top_unlocked': '✅ TOP розблоковано!',
            'payment_cancelled': 'Оплата скасована',
            'payment_error': '❌ Помилка оплати',
            'saving': 'Збереження...',
            'link_copied': '✅ Лінк скопійовано!',
            'copy_failed': 'Помилка копіювання',
            'bot_id_missing': 'Помилка: Bot ID не знайдено',
            'link_missing': 'Реферальна лінка відсутня',
            'copied': '✅ Скопійовано!',
            'share_text_pro': '🚀 Долучайся до {{bot_name}} — отримуй зірки за активність!',
            'share_text_starter': "🚀 Долучайся до {{bot_name}} — отримуй зірки за активність!",
            'activate_7_title': 'Як увімкнути 7% (1 раз назавжди):',
            'activate_7_step_1': '1️⃣ Відкрий @{{username}}',
            'activate_7_step_2': '2️⃣ «Партнерська програма»',
            'activate_7_step_3': "3️⃣ «Під'єднатись»",
            'activate_7_footer': '→ {{percent}}% активуються назавжди',
            'buy_top_fallback_title': 'Розблокувати ТОП',
            'buy_top_fallback_text': "Для розблокування ТОП потрібно:\n• Запросити {{needed}} друзів\n• Або купити доступ за {{price}} ⭐\nДля покупки відкрийте бота та натисніть кнопку \"Розблокувати ТОП\"",
            'buy_top_fallback_text': "Для розблокування ТОП потрібно:\n• Запросити {{needed}} друзів\n• Або купити доступ за {{price}} ⭐\nДля покупки відкрийте бота та натисніть кнопку \"Розблокувати ТОП\"",
            'open_bot': 'Відкрити бота',
            'buy_top_title': 'Розблокувати ТОП',
            'buy_top_description': 'Доступ до ексклюзивних партнерів та x7 заробітку',
            'buy_top_label': '{{price}} зірок',
            
            # --- Frontend Aliases (Fix for v5.0 UI) ---
            'stat_friends': 'Друзі',
            'top_program_active': 'ТОП ПРОГРАМА АКТИВНА',
            'paste_link_placeholder': 'Встав свою 7% лінку тут...',
            'activate_7_note': '⚠️ Важливо: Після підключення натисніть "Launch" в чаті.',
            'where_to_get_link': 'Де взяти лінку?',
            'share_your_link': 'ПОДІЛИТИСЬ ЛІНКОЮ',
            'invited_count': '{{count}} запрошено',
            'goal_text': 'ЦІЛЬ: {{goal}}',
            'unlock_top_status': 'Розблокувати ТОП статус',
            'invite_5_subtitle': 'Запроси 5 друзів, щоб розблокувати ексклюзивні винагороди',
            'invite_and_earn': 'ЗАПРОШУЙ ТА ЗАРОБЛЯЙ',
            'browse': 'Переглянути',
            'partners': 'Партнери',
            'verified_partners_desc': 'Перевірені боти та заробіток зірок за дії',
            'top_bots': 'ТОП Боти',
            'top_bots_desc': 'Отримуй в x3-x7 більше зірок',
            'recommended_title': 'Перевірені Telegram-боти',
            'recommended_subtitle': 'Обери будь-який — запускай та прокачуйся! 💪',
            'wallet_btn': 'Гаманець',
            
            # --- Missing Static Elements (Added for full Index.html coverage) ---
            'trust_item_1': '🟢 Офіційна партнерська програма Telegram',
            'trust_item_2': '🟢 Модель розподілу доходу (до 7%)',
            'trust_item_3': '🟢 Гаманець: опціонально',
            'share_copy_1': 'Твоя лінка працює 24/7',
            'share_copy_2': 'Кожен новий юзер може запускати цей шлях далі',
            'wallet_banner_text': 'Підключи гаманець → зможеш виводити',
            'wallet_banner_btn': 'Підключити',
            'info_title': 'Інформація про бот',
            'wallet_connect_title': 'Підключити TON гаманець',
            'wallet_connect_subtitle': 'Використовуйте Wallet у Telegram або інший застосунок',
            'wallet_modal_copy': 'Потрібно лише для майбутніх виплат\nНіколи не списуємо кошти',
            'share_popup_text': 'Я підʼєднався до партнерської програми Telegram. Це працює автоматично.',
            'close_btn': 'Закрити',
            'saved': 'Збережено',
            'change_link': 'Змінити лінку?',
        },
        'en': {
            'nav_home': 'Home',
            'nav_partners': 'Partners',
            'nav_top': 'TOP',
            'friends': 'Friends',
            'top_activated': 'TOP PROGRAM ACTIVE',
            'link_connected': 'Link Connected',
            'input_link_placeholder': 'Paste your 7% link here...',
            'save': 'Save',
            'how_to_get_link': 'How to get link?',
            'unlock_top_title': 'Unlock TOP Status',
            'unlock_top_subtitle': 'Invite 5 friends to unlock exclusive rewards',
            'invited': 'invited',
            'goal': 'GOAL',
            'invite_earn': 'INVITE & EARN',
            'potential_earnings': 'Your Potential Earnings',
            'user_count_1': '1 USER',
            'user_count_10': '10 USERS',
            'user_count_100': '100 USERS',
            'estimates_disclaimer': 'Estimates based on average active user engagement.',
            'estimates_desc': 'Estimates based on average active user engagement.',
            'partners_title': 'Partners',
            'partners_subtitle': 'Verified Bots & Earn Stars for Actions',
            'top_bots_title': 'TOP Bots',
            'top_bots_subtitle': 'Get x3-x7 More Stars',
            'browse_btn': 'Browse',
            'stars_suffix': '+ STARS',
            'x7_badge': '⚡ x7',
            'launch_btn': 'Launch ↗',
            'open_btn': 'Open ↗',
            'estimated_share': '{{percent}}% share',
            'about_earnhub': 'About {{platform_name}}',
            'footer_about_text': '{{platform_name}} is an aggregator of referral programs, offering bonuses for network growth. Benefit from 7% Telegram monetization and maximize returns through our partner bots.',
            'footer_disclaimer': 'Disclaimer: {{platform_name}} is not a financial institution.',
            'terms_of_use': 'Terms of Use',
            'privacy_policy': 'Privacy Policy',
            'support': 'Support',
            'badge_7_path': '7% Path Started',
            'badge_top_member': 'TOP Member',
            'badge_super_sharer': 'Super Sharer',
            'your_earnings': 'Your Earnings',
            'program_active': '✅ 7% Program Active',
            'program_inactive': '❌ 7% Program Inactive',
            'achievements': 'Achievements',
            'unlock_top': 'Unlock TOP',
            'to_pro': 'To Pro',
            'to_hub': 'To Hub',
            'max_level': 'Max Level',
            'started_path': '47 people started 7% path',
            'top_opened_today': 'TOP opened 19 times today',
            'partners_clicked_most': 'Most clicked partners',
            'share_popup_title': 'Share Link',
            'next_btn': 'Next',
            'start_btn': 'Start',
            'enter_wallet_error': 'Enter wallet address',
            'invalid_wallet_format': 'Invalid wallet address format',
            'wallet_saved_success': '✅ Wallet saved successfully!',
            'wallet_save_error': '❌ Save error: ',
            'top_locked_title': 'TOP Locked',
            'top_locked_subtitle': 'Invite {{count}} more friends to unlock TOP partners or buy access.',
            'top_locked_message': "🎯 TOP bots unlock after your first <b>5 invites</b>.\n\n💬 You still need to invite <b>{{needed}}</b> friends to unlock the most profitable partners!\n\n💫 You can also unlock TOP instantly for <b>{{price}}⭐</b>.\n\n👇 Tap to share your link:",
            'btn_unlock_top': 'Unlock for {{price}} Stars',
            'top_profits_title': 'TOP Partners',
            'top_profits_subtitle': 'Best offers of the week',
            'no_partners_found': 'No partners found',
            'no_top_bots': 'No TOP bots available yet',
            'ton_connect_help': 'TON Connect is the official protocol for connecting TON wallets in Telegram Mini Apps. It allows you to safely connect wallets without sharing private keys.',
            'starter': 'Starter',
            'pro': 'Pro',
            'hub': 'Hub',
            'share_button': '🧡 Share the link',
            'loading': 'Loading...',
            'retry_btn': 'Retry',
            'connect_telegram_wallet': 'Connect Wallet in Telegram',
            'choose_other_wallet': 'Choose other application',
            'view_all_wallets': 'View all wallets',
            'wallet_payouts_info': 'Only needed for future payouts',
            'wallet_no_withdrawals': 'We never withdraw funds',
            'how_to_find_address': 'How to find wallet address:',
            'instruction_step_1': 'Open your TON wallet (Tonkeeper, MyTonWallet, Tonhub)',
            'instruction_step_2': 'Go to "Receive" or "Get" section',
            'instruction_step_3': 'Copy address (starts with EQ, UQ, kQ or 0Q)',
            'wallet_input_label': 'TON Wallet Address:',
            'cancel': 'Cancel',
            'onboarding_title_1': 'Earn from actions in Telegram',
            'onboarding_step_1': 'Activate 7%',
            'onboarding_step_2': 'Share your link',
            'onboarding_step_3': 'People buy → you get %',
            'creating_invoice': 'Creating invoice...',
            'top_unlocked': '✅ TOP unlocked!',
            'payment_cancelled': 'Payment cancelled',
            'payment_error': '❌ Payment error',
            'saving': 'Saving...',
            'link_copied': '✅ Link copied!',
            'copy_failed': 'Copy failed',
            'bot_id_missing': 'Error: Bot ID not found',
            'link_missing': 'Referral link missing',
            'copied': '✅ Copied!',
            'share_text_pro': '🚀 Join {{bot_name}} — earn Stars for your activity!',
            'share_text_starter': "🚀 Join {{bot_name}} — earn Stars for your activity!",
            'activate_7_title': 'How to enable 7% (once forever):',
            'activate_7_step_1': '1️⃣ Open @{{username}}',
            'activate_7_step_2': '2️⃣ "Partner Program"',
            'activate_7_step_3': '3️⃣ "Connect"',
            'activate_7_footer': '→ {{percent}}% active forever',
            'buy_top_fallback_title': 'Unlock TOP',
            'buy_top_fallback_text': "To unlock TOP you need:\n• Invite {{needed}} friends\n• Or buy access for {{price}} ⭐\nTo buy, open the bot and click \"Unlock TOP\" button",
            'buy_top_fallback_text': "To unlock TOP you need:\n• Invite {{needed}} friends\n• Or buy access for {{price}} ⭐\nTo buy, open the bot and click \"Unlock TOP\" button",
            'open_bot': 'Open Bot',
            'buy_top_title': 'Unlock TOP',
            'buy_top_description': 'Access to exclusive partners and x7 earnings',
            'buy_top_label': '{{price}} Stars',

            # --- Frontend Aliases (Fix for v5.0 UI) ---
            'stat_friends': 'Friends',
            'top_program_active': 'TOP PROGRAM ACTIVE',
            'paste_link_placeholder': 'Paste your 7% link here...',
            'activate_7_note': '⚠️ Important: After connecting, tap "Open App" in chat to return here.',
            'where_to_get_link': 'How to get link?',
            'share_your_link': 'SHARE YOUR LINK',
            'invited_count': '{{count}} invited',
            'goal_text': 'GOAL: {{goal}}',
            'unlock_top_status': 'Unlock TOP Status',
            'invite_5_subtitle': 'Invite 5 friends to unlock exclusive rewards',
            'invite_and_earn': 'INVITE & EARN',
            'browse': 'Browse',
            'partners': 'Partners',
            'verified_partners_desc': 'Verified Bots & Earn Stars for Actions',
            'top_bots': 'TOP Bots',
            'top_bots_desc': 'Get x3-x7 More Stars',
            'recommended_title': 'Verified Telegram Bots',
            'recommended_subtitle': 'Pick any — launch & upgrade! 💪',
            'wallet_btn': 'Wallet',

            # --- Missing Static Elements ---
            'trust_item_1': '🟢 Official Telegram Partner Program',
            'trust_item_2': '🟢 Revenue share model (up to 7%)',
            'trust_item_3': '🟢 Wallet: optional',
            'share_copy_1': 'Your link works 24/7',
            'share_copy_2': 'Every new user can launch this path further',
            'wallet_banner_text': 'Connect wallet → enable withdrawals',
            'wallet_banner_btn': 'Connect',
            'info_title': 'Bot Info',
            'wallet_connect_title': 'Connect your TON wallet',
            'wallet_connect_subtitle': 'Use Wallet in Telegram or choose other application',
            'wallet_modal_copy': 'Only needed for future payouts\nWe never withdraw funds',
            'share_popup_text': 'I joined the Telegram partner program. It works automatically.',
            'close_btn': 'Close',
            'saved': 'Saved',
            'change_link': 'Change link?',
        },
        'ru': {
            'nav_home': 'Главная',
            'nav_partners': 'Партнеры',
            'nav_top': 'ТОП',
            'friends': 'Друзья',
            'top_activated': 'ТОП ПРОГРАММА АКТИВНА',
            'link_connected': 'Ссылка подключена',
            'input_link_placeholder': 'Вставь свою 7% ссылку здесь...',
            'save': 'Сохранить',
            'how_to_get_link': 'Где взять ссылку?',
            'unlock_top_title': 'Разблокировать ТОП статус',
            'unlock_top_subtitle': 'Пригласи 5 друзей, чтобы разблокировать эксклюзивные награды',
            'invited': 'приглашено',
            'goal': 'ЦЕЛЬ',
            'invite_earn': 'ПРИГЛАШАЙ И ЗАРАБАТЫВАЙ',
            'potential_earnings': 'Твой потенциальный заработок',
            'user_count_1': '1 ЮЗЕР',
            'user_count_10': '10 ЮЗЕРОВ',
            'user_count_100': '100 ЮЗЕРОВ',
            'estimates_disclaimer': 'Оценки основаны на средней активности привлеченных пользователей.',
            'estimates_desc': 'Оценки основаны на средней активности привлеченных пользователей.',
            'partners_title': 'Партнеры',
            'partners_subtitle': 'Проверенные боты и заработок звезд за действия',
            'top_bots_title': 'ТОП Боты',
            'top_bots_subtitle': 'Получай в x3-x7 больше звезд',
            'browse_btn': 'Посмотреть',
            'stars_suffix': '+ ЗВЕЗДЫ',
            'x7_badge': '⚡ x7',
            'launch_btn': 'Запустить ↗',
            'open_btn': 'Открыть ↗',
            'estimated_share': '{{percent}}% доля',
            'about_earnhub': 'О {{platform_name}}',
            'footer_about_text': '{{platform_name}} — это агрегатор реферальных программ, предлагающий бонусы за рост сети. Получайте выгоду от 7% монетизации Telegram и максимизируйте прибыль через наших партнерских ботов.',
            'footer_disclaimer': 'Отказ от ответственности: {{platform_name}} не является финансовым учреждением.',
            'terms_of_use': 'Условия использования',
            'privacy_policy': 'Политика конфиденциальности',
            'support': 'Поддержка',
            'badge_7_path': '7% путь начат',
            'badge_top_member': 'ТОП участник',
            'badge_super_sharer': 'Супер распространитель',
            'your_earnings': 'Ваш заработок',
            'program_active': '✅ Программа 7% активна',
            'program_inactive': '❌ Программа 7% неактивна',
            'achievements': 'Достижения',
            'unlock_top': 'Разблокировать ТОП',
            'to_pro': 'До Pro',
            'to_hub': 'До Hub',
            'max_level': 'Максимальный уровень',
            'started_path': '47 человек начали 7% путь',
            'top_opened_today': 'ТОП открывали 19 раз сегодня',
            'partners_clicked_most': 'Чаще всего кликают партнеров',
            'share_popup_title': 'Поделись ссылкой',
            'next_btn': 'Далее',
            'start_btn': 'Начать',
            'enter_wallet_error': 'Введите адрес кошелька',
            'invalid_wallet_format': 'Неверный формат адреса кошелька',
            'wallet_saved_success': '✅ Кошелек сохранен успешно!',
            'wallet_save_error': '❌ Ошибка сохранения: ',
            'top_locked_title': 'ТОП заблокировано',
            'top_locked_subtitle': 'Пригласи еще {{count}} друзей, чтобы разблокировать ТОП партнеров или купи доступ.',
            'top_locked_message': "🎯 ТОП-боты открываются после первых <b>5 приглашений</b>.\n\n💬 Тебе осталось пригласить ещё <b>{{needed}}</b> друзей, чтобы открыть самые выгодные партнёрки!\n\n💫 Также ты можешь открыть TOP мгновенно за <b>{{price}}⭐</b>.\n\n👇 Нажми, чтобы поделиться ссылкой:",
            'btn_unlock_top': 'Разблокировать за {{price}} звезд',
            'top_profits_title': 'ТОП партнеры',
            'top_profits_subtitle': 'Самые выгодные предложения недели',
            'no_partners_found': 'Партнеров не найдено',
            'no_top_bots': 'ТОП ботов пока нет',
            'ton_connect_help': 'TON Connect — это официальный протокол для подключения TON кошельков в Telegram Mini Apps. Он позволяет безопасно подключать кошельки без передачи приватных ключей.',
            'starter': 'Новичок',
            'pro': 'Профи',
            'hub': 'Хаб',
            'share_button': '🧡 Поделиться ссылкой',
            'loading': 'Загрузка...',
            'retry_btn': 'Повторить',
            'connect_telegram_wallet': 'Подключить кошелек в Telegram',
            'choose_other_wallet': 'Выбрать другое приложение',
            'view_all_wallets': 'Все кошельки',
            'wallet_payouts_info': 'Требуется только для будущих выплат',
            'wallet_no_withdrawals': 'Мы никогда не списываем средства',
            'how_to_find_address': 'Как найти адрес кошелька:',
            'instruction_step_1': 'Открой свой TON кошелек (Tonkeeper, MyTonWallet, Tonhub)',
            'instruction_step_2': 'Найди раздел "Receive" или "Получить"',
            'instruction_step_3': 'Скопируй адрес (начинается с EQ, UQ, kQ или 0Q)',
            'wallet_input_label': 'Адрес TON кошелька:',
            'cancel': 'Отмена',
            'onboarding_title_1': 'Здесь зарабатывают на действиях в Telegram',
            'onboarding_step_1': 'Активируй 7%',
            'onboarding_step_2': 'Поделись ссылкой',
            'onboarding_step_3': 'Люди покупают → ты получаешь %',
            'creating_invoice': 'Создаем счет...',
            'top_unlocked': '✅ TOP разблокирован!',
            'payment_cancelled': 'Оплата отменена',
            'payment_error': '❌ Ошибка оплаты',
            'saving': 'Сохранение...',
            'link_copied': '✅ Ссылка скопирована!',
            'copy_failed': 'Ошибка копирования',
            'bot_id_missing': 'Ошибка: Bot ID не найден',
            'link_missing': 'Реферальная ссылка отсутствует',
            'copied': '✅ Скопировано!',
            'share_text_pro': '🚀 Присоединяйся к {{bot_name}} — получай звёзды за активность!',
            'share_text_starter': "🚀 Присоединяйся к {{bot_name}} — получай звёзды за активность!",
            'activate_7_title': 'Как включить 7% (1 раз навсегда):',
            'activate_7_step_1': '1️⃣ Открой @{{username}}',
            'activate_7_step_2': '2️⃣ «Партнерская программа»',
            'activate_7_step_3': '3️⃣ «Подключиться»',
            'activate_7_footer': '→ {{percent}}% активируются навсегда',
            'buy_top_fallback_title': 'Разблокировать ТОП',
            'buy_top_fallback_text': "Для разблокировки ТОП нужно:\n• Пригласить {{needed}} друзей\n• Или купить доступ за {{price}} ⭐\nДля покупки откройте бота и нажмите кнопку \"Разблокировать ТОП\"",
            'buy_top_fallback_text': "Для разблокировки ТОП нужно:\n• Пригласить {{needed}} друзей\n• Или купить доступ за {{price}} ⭐\nДля покупки откройте бота и нажмите кнопку \"Разблокировать ТОП\"",
            'open_bot': 'Открыть бота',
            'buy_top_title': 'Разблокировать ТОП',
            'buy_top_description': 'Доступ к эксклюзивным партнерам и x7 заработку',
            'buy_top_label': '{{price}} звезд',

            # --- Frontend Aliases (Fix for v5.0 UI) ---
            'stat_friends': 'Друзья',
            'top_program_active': 'ТОП ПРОГРАММА АКТИВНА',
            'paste_link_placeholder': 'Вставь свою 7% ссылку здесь...',
            'activate_7_note': '⚠️ Важно: После подключения нажмите "Launch" в чате.',
            'where_to_get_link': 'Где взять ссылку?',
            'share_your_link': 'ПОДЕЛИТЬСЯ ССЫЛКОЙ',
            'invited_count': '{{count}} приглашено',
            'goal_text': 'ЦЕЛЬ: {{goal}}',
            'unlock_top_status': 'Разблокировать ТОП статус',
            'invite_5_subtitle': 'Пригласи 5 друзей, чтобы разблокировать эксклюзивные награды',
            'invite_and_earn': 'ПРИГЛАШАЙ И ЗАРАБАТЫВАЙ',
            'browse': 'Посмотреть',
            'partners': 'Партнеры',
            'verified_partners_desc': 'Проверенные боты и заработок звезд за действия',
            'top_bots': 'ТОП Боты',
            'top_bots_desc': 'Получай в x3-x7 больше звезд',
            'recommended_title': 'Проверенные Telegram-боты',
            'recommended_subtitle': 'Выбирай любой — запускай и прокачивайся! 💪',
            'wallet_btn': 'Кошелек',

            # --- Missing Static Elements ---
            'trust_item_1': '🟢 Официальная партнерская программа Telegram',
            'trust_item_2': '🟢 Модель разделения дохода (до 7%)',
            'trust_item_3': '🟢 Кошелек: опционально',
            'share_copy_1': 'Твоя ссылка работает 24/7',
            'share_copy_2': 'Каждый новый юзер может запускать этот путь дальше',
            'wallet_banner_text': 'Подключи кошелек → сможешь выводить',
            'wallet_banner_btn': 'Подключить',
            'info_title': 'Информация о боте',
            'wallet_connect_title': 'Подключить TON кошелек',
            'wallet_connect_subtitle': 'Используйте Wallet в Telegram или другое приложение',
            'wallet_modal_copy': 'Нужно только для будущих выплат\nНикогда не списываем средства',
            'share_popup_text': 'Я подключился к партнерской программе Telegram. Это работает автоматически.',
            'close_btn': 'Закрыть',
            'saved': 'Сохранено',
            'change_link': 'Изменить ссылку?',
        },

        'de': {
            'nav_home': 'Startseite',
            'nav_partners': 'Partner',
            'nav_top': 'TOP',
            'friends': 'Freunde',
            'top_activated': 'TOP PROGRAMM AKTIV',
            'link_connected': 'Link verbunden',
            'input_link_placeholder': 'Link hier einfügen...',
            'save': 'Speichern',
            'how_to_get_link': 'Wo finde ich den Link?',
            'unlock_top_title': 'TOP Status freischalten',
            'unlock_top_subtitle': 'Lade 5 Freunde ein, um exklusive Belohnungen freizuschalten',
            'invited': 'eingeladen',
            'goal': 'ZIEL',
            'invite_earn': 'EINLADEN & VERDIENEN',
            'potential_earnings': 'Deine möglichen Einnahmen',
            'user_count_1': '1 NUTZER',
            'user_count_10': '10 NUTZER',
            'user_count_100': '100 NUTZER',
            'estimates_disclaimer': 'Schätzungen basieren auf der durchschnittlichen Aktivität der geworbenen Nutzer.',
            'estimates_desc': 'Schätzungen basieren auf der durchschnittlichen Aktivität der geworbenen Nutzer.',
            'partners_title': 'Partner',
            'partners_subtitle': 'Geprüfte Bots & Stars für Aktionen verdienen',
            'top_bots_title': 'TOP Bots',
            'top_bots_subtitle': 'Erhalte x3-x7 mehr Stars',
            'browse_btn': 'Ansehen',
            'stars_suffix': '+ STARS',
            'x7_badge': '⚡ x7',
            'launch_btn': 'Starten ↗',
            'open_btn': 'Öffnen ↗',
            'estimated_share': '{{percent}}% Anteil',
            'about_earnhub': 'Über {{platform_name}}',
            'footer_about_text': '{{platform_name}} ist ein Aggregator für Empfehlungsprogramme, der Boni für das Netzwerkwachstum bietet. Profitiere von der 7% Telegram-Monetarisierung und maximiere deine Erträge durch unsere Partner-Bots.',
            'footer_disclaimer': 'Haftungsausschluss: {{platform_name}} ist kein Finanzinstitut.',
            'terms_of_use': 'Nutzungsbedingungen',
            'privacy_policy': 'Datenschutzrichtlinie',
            'support': 'Support',
            'badge_7_path': '7% Pfad gestartet',
            'badge_top_member': 'TOP Mitglied',
            'badge_super_sharer': 'Super-Verteiler',
            'your_earnings': 'Deine Einnahmen',
            'program_active': '✅ 7% Programm aktiv',
            'program_inactive': '❌ 7% Programm inaktiv',
            'achievements': 'Erfolge',
            'unlock_top': 'TOP freischalten',
            'to_pro': 'Zu Pro',
            'to_hub': 'Zu Hub',
            'max_level': 'Maximales Level',
            'started_path': '47 Personen haben den 7% Pfad gestartet',
            'top_opened_today': 'TOP wurde heute 19 Mal geöffnet',
            'partners_clicked_most': 'Meistgeklickte Partner',
            'share_popup_title': 'Link teilen',
            'next_btn': 'Weiter',
            'start_btn': 'Starten',
            'enter_wallet_error': 'Wallet-Adresse eingeben',
            'invalid_wallet_format': 'Ungültiges Wallet-Format',
            'wallet_saved_success': '✅ Wallet erfolgreich gespeichert!',
            'wallet_save_error': '❌ Fehler beim Speichern: ',
            'top_locked_title': 'TOP gesperrt',
            'top_locked_subtitle': 'Lade noch {{count}} Freunde ein, um TOP Partner freizuschalten oder kaufe Zugang.',
            'top_locked_message': "🎯 TOP-Bots werden nach deinen ersten <b>5 Einladungen</b> freigeschaltet.\n\n💬 Du musst noch <b>{{needed}}</b> Freunde einladen, um die profitabelsten Partner zu öffnen!\n\n💫 Du kannst TOP auch sofort für <b>{{price}}⭐</b> freischalten.\n\n👇 Tippe, um deinen Link zu teilen:",
            'btn_unlock_top': 'Freischalten für {{price}} Stars',
            'top_profits_title': 'TOP Partner',
            'top_profits_subtitle': 'Beste Angebote der Woche',
            'no_partners_found': 'Keine Partner gefunden',
            'no_top_bots': 'Keine TOP Bots verfügbar',
            'ton_connect_help': 'TON Connect ist das offizielle Protokoll zum Verbinden von TON Wallets in Telegram Mini Apps. Es ermöglicht das sichere Verbinden von Wallets, ohne private Schlüssel weiterzugeben.',
            'starter': 'Starter',
            'pro': 'Pro',
            'hub': 'Hub',
            'share_button': '🧡 Link teilen',
            'loading': 'Laden...',
            'retry_btn': 'Wiederholen',
            'connect_telegram_wallet': 'Wallet in Telegram verbinden',
            'choose_other_wallet': 'Andere App wählen',
            'view_all_wallets': 'Alle Wallets',
            'wallet_payouts_info': 'Nur für zukünftige Auszahlungen erforderlich',
            'wallet_no_withdrawals': 'Wir buchen niemals Geld ab',
            'how_to_find_address': 'So findest du die Wallet-Adresse:',
            'instruction_step_1': 'Öffne deine TON Wallet (Tonkeeper, MyTonWallet, Tonhub)',
            'instruction_step_2': 'Gehe zum Bereich "Empfangen" oder "Erhalten"',
            'instruction_step_3': 'Kopiere die Adresse (beginnt mit EQ, UQ, kQ oder 0Q)',
            'wallet_input_label': 'TON Wallet-Adresse:',
            'cancel': 'Abbrechen',
            'onboarding_title_1': 'Hier verdienst du an Aktionen in Telegram',
            'onboarding_step_1': 'Aktiviere 7%',
            'onboarding_step_2': 'Teile den Link',
            'onboarding_step_3': 'Leute kaufen → du erhältst %',
            'creating_invoice': 'Rechnung wird erstellt...',
            'top_unlocked': '✅ TOP freigeschaltet!',
            'payment_cancelled': 'Zahlung abgebrochen',
            'payment_error': '❌ Zahlungsfehler',
            'saving': 'Speichern...',
            'link_copied': '✅ Link kopiert!',
            'copy_failed': 'Kopieren fehlgeschlagen',
            'bot_id_missing': 'Fehler: Bot ID nicht gefunden',
            'link_missing': 'Empfehlungslink fehlt',
            'copied': '✅ Kopiert!',
            'share_text_pro': '🚀 Tritt {{bot_name}} bei — sammle Stars für deine Aktivität!',
            'share_text_starter': "🚀 Tritt {{bot_name}} bei — sammle Stars für deine Aktivität!",
            'activate_7_title': 'So aktivierst du 7% (einmalig für immer):',
            'activate_7_step_1': '1️⃣ Öffne @{{username}}',
            'activate_7_step_2': '2️⃣ «Partnerprogramm»',
            'activate_7_step_3': '3️⃣ «Verbinden»',
            'activate_7_footer': '→ {{percent}}% dauerhaft aktiv',
            'buy_top_fallback_title': 'TOP freischalten',
            'buy_top_fallback_text': "Um TOP freizuschalten, musst du:\n• {{needed}} Freunde einladen\n• Oder Zugang für {{price}} ⭐ kaufen\nZum Kaufen öffne den Bot und drücke \"TOP freischalten\"",
            'buy_top_fallback_text': "Um TOP freizuschalten, musst du:\n• {{needed}} Freunde einladen\n• Oder Zugang für {{price}} ⭐ kaufen\nZum Kaufen öffne den Bot und drücke \"TOP freischalten\"",
            'open_bot': 'Bot öffnen',
            'buy_top_title': 'TOP freischalten',
            'buy_top_description': 'Zugang zu exklusiven Partnern und x7 Verdienst',
            'buy_top_label': '{{price}} Stars',

            # --- Frontend Aliases (Fix for v5.0 UI) ---
            'stat_friends': 'Freunde',
            'top_program_active': 'TOP PROGRAMM AKTIV',
            'paste_link_placeholder': 'Link hier einfügen...',
            'activate_7_note': '⚠️ Wichtig: Nach der Verbindung drücke "Starten" im Chat.',
            'where_to_get_link': 'Wo finde ich den Link?',
            'share_your_link': 'LINK TEILEN',
            'invited_count': '{{count}} eingeladen',
            'goal_text': 'ZIEL: {{goal}}',
            'unlock_top_status': 'TOP Status freischalten',
            'invite_5_subtitle': 'Lade 5 Freunde ein, um exklusive Belohnungen freizuschalten',
            'invite_and_earn': 'EINLADEN & VERDIENEN',
            'browse': 'Ansehen',
            'partners': 'Partner',
            'verified_partners_desc': 'Geprüfte Bots & Stars für Aktionen verdienen',
            'top_bots': 'TOP Bots',
            'top_bots_desc': 'Erhalte x3-x7 mehr Stars',
            'recommended_title': 'Verifizierte Telegram-Bots',
            'recommended_subtitle': 'Wähle einen aus — starte und verbessere dich! 💪',
            'wallet_btn': 'Wallet',
            
            # --- Missing Static Elements (Added for full Index.html coverage) ---
            'trust_item_1': '🟢 Offizielles Telegram-Partnerprogramm',
            'trust_item_2': '🟢 Umsatzbeteiligungsmodell (bis zu 7%)',
            'trust_item_3': '🟢 Wallet: optional',
            'share_copy_1': 'Dein Link funktioniert 24/7',
            'share_copy_2': 'Jeder neue Nutzer kann diesen Pfad fortsetzen',
            'wallet_banner_text': 'Wallet verbinden → Auszahlungen aktivieren',
            'wallet_banner_btn': 'Verbinden',
            'info_title': 'Bot-Informationen',
            'wallet_connect_title': 'TON Wallet verbinden',
            'wallet_connect_subtitle': 'Nutze Wallet in Telegram oder eine andere App',
            'wallet_modal_copy': 'Nur für zukünftige Auszahlungen erforderlich\nWir buchen niemals Geld ab',
            'share_popup_text': 'Ich bin dem Telegram-Partnerprogramm beigetreten. Es funktioniert automatisch.',
            'close_btn': 'Schließen',
            'saved': 'Gespeichert',
            'change_link': 'Link ändern?',
        },
        'es': {
            'nav_home': 'Inicio',
            'nav_partners': 'Socios',
            'nav_top': 'TOP',
            'friends': 'Amigos',
            'top_activated': 'PROGRAMA TOP ACTIVO',
            'link_connected': 'Enlace conectado',
            'input_link_placeholder': 'Pega tu enlace del 7% aquí...',
            'save': 'Guardar',
            'how_to_get_link': '¿Cómo obtener el enlace?',
            'unlock_top_title': 'Desbloquear Estado TOP',
            'unlock_top_subtitle': 'Invita a 5 amigos para desbloquear recompensas exclusivas',
            'invited': 'invitado',
            'goal': 'META',
            'invite_earn': 'INVITA Y GANA',
            'potential_earnings': 'Tus Ganancias Potenciales',
            'user_count_1': '1 USUARIO',
            'user_count_10': '10 USUARIOS',
            'user_count_100': '100 USUARIOS',
            'estimates_disclaimer': 'Estimaciones basadas en la actividad promedio de los usuarios invitados.',
            'estimates_desc': 'Estimaciones basadas en la actividad promedio de los usuarios invitados.',
            'partners_title': 'Socios',
            'partners_subtitle': 'Bots verificados y gana Stars por acciones',
            'top_bots_title': 'Bots TOP',
            'top_bots_subtitle': 'Gana x3-x7 más Stars',
            'browse_btn': 'Explorar',
            'stars_suffix': '+ STARS',
            'x7_badge': '⚡ x7',
            'launch_btn': 'Lanzar ↗',
            'open_btn': 'Abrir ↗',
            'estimated_share': '{{percent}}% de participación',
            'about_earnhub': 'Sobre {{platform_name}}',
            'footer_about_text': '{{platform_name}} es un agregador de programas de referidos que ofrece bonos por el crecimiento de la red. Benefíciese de la monetización del 7% de Telegram y maximice sus ganancias a través de nuestros bots asociados.',
            'footer_disclaimer': 'Descargo de responsabilidad: {{platform_name}} no es una institución financiera.',
            'terms_of_use': 'Términos de uso',
            'privacy_policy': 'Política de privacidad',
            'support': 'Soporte',
            'badge_7_path': 'Camino del 7% iniciado',
            'badge_top_member': 'Miembro TOP',
            'badge_super_sharer': 'Súper compartidor',
            'your_earnings': 'Tus ganancias',
            'program_active': '✅ Programa 7% activo',
            'program_inactive': '❌ Programa 7% inactivo',
            'achievements': 'Logros',
            'unlock_top': 'Desbloquear TOP',
            'to_pro': 'A Pro',
            'to_hub': 'A Hub',
            'max_level': 'Nivel máximo',
            'started_path': '47 personas iniciaron el camino del 7%',
            'top_opened_today': 'TOP abierto 19 veces hoy',
            'partners_clicked_most': 'Socios más clicados',
            'share_popup_title': 'Compartir enlace',
            'next_btn': 'Siguiente',
            'start_btn': 'Empezar',
            'enter_wallet_error': 'Introduce la dirección de la billetera',
            'invalid_wallet_format': 'Formato de dirección de billetera no válido',
            'wallet_saved_success': '✅ ¡Monedero guardado con éxito!',
            'wallet_save_error': '❌ Error al guardar: ',
            'top_locked_title': 'TOP Bloqueado',
            'top_locked_subtitle': 'Invita a {{count}} amigos más para desbloquear socios TOP o compra el acceso.',
            'top_locked_message': "🎯 Los bots TOP se desbloquean después de tus primeros <b>5 invitados</b>.\n\n💬 Todavía necesitas invitar a <b>{{needed}}</b> amigos para desbloquear los partners más rentables.\n\n💫 También puedes desbloquear TOP al instante por <b>{{price}}⭐</b>.\n\n👇 Toca para compartir tu enlace:",
            'btn_unlock_top': 'Desbloquear por {{price}} Stars',
            'top_profits_title': 'Socios TOP',
            'top_profits_subtitle': 'Mejores ofertas de la semana',
            'no_partners_found': 'No se encontraron socios',
            'no_top_bots': 'No hay bots TOP disponibles todavía',
            'ton_connect_help': 'TON Connect es el protocolo oficial para conectar monederos TON en las Mini Apps de Telegram. Permite conectar monederos de forma segura sin compartir claves privadas.',
            'starter': 'Principiante',
            'pro': 'Pro',
            'hub': 'Hub',
            'share_button': '🧡 Compartir enlace',
            'loading': 'Cargando...',
            'retry_btn': 'Reintentar',
            'connect_telegram_wallet': 'Conectar monedero en Telegram',
            'choose_other_wallet': 'Elegir otra aplicación',
            'view_all_wallets': 'Todos los monederos',
            'wallet_payouts_info': 'Solo necesario para futuros pagos',
            'wallet_no_withdrawals': 'Nunca retiramos fondos',
            'how_to_find_address': 'Cómo encontrar la dirección del monedero:',
            'instruction_step_1': 'Abre tu monedero TON (Tonkeeper, MyTonWallet, Tonhub)',
            'instruction_step_2': 'Ve a la sección "Recibir" o "Obtener"',
            'instruction_step_3': 'Copia la dirección (empieza por EQ, UQ, kQ o 0Q)',
            'wallet_input_label': 'Dirección del monedero TON:',
            'cancel': 'Cancelar',
            'onboarding_title_1': 'Aquí ganas por acciones en Telegram',
            'onboarding_step_1': 'Activa el 7%',
            'onboarding_step_2': 'Comparte tu enlace',
            'onboarding_step_3': 'La gente compra → tú recibes %',
            'creating_invoice': 'Creando factura...',
            'top_unlocked': '✅ TOP desbloqueado!',
            'payment_cancelled': 'Pago cancelado',
            'payment_error': '❌ Error de pago',
            'saving': 'Guardando...',
            'link_copied': '✅ ¡Enlace copiado!',
            'copy_failed': 'Error al copiar',
            'bot_id_missing': 'Error: Bot ID no encontrado',
            'link_missing': 'Falta el enlace de referido',
            'copied': '✅ ¡Copiado!',
            'share_text_pro': '🚀 ¡Únete a {{bot_name}} — gana Stars por tu actividad!',
            'share_text_starter': "🚀 ¡Únete a {{bot_name}} — gana Stars por tu actividad!",
            'activate_7_title': 'Cómo activar el 7% (una vez para siempre):',
            'activate_7_step_1': '1️⃣ Abre @{{username}}',
            'activate_7_step_2': '2️⃣ "Programa de socios"',
            'activate_7_step_3': '3️⃣ "Conectar"',
            'activate_7_footer': '→ {{percent}}% activo para siempre',
            'buy_top_fallback_title': 'Desbloquear TOP',
            'buy_top_fallback_text': "Para desbloquear TOP necesitas:\n• Invita a {{needed}} amigos\n• O compra el acceso por {{price}} ⭐\nPara comprar, abre el bot y haz clic en el botón \"Desbloquear TOP\"",
            'buy_top_fallback_text': "Para desbloquear TOP necesitas:\n• Invita a {{needed}} amigos\n• O compra el acceso por {{price}} ⭐\nPara comprar, abre el bot y haz clic en el botón \"Desbloquear TOP\"",
            'open_bot': 'Abrir bot',
            'buy_top_title': 'Desbloquear TOP',
            'buy_top_description': 'Acceso a socios exclusivos y ganancias x7',
            'buy_top_label': '{{price}} Stars',
            'buy_top_price': '1',
            'earnings_step1_locked': "🔒 <b>Paso 1:</b> Desbloquea TOP invitando a {{needed}} amigos o comprando acceso por {{price}}⭐",

            # --- Frontend Aliases (Fix for v5.0 UI) ---
            'stat_friends': 'Amigos',
            'top_program_active': 'PROGRAMA TOP ACTIVO',
            'paste_link_placeholder': 'Pega tu enlace del 7% aquí...',
            'activate_7_note': '⚠️ Importante: Después de conectar, toca "Abrir" en el chat.',
            'where_to_get_link': '¿Cómo obtener el enlace?',
            'share_your_link': 'COMPARTIR ENLACE',
            'invited_count': '{{count}} invitado',
            'goal_text': 'META: {{goal}}',
            'unlock_top_status': 'Desbloquear Estado TOP',
            'invite_5_subtitle': 'Invita a 5 amigos para desbloquear recompensas exclusivas',
            'invite_and_earn': 'INVITA Y GANA',
            'browse': 'Explorar',
            'partners': 'Socios',
            'verified_partners_desc': 'Bots verificados y gana Stars por acciones',
            'top_bots': 'Bots TOP',
            'top_bots_desc': 'Gana x3-x7 más Stars',
            'recommended_title': 'Bots de Telegram verificados',
            'recommended_subtitle': '¡Elige cualquiera — lanza y mejora! 💪',
            'wallet_btn': 'Billetera',
            
            # --- Missing Static Elements (Added for full Index.html coverage) ---
            'trust_item_1': '🟢 Programa oficial de socios de Telegram',
            'trust_item_2': '🟢 Modelo de reparto de ingresos (hasta el 7%)',
            'trust_item_3': '🟢 Billetera: opcional',
            'share_copy_1': 'Tu enlace funciona 24/7',
            'share_copy_2': 'Cada nuevo usuario puede iniciar este camino',
            'wallet_banner_text': 'Conectar billetera → activar retiros',
            'wallet_banner_btn': 'Conectar',
            'info_title': 'Información del bot',
            'wallet_connect_title': 'Conectar tu billetera TON',
            'wallet_connect_subtitle': 'Usa Wallet en Telegram o elige otra aplicación',
            'wallet_modal_copy': 'Solo necesario para futuros pagos\nNunca retiramos fondos',
            'share_popup_text': 'Me uní al programa de socios de Telegram. Funciona automáticamente.',
            'close_btn': 'Cerrar',
            'saved': 'Guardado',
            'change_link': '¿Cambiar enlace?',
        },
    }
    
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
        
        PERFORMANCE: This method uses Redis caching to reduce DB queries by 70-90%.
        Cache key format: translations:{bot_id}:{key}:{lang}
        TTL: 3600s (1 hour)
        
        Args:
            key: Translation key (e.g., 'welcome', 'wallet_saved')
            lang: Language code (defaults to FALLBACK_LANG)
            variables: Variables for substitution (e.g., {'wallet': 'EQ123...'})
        
        Returns:
            Translated text with variables substituted
        """
        lang = lang or self.FALLBACK_LANG
        variables = variables or {}
        
        # Try Redis cache first (before custom/DB lookups)
        cache_key = f"translations:{self.bot_id}:{key}:{lang}"
        cached_text = cache.get(cache_key)
        if cached_text:
            logger.debug(f"Cache HIT: {cache_key}")
            # Apply variable substitution to cached text
            text = cached_text
            for var_key, var_value in variables.items():
                placeholder = '{{' + var_key + '}}'
                text = text.replace(placeholder, str(var_value))
            return text
        
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
            
            # If database translation not found, try GLOBAL_UI_DEFAULTS
            if not translation:
                if key in self.GLOBAL_UI_DEFAULTS.get(lang, {}):
                    text = self.GLOBAL_UI_DEFAULTS[lang][key]
                elif key in self.GLOBAL_UI_DEFAULTS.get(self.FALLBACK_LANG, {}):
                    text = self.GLOBAL_UI_DEFAULTS[self.FALLBACK_LANG][key]
                elif key in self.GLOBAL_UI_DEFAULTS.get(self.DEFAULT_LANG, {}):
                    text = self.GLOBAL_UI_DEFAULTS[self.DEFAULT_LANG][key]
                else:
                    return key
            else:
                text = translation.text
        
        # Store in Redis cache for next time (TTL: 1 hour)
        # Cache after DB lookup but before variable substitution
        cache.set(cache_key, text, ttl=3600)
        logger.debug(f"Cache SET: {cache_key}")
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

