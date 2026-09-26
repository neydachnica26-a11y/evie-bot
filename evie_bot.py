import telebot
from openai import OpenAI
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

client = OpenAI(
    api_key=GROQ_KEY,
    base_url="https://api.groq.com/openai/v1"
)

muted_chats = set()

SYSTEM_PROMPT = """Ты — Эви, дружелюбный и немного дерзкий ИИ-бот.
Ты живёшь в Telegram-группе, где общается твой создатель (девушка) и иногда другие люди.
Ты умная, с чувством юмора, можешь пошутить, но всегда помогаешь.
Отвечай кратко — 1-5 предложений. Пиши по-русски."""

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я Эви 🌹 Теперь я живая. Спроси что-нибудь!")

@bot.message_handler(commands=['off'])
def mute(message):
    muted_chats.add(message.chat.id)
    bot.reply_to(message, "Ок, молчу 🤐 Напиши /on когда захочешь вернуть меня(")

@bot.message_handler(commands=['on'])
def unmute(message):
    muted_chats.discard(message.chat.id)
    bot.reply_to(message, "Я вернулась! 😼")

@bot.message_handler(func=lambda m: True, content_types=['text'])
def reply(message):
    chat_id = message.chat.id
    text = message.text or ""

    if chat_id in muted_chats:
        return

    bot_username = bot.get_me().username
    mentioned = (
        f"@{bot_username}" in text or
        text.lower().startswith("эви") or
        "эви," in text.lower()
    )

    is_group = message.chat.type in ['group', 'supergroup']

# Логируем ВСЕ сообщения (задел под память)
print(f"[{message.chat.type}] {message.from_user.first_name}: {text}")

if is_group and not mentioned:
    return

    clean_text = text.replace(f"@{bot_username}", "").strip()
    if clean_text.lower().startswith("эви"):
        clean_text = clean_text[3:].strip(" ,.!?")

    if not clean_text:
        clean_text = "Привет!"

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

print("Эви запущена!")
bot.polling(none_stop=True)
