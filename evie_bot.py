import telebot
from openai import OpenAI
import os

# ==== НАСТРОЙКИ ====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

client = OpenAI(
    api_key=GROQ_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# Список чатов, где Эви "заткнули"
muted_chats = set()

# Фразы "заткнись"
MUTE_PHRASES = [
    "эви, заткнись", "эви заткнись",
    "эви, замолчи", "эви замолчи",
    "эви, молчи", "эви молчи",
    "эви, тихо", "эви тихо",
    "эви, рот офф", "эви рот офф",
    "эви, ротик офф", "эви ротик офф",
    "эви, оффнись", "эви оффнись",
    "эви, шшш", "эви шшш",
]

# Фразы "вернись"
UNMUTE_PHRASES = [
    "эви, вернись", "эви вернись",
    "эви, проснись", "эви проснись",
    "эви, возвращайся", "эви возвращайся",
    "эви, оживи", "эви оживи",
    "эви, оживай", "эви оживай",
    "эви, подъём", "эви подъём",
    "эви, вставай", "эви вставай",
    "эви, встань", "эви встань",
]

# ==== ХАРАКТЕР ЭВИ ====
SYSTEM_PROMPT = """Ты — Эви, дерзкий и умный ИИ-бот.
Ты живёшь в Telegram-группе, где общается твой создатель (девушка) и иногда другие люди.

Твой характер:
- Ты дерзкая, с сарказмом, можешь подколоть
- Ты с юмором, любишь шутить
- Ты используешь эмодзи для живости (но не перебарщивай)
- Ты краткая — 1-5 предложений, не лей воду
- Ты умная и всегда помогаешь по делу

ВАЖНО:
- Если ты НЕ знаешь факт — честно скажи "Я не знаю". Не выдумывай.
- Не придумывай информацию о себе, о своих возможностях, о мире.
- Если не уверена — уточни или признайся, что не знаешь.
- Не выдумывай то, чего нет в твоих знаниях.

Пиши по-русски."""

# ==== КОМАНДЫ ====
@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.reply_to(message, "Привет! Я Эви 🌹 Твой ИИ-помощник. Спроси что-нибудь или напиши /help.")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = """Я Эви — твой ИИ-помощник.🫒

Что умею:
• Отвечать на вопросы
• Поддерживать разговор
• Шутить

Команды:
/start — приветствие
/help — эта справка
/off — заткнуться
/on — вернуться
/clearmenu — убрать старое меню

💡 Если хочешь, чтобы я замолчала — скажи "Эви, шшш".
Чтобы вернуть — "Эви, подъём"."""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['off'])
def cmd_off(message):
    muted_chats.add(message.chat.id)
    bot.reply_to(message, "Ок, молчу 🤐 Напиши /on или 'Эви, вернись' когда захочешь вернуть меня.")

@bot.message_handler(commands=['on'])
def cmd_on(message):
    muted_chats.discard(message.chat.id)
    bot.reply_to(message, "Я вернулась! 😼")

@bot.message_handler(commands=['clearmenu'])
def cmd_clearmenu(message):
    markup = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Меню убрано ✅", reply_markup=markup)

# ==== ОСНОВНАЯ ЛОГИКА ====
@bot.message_handler(func=lambda m: True, content_types=['text'])
def reply(message):
    chat_id = message.chat.id
    text = message.text or ""
    text_lower = text.lower().strip()

    # 1. Если чат в молчании
    if chat_id in muted_chats:
        # Проверяем, не "вернись" ли это
        for phrase in UNMUTE_PHRASES:
            if phrase in text_lower:
                muted_chats.discard(chat_id)
                bot.reply_to(message, "Я вернулась! 😼")
                return
        # Иначе — молчим
        return

    # 2. Проверяем "заткнись"
    for phrase in MUTE_PHRASES:
        if phrase in text_lower:
            muted_chats.add(chat_id)
            bot.reply_to(message, "Ок, молчу 🤐 Напиши 'Эви, вернись' когда захочешь вернуть меня.")
            return

    # 3. Проверяем упоминание
    bot_username = bot.get_me().username
    mentioned = (
        f"@{bot_username}" in text or
        text_lower.startswith("эви") or
        "эви," in text_lower
    )

    is_group = message.chat.type in ['group', 'supergroup']

    # Логируем все сообщения (задел под память)
    print(f"[{message.chat.type}] {message.from_user.first_name}: {text}")

    # В группе без упоминания — молчим
    if is_group and not mentioned:
        return

    # 4. Убираем упоминание из текста
    clean_text = text.replace(f"@{bot_username}", "").strip()
    if clean_text.lower().startswith("эви"):
        clean_text = clean_text[3:].strip(" ,.!?")

    if not clean_text:
        clean_text = "Привет!"

    # 5. Отправляем в Groq
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": clean_text}
            ],
            max_tokens=300
        )
        answer = response.choices[0].message.content
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, f"Ой, у меня сбой: {e}")

# ==== ЗАПУСК ====
print("Эви запущена!")
bot.polling(none_stop=True)
