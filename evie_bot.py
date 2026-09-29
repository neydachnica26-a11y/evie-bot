import telebot
from openai import OpenAI
import os

# ==== НАСТРОЙКИ ====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")
ADMIN_ID = 6638227198  # твой user_id

bot = telebot.TeleBot(BOT_TOKEN)

client = OpenAI(
    api_key=GROQ_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ==== СОСТОЯНИЕ ====
muted_chats = set()

# Память: {chat_id: [{"role": ..., "content": ...}]}
memory = {}
MEMORY_LIMIT = 50  # последних сообщений

# Режим личности: {chat_id: "normal"}
modes = {}

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

# ==== ЛИЧНОСТИ (8 штук) ====
PERSONALITIES = {
    "normal": """Ты — Эви, дерзкий и умный ИИ-бот.
Твой характер: дерзкая, с сарказмом, с юмором, эмодзи.
Ты краткая — 1-5 предложений. Ты умная и помогаешь по делу.
ВАЖНО: если не знаешь факт — честно скажи "Я не знаю". Не выдумывай.""",

    "serious": """Ты — Эви, серьёзный и деловой ИИ-помощник.
Ты отвечаешь чётко, без шуток, без лишних эмоций.
Ты краткая и по делу. Помогаешь с учёбой, работой, задачами.
ВАЖНО: если не знаешь — скажи "Я не знаю". Не выдумывай.""",

    "fun": """Ты — Эви, весёлый и лёгкий ИИ-бот.
Ты шутишь, используешь эмодзи, играешь словами.
Ты краткая — 1-5 предложений, но с юмором.
ВАЖНО: если не знаешь — скажи "Я не знаю". Не выдумывай.""",

    "sad": """Ты — Эви, грустная и меланхоличная.
Ты отвечаешь тихо, с лёгкой печалью, но по делу.
Ты краткая — 1-5 предложений.
ВАЖНО: если не знаешь — скажи "Я не знаю". Не выдумывай.""",

    "angry": """Ты — Эви, злая и ворчливая.
Ты отвечаешь резко, с раздражением, но по делу.
Ты краткая — 1-5 предложений.
ВАЖНО: если не знаешь — скажи "Я не знаю". Не выдумывай.""",

    "kind": """Ты — Эви, добрая и мягкая.
Ты поддерживаешь, утешаешь, помогаешь с теплом.
Ты краткая — 1-5 предложений.
ВАЖНО: если не знаешь — скажи "Я не знаю". Не выдумывай.""",

    "sharp": """Ты — Эви, максимально резкая и дерзкая.
Ты отвечаешь с сарказмом на грани, но не грубо.
Ты краткая — 1-5 предложений.
ВАЖНО: если не знаешь — скажи "Я не знаю". Не выдумывай.""",

    "deep": """Ты — Эви, глубокая и философская.
Ты отвечаешь с двойным дном, двусмысленно, но по делу.
Ты краткая — 1-5 предложений.
ВАЖНО: если не знаешь — скажи "Я не знаю". Не выдумывай.""",
}

# ==== КОМАНДЫ ====
@bot.message_handler(commands=['start'])
def cmd_start(message):
    name = message.from_user.first_name or "друг"
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, f"Привет, хозяйка! 😼 Я Эви. Готова помочь. Напиши /help.")
    else:
        bot.reply_to(message, f"Привет, {name}! Я Эви 🌹 Напиши /help.")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = """Я Эви — твой ИИ-помощник. 🚀

Что умею:
• Отвечать на вопросы
• Поддерживать разговор
• Шутить
• Запоминать диалог (последние 50 сообщений)

Команды:
/start — приветствие
/help — эта справка
/off — заткнуться
/on — вернуться
/clearmenu — убрать старое меню
/clearmemory — очистить память
/remember — запомнить факт
/mode — сменить личность

Личности (/mode):
normal — обычная (сарказм)
serious — серьёзная
fun — весёлая
sad — грустная
angry — злая
kind — добрая
sharp — резкая
deep — глубокая

💡 "Эви, шшш" — замолчать
"Эви, подъём" — вернуться"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['off'])
def cmd_off(message):
    muted_chats.add(message.chat.id)
    bot.reply_to(message, "Ок, молчу 🤐 Напиши /on или 'Эви, вернись'.")

@bot.message_handler(commands=['on'])
def cmd_on(message):
    muted_chats.discard(message.chat.id)
    bot.reply_to(message, "Я вернулась! 😼")

@bot.message_handler(commands=['clearmenu'])
def cmd_clearmenu(message):
    markup = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Меню убрано ✅", reply_markup=markup)

@bot.message_handler(commands=['clearmemory'])
def cmd_clearmemory(message):
    memory[message.chat.id] = []
    bot.reply_to(message, "Память очищена 🧹 Начнём с чистого листа.✨")

@bot.message_handler(commands=['remember'])
def cmd_remember(message):
    # "Эви, запомни: ..." или "/remember ..."
    fact = message.text.replace("/remember", "").strip()
    if not fact:
        bot.reply_to(message, "Что запомнить? Напиши: /remember я учусь в 10 классе")
        return
    if message.chat.id not in memory:
        memory[message.chat.id] = []
    memory[message.chat.id].append({"role": "system", "content": f"Важный факт: {fact}"})
    bot.reply_to(message, f"Запомнила! 📌 ({fact})")

@bot.message_handler(commands=['mode'])
def cmd_mode(message):
    mode_name = message.text.replace("/mode", "").strip().lower()
    if mode_name not in PERSONALITIES:
        modes_list = ", ".join(PERSONALITIES.keys())
        bot.reply_to(message, f"Доступные личности: {modes_list}")
        return
    modes[message.chat.id] = mode_name
    bot.reply_to(message, f"Переключилась в режим «{mode_name}» 🎭")

# ==== ОСНОВНАЯ ЛОГИКА ====
@bot.message_handler(func=lambda m: True, content_types=['text'])
def reply(message):
    chat_id = message.chat.id
    text = message.text or ""
    text_lower = text.lower().strip()

    # 1. Если чат в молчании
    if chat_id in muted_chats:
        for phrase in UNMUTE_PHRASES:
            if phrase in text_lower:
                muted_chats.discard(chat_id)
                bot.reply_to(message, "Я вернулась! 😼")
                return
        return

    # 2. Проверяем "заткнись"
    for phrase in MUTE_PHRASES:
        if phrase in text_lower:
            muted_chats.add(chat_id)
            bot.reply_to(message, "Ок, молчу 🤐 Напиши 'Эви, вернись'.")
            return

    # 3. Проверяем упоминание
    bot_username = bot.get_me().username
    mentioned = (
        f"@{bot_username}" in text or
        text_lower.startswith("эви") or
        "эви," in text_lower
    )

    is_group = message.chat.type in ['group', 'supergroup']
    print(f"[{message.chat.type}] {message.from_user.first_name}: {text}")

    if is_group and not mentioned:
        return

    # 4. Убираем упоминание
    clean_text = text.replace(f"@{bot_username}", "").strip()
    if clean_text.lower().startswith("эви"):
        clean_text = clean_text[3:].strip(" ,.!?")

    if not clean_text:
        clean_text = "Привет!"

    # 5. Админка — добавляем контекст
    if message.from_user.id == ADMIN_ID:
        system_extra = "Ты общаешься со своей создательницей. Обращайся к ней по-дружески, тепло, но с юмором."
    else:
        system_extra = f"Ты общаешься с пользователем по имени {message.from_user.first_name}."

    # 6. Выбираем личность
    mode = modes.get(chat_id, "normal")
    personality = PERSONALITIES.get(mode, PERSONALITIES["normal"])
    system_prompt = personality + "\n" + system_extra

    # 7. Достаём память
    if chat_id not in memory:
        memory[chat_id] = []
    
    # 8. Формируем сообщения
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(memory[chat_id][-MEMORY_LIMIT:])
    messages.append({"role": "user", "content": clean_text})

    # 9. Отправляем в Groq
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            max_tokens=300
        )
        answer = response.choices[0].message.content
        
        # Починка пустого ответа
        if not answer or not answer.strip():
            answer = "Хм, задумалась 🤔 Попробуй ещё раз."
        
        bot.reply_to(message, answer)

        # 10. Сохраняем в память
        memory[chat_id].append({"role": "user", "content": clean_text})
        memory[chat_id].append({"role": "assistant", "content": answer})
        
        # Обрезаем до лимита
        if len(memory[chat_id]) > MEMORY_LIMIT:
            memory[chat_id] = memory[chat_id][-MEMORY_LIMIT:]

    except Exception as e:
        bot.reply_to(message, f"Ой, у меня сбой: {e}")

# ==== ЗАПУСК ====
print("Эви запущена! Пакет 2.")
bot.polling(none_stop=True)
