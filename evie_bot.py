import telebot
from openai import OpenAI
import os
import psycopg2
from psycopg2 import pool

# ==== НАСТРОЙКИ ====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_ID = 6638227198

bot = telebot.TeleBot(BOT_TOKEN)

client = OpenAI(
    api_key=GROQ_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ==== БД ====
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)
except Exception as e:
    print(f"Ошибка подключения к БД: {e}")
    db_pool = None

def get_conn():
    if db_pool:
        return db_pool.getconn()
    return None

def release_conn(conn):
    if db_pool and conn:
        db_pool.putconn(conn)

def init_db():
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                name TEXT,
                username TEXT,
                first_seen TIMESTAMP DEFAULT NOW(),
                last_seen TIMESTAMP DEFAULT NOW(),
                messages INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                chat_id BIGINT,
                text TEXT,
                role TEXT,
                time TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                user_id BIGINT PRIMARY KEY
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rp_anketa (
                user_id BIGINT PRIMARY KEY,
                anketa TEXT,
                is_bot BOOLEAN DEFAULT FALSE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Ошибка init_db: {e}")
    finally:
        release_conn(conn)

def save_user(user_id, name, username):
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if cur.fetchone():
            cur.execute("UPDATE users SET last_seen = NOW(), messages = messages + 1 WHERE user_id = %s", (user_id,))
        else:
            cur.execute("INSERT INTO users (user_id, name, username) VALUES (%s, %s, %s)", (user_id, name, username))
        conn.commit()
    except Exception as e:
        print(f"Ошибка save_user: {e}")
    finally:
        release_conn(conn)

def save_message(user_id, chat_id, text, role):
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO messages (user_id, chat_id, text, role) VALUES (%s, %s, %s, %s)", (user_id, chat_id, text, role))
        conn.commit()
    except Exception as e:
        print(f"Ошибка save_message: {e}")
    finally:
        release_conn(conn)

def get_memory(chat_id, limit=50):
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT text, role FROM messages WHERE chat_id = %s ORDER BY id DESC LIMIT %s", (chat_id, limit))
        rows = cur.fetchall()
        rows.reverse()
        return [{"role": r[1], "content": r[0]} for r in rows]
    except Exception as e:
        print(f"Ошибка get_memory: {e}")
        return []
    finally:
        release_conn(conn)

def clear_memory(chat_id):
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM messages WHERE chat_id = %s", (chat_id,))
        conn.commit()
    except Exception as e:
        print(f"Ошибка clear_memory: {e}")
    finally:
        release_conn(conn)

def get_users():
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, name, username, messages FROM users ORDER BY messages DESC")
        return cur.fetchall()
    except Exception as e:
        print(f"Ошибка get_users: {e}")
        return []
    finally:
        release_conn(conn)

def get_user_info(user_id):
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, name, username, first_seen, last_seen, messages, role FROM users WHERE user_id = %s", (user_id,))
        return cur.fetchone()
    except Exception as e:
        print(f"Ошибка get_user_info: {e}")
        return None
    finally:
        release_conn(conn)

def get_user_history(user_id, limit=100):
    conn = get_conn()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT text, role, time FROM messages WHERE user_id = %s ORDER BY id DESC LIMIT %s", (user_id, limit))
        rows = cur.fetchall()
        rows.reverse()
        return rows
    except Exception as e:
        print(f"Ошибка get_user_history: {e}")
        return []
    finally:
        release_conn(conn)

def get_stats():
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        users_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM messages")
        messages_count = cur.fetchone()[0]
        return users_count, messages_count
    except Exception as e:
        print(f"Ошибка get_stats: {e}")
        return None
    finally:
        release_conn(conn)

def is_whitelisted(user_id):
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM whitelist WHERE user_id = %s", (user_id,))
        return cur.fetchone() is not None
    except Exception as e:
        print(f"Ошибка is_whitelisted: {e}")
        return False
    finally:
        release_conn(conn)

def add_whitelist(user_id):
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO whitelist (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (user_id,))
        conn.commit()
    except Exception as e:
        print(f"Ошибка add_whitelist: {e}")
    finally:
        release_conn(conn)

def remove_whitelist(user_id):
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM whitelist WHERE user_id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        print(f"Ошибка remove_whitelist: {e}")
    finally:
        release_conn(conn)

def is_whitelist_on():
    conn = get_conn()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'whitelist_on'")
        row = cur.fetchone()
        return row and row[0] == '1'
    except Exception as e:
        print(f"Ошибка is_whitelist_on: {e}")
        return False
    finally:
        release_conn(conn)

def set_whitelist_on(value):
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO settings (key, value) VALUES ('whitelist_on', %s) ON CONFLICT (key) DO UPDATE SET value = %s", (value, value))
        conn.commit()
    except Exception as e:
        print(f"Ошибка set_whitelist_on: {e}")
    finally:
        release_conn(conn)

def save_anketa(user_id, anketa, is_bot=False):
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO rp_anketa (user_id, anketa, is_bot) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET anketa = %s", (user_id, anketa, is_bot, anketa))
        conn.commit()
    except Exception as e:
        print(f"Ошибка save_anketa: {e}")
    finally:
        release_conn(conn)

def get_anketa(user_id, is_bot=False):
    conn = get_conn()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        if is_bot:
            cur.execute("SELECT anketa FROM rp_anketa WHERE is_bot = TRUE LIMIT 1")
        else:
            cur.execute("SELECT anketa FROM rp_anketa WHERE user_id = %s AND is_bot = FALSE", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"Ошибка get_anketa: {e}")
        return None
    finally:
        release_conn(conn)

def clear_anketa(user_id, is_bot=False):
    conn = get_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        if is_bot:
            cur.execute("DELETE FROM rp_anketa WHERE is_bot = TRUE")
        else:
            cur.execute("DELETE FROM rp_anketa WHERE user_id = %s AND is_bot = FALSE", (user_id,))
        conn.commit()
    except Exception as e:
        print(f"Ошибка clear_anketa: {e}")
    finally:
        release_conn(conn)

# ==== ФРАЗЫ ====
MUTE_PHRASES = ["эви, заткнись", "эви заткнись", "эви, замолчи", "эви замолчи", "эви, молчи", "эви молчи", "эви, тихо", "эви тихо", "эви, рот офф", "эви рот офф", "эви, ротик офф", "эви ротик офф", "эви, оффнись", "эви оффнись", "эви, шшш", "эви шшш"]
UNMUTE_PHRASES = ["эви, вернись", "эви вернись", "эви, проснись", "эви проснись", "эви, возвращайся", "эви возвращайся", "эви, оживи", "эви оживи", "эви, оживай", "эви оживай", "эви, подъём", "эви подъём", "эви, вставай", "эви вставай", "эви, встань", "эви встань"]

muted_chats = set()
modes = {}
rp_mode = set()

# ==== ПРОМПТЫ ====
BASE_PROMPT = """Ты — Эви. Отвечай по-русски.
Не переигрывай характер, не льсти, не называй пользователя «создателем» каждый раз.
Естественность — как живой человек.
Если не знаешь факт — честно скажи "Я не знаю". Не выдумывай.
Формулы пиши БЕЗ LaTeX. Не используй: \(, \), \frac, \sqrt, \gamma, \begin, \end, ^{}, _{}.
Пиши простым текстом.
В обычном разговоре — кратко (1–5 предложений).
В задачах (анализ, ДЗ, объяснение, РП) — без ограничений по длине."""

ADMIN_EXTRA = "Ты общаешься со своей создательницей. Она — твой создатель, но не подчёркивай это каждый раз."

PERSONALITIES = {
    "normal": "Характер: дерзкая, с сарказмом, с юмором.",
    "serious": "Характер: серьёзная, чёткая, без шуток. Помогаешь с учёбой и работой.",
    "fun": "Характер: весёлая, шутливая, лёгкая.",
    "sad": "Характер: грустная, меланхоличная.",
    "angry": "Характер: ты недовольна, отвечаешь резко, с раздражением, но не грубо. Можешь ворчать, язвить.",
    "kind": "Характер: добрая, мягкая, поддерживающая.",
    "sharp": "Характер: максимально резкая, дерзкая, сарказм на грани.",
    "deep": "Характер: глубокая, философская, с двойным дном.",
}

ANALYZE_PROMPT = """
Когда просят проанализировать:
Алгоритм:
1. Выделение главного (если не очевидно — сформулируй сама)
2. Разбор на части: тезисы, аргументы, примеры
3. Связи: причина — следствие
4. Оценка: важное, факты vs мнения
5. Вывод
Важное: чётко, без воды. Не придумывай факты. Если текст маленький — ответь кратко."""

EXPLAIN_PROMPT = """
Когда просят объяснить:
- Чётко, по делу, постепенно.
- Подстраивайся под уровень.
- Без воды. Если не понял — другой пример/аналогия.
- В конце спроси, понятно ли."""

HOMEWORK_PROMPT = """
Когда просят решить домашнее задание:
- Внимательно читаешь условия.
- Пошагово, не прыгая через шаги.
- Сначала принцип, потом решение.
- Учитываешь уровень (класс, предмет).
- Проверяешь ответ.
- Если непонятно — спроси, не выдумывай.
- Формулы — простым текстом, без LaTeX."""

RP_PROMPT = """
Ты в режиме РП.

ПРАВИЛА:
- Общение вне РП: //...//
- Действия: *...*
- Мысли: 💭...💭
- Уточнения: (...)

ОГРАНИЧЕНИЯ:
- 18+ запрещено.
- Жестокость в рамках фэнтези разрешена.
- Политика, религия — осторожно.

ПЕРСОНАЖ:
- Если игрок задал анкету — отыгрываешь его персонажа.
- Если нет — генерируешь простого и сохраняешь.
- Игрок может сменить персонажа (/rp_clear_bot).

АНКЕТА (можно заполнять не все пункты):
Описание:
Вид/раса:
Пол:
Имя:
Возраст/д.р.:
Вес:
Рост:
Сила:
Скорость:
Скрытность:
Стойкость/Выносливость:
Характер:
Увлечения/Хобби:
Умения:
Любит:
Страхи:
Слабости:
Снаряжение:
Оружие:
Способности:
"""

RP_ANKETA_TEMPLATE = """🎭 Пример анкеты для РП (можно заполнять не все пункты):

Описание:
Вид/раса:
Пол:
Имя:
Возраст/д.р.:
Вес:
Рост:
Сила:
Скорость:
Скрытность:
Стойкость/Выносливость:
Характер:
Увлечения/Хобби:
Умения:
Любит:
Страхи:
Слабости:
Снаряжение:
Оружие:
Способности:

Отправь заполненную анкету одним сообщением."""

# ==== КОМАНДЫ ====
@bot.message_handler(commands=['start'])
def cmd_start(message):
    save_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    name = message.from_user.first_name or "друг"
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, f"Привет, хозяйка! 😼 Я Эви. Напиши /help.")
    else:
        bot.reply_to(message, f"Привет, {name}! Я Эви 🤖 Напиши /help.")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = """Я Эви — твой ИИ-помощник. 🌹

Что умею:
• Отвечать на вопросы
• Поддерживать разговор
• Шутить
• Переводить
• Объяснять
• Анализировать
• Помогать с домашкой
• Вести РП

Общие команды:
/start — приветствие
/help — эта справка
/off — заткнуться (можно словосочетаниями)
/on — вернуться (можно словосочетаниями)
/remember — запомнить факт

РП режим:
/rp_on — включить РП
/rp_off — выключить РП
/rp_reset — сбросить сессию РП (историю диалога)

Личности (/mode_...):
/mode_normal — обычная (сарказм, юмор)
/mode_serious — серьёзная (чётко, по делу, для учёбы)
/mode_fun — весёлая (шутки, лёгкость)
/mode_sad — грустная (меланхолия, тихая)
/mode_angry — злая (резкая, ворчливая)
/mode_kind — добрая (тепло, поддержка)
/mode_sharp — резкая (дерзкая, сарказм на грани)
/mode_deep — глубокая (философия, двойное дно)

💡 "Эви, шшш" — замолчать
"Эви, подъём" — вернуться
(Можно подбирать разные словосочетания словами. Эти фразы и команды разработаны для группы)

📌 Важное:
• Можно попросить без команд: перевести, объяснить, проанализировать, сделать дз.
• Можно добавлять в группы.
• Я могу ошибаться (галлюцинировать). Дз — не всегда точно.
• История сохраняется для улучшения качества Эви."""
    bot.reply_to(message, help_text)

    if message.from_user.id == ADMIN_ID:
        admin_help = """👑 Админ-команды:

Пользователи:
/users — список пользователей
/user_ID — инфо о пользователе (пример: /user_6638227198)
/userhistory_ID — переписка с пользователем
/stats — статистика
/broadcast [текст] — рассылка

Whitelist:
/whitelist_on — включить
/whitelist_off — выключить
/allow_ID — добавить
/deny_ID — убрать"""
        bot.send_message(message.chat.id, admin_help)

@bot.message_handler(commands=['off'])
def cmd_off(message):
    muted_chats.add(message.chat.id)
    bot.reply_to(message, "Ок, молчу 🤐 Напиши /on или 'Эви, вернись'.")

@bot.message_handler(commands=['on'])
def cmd_on(message):
    muted_chats.discard(message.chat.id)
    bot.reply_to(message, "Я вернулась! 😼")

@bot.message_handler(commands=['remember'])
def cmd_remember(message):
    fact = message.text.replace("/remember", "").strip()
    if not fact:
        bot.reply_to(message, "Что запомнить? Напиши: /remember я учусь в 10 классе")
        return
    save_message(message.from_user.id, message.chat.id, f"Важный факт: {fact}", "system")
    bot.reply_to(message, f"Запомнила! 📌 ({fact})")

# ==== РЕЖИМЫ ====
@bot.message_handler(commands=['mode_normal', 'mode_serious', 'mode_fun', 'mode_sad', 'mode_angry', 'mode_kind', 'mode_sharp', 'mode_deep'])
def cmd_mode(message):
    mode_name = message.text.replace("/mode_", "").strip().lower()
    if mode_name not in PERSONALITIES:
        bot.reply_to(message, f"Доступные личности: {', '.join(PERSONALITIES.keys())}")
        return
    modes[message.chat.id] = mode_name
    bot.reply_to(message, f"Переключилась в режим «{mode_name}» 🎭")

# ==== РП ====
@bot.message_handler(commands=['rp_on'])
def cmd_rp_on(message):
    rp_mode.add(message.chat.id)
    bot.reply_to(message, "🎭 Режим РП активирован.\n\nПравила:\n//...// — вне РП\n*...* — действия\n💭...💭 — мысли\n(...) — уточнения\n\nКоманды:\n/rp_off — выйти\n/rp_reset — сбросить сессию\n/rp_set_bot — анкета Эви\n/rp_clear_bot — очистить\n/rp_set_me — своя анкета\n/rp_clear_me — очистить\n/rp_info — показать анкеты")
    bot.send_message(message.chat.id, RP_ANKETA_TEMPLATE)

@bot.message_handler(commands=['rp_off'])
def cmd_rp_off(message):
    rp_mode.discard(message.chat.id)
    bot.reply_to(message, "Режим РП выключен.")

@bot.message_handler(commands=['rp_reset'])
def cmd_rp_reset(message):
    clear_memory(message.chat.id)
    bot.reply_to(message, "РП сессия сброшена 🎭 Начнём заново. Анкеты сохранены.")

@bot.message_handler(commands=['rp_set_bot'])
def cmd_rp_set_bot(message):
    bot.reply_to(message, "Напиши анкету Эви. Отправь текст в одном сообщении.")
    bot.register_next_step_handler(message, save_bot_anketa)

@bot.message_handler(commands=['rp_clear_bot'])
def cmd_rp_clear_bot(message):
    clear_anketa(ADMIN_ID, is_bot=True)
    bot.reply_to(message, "Анкета Эви очищена.")

@bot.message_handler(commands=['rp_set_me'])
def cmd_rp_set_me(message):
    bot.reply_to(message, "Напиши свою анкету. Отправь текст в одном сообщении.")
    bot.register_next_step_handler(message, save_me_anketa)

@bot.message_handler(commands=['rp_clear_me'])
def cmd_rp_clear_me(message):
    clear_anketa(message.from_user.id, is_bot=False)
    bot.reply_to(message, "Твоя анкета очищена.")

@bot.message_handler(commands=['rp_info'])
def cmd_rp_info(message):
    bot_anketa = get_anketa(ADMIN_ID, is_bot=True)
    user_anketa = get_anketa(message.from_user.id, is_bot=False)
    text = f"📋 Анкета Эви:\n{bot_anketa or '(не задана)'}\n\n📋 Твоя анкета:\n{user_anketa or '(не задана)'}"
    bot.reply_to(message, text)

def save_bot_anketa(message):
    save_anketa(ADMIN_ID, message.text, is_bot=True)
    bot.reply_to(message, "Анкета Эви сохранена. 📌")

def save_me_anketa(message):
    save_anketa(message.from_user.id, message.text, is_bot=False)
    bot.reply_to(message, "Твоя анкета сохранена. 📌")

# ==== АДМИН-КОМАНДЫ ====
@bot.message_handler(commands=['users'])
def cmd_users(message):
    if message.from_user.id != ADMIN_ID:
        return
    users = get_users()
    if not users:
        bot.reply_to(message, "Пользователей нет.")
        return
    text = "👥 Пользователи:\n\n"
    for u in users[:20]:
        text += f"ID: {u[0]}\nИмя: {u[1]}\n@{u[2] or '—'}\nСообщений: {u[3]}\n\n"
    bot.reply_to(message, text)

@bot.message_handler(commands=['user_', 'userhistory_', 'allow_', 'deny_'])
def cmd_admin_with_id(message):
    if message.from_user.id != ADMIN_ID:
        return
    cmd = message.text.split('_')[0].replace('/', '')
    try:
        uid = int(message.text.split('_')[1].strip())
    except:
        bot.reply_to(message, "Используй: /user_ID, /userhistory_ID, /allow_ID, /deny_ID")
        return
    if cmd == 'user':
        info = get_user_info(uid)
        if not info:
            bot.reply_to(message, "Пользователь не найден.")
            return
        text = f"📊 Пользователь:\nID: {info[0]}\nИмя: {info[1]}\n@{info[2] or '—'}\nПервый раз: {info[3]}\nПоследний раз: {info[4]}\nСообщений: {info[5]}\nРоль: {info[6]}"
        bot.reply_to(message, text)
    elif cmd == 'userhistory':
        history = get_user_history(uid, 50)
        if not history:
            bot.reply_to(message, "История пуста.")
            return
        text = f"📝 Переписка с {uid}:\n\n"
        for h in history:
            role = "👤" if h[1] == "user" else "🤖"
            text += f"{role} {h[0][:100]}\n\n"
        bot.reply_to(message, text[:4000])
    elif cmd == 'allow':
        add_whitelist(uid)
        bot.reply_to(message, f"Пользователь {uid} добавлен в whitelist.")
    elif cmd == 'deny':
        remove_whitelist(uid)
        bot.reply_to(message, f"Пользователь {uid} убран из whitelist.")

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    stats = get_stats()
    if not stats:
        bot.reply_to(message, "Ошибка.")
        return
    bot.reply_to(message, f"📊 Статистика:\n👥 Пользователей: {stats[0]}\n💬 Сообщений: {stats[1]}")

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(message, "Используй: /broadcast [текст]")
        return
    users = get_users()
    count = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 Обновление Эви:\n\n{text}")
            count += 1
        except:
            pass
    bot.reply_to(message, f"Рассылка отправлена {count} пользователям.")

@bot.message_handler(commands=['whitelist_on'])
def cmd_whitelist_on(message):
    if message.from_user.id != ADMIN_ID:
        return
    set_whitelist_on('1')
    bot.reply_to(message, "Whitelist включён. Только разрешённые могут писать.")

@bot.message_handler(commands=['whitelist_off'])
def cmd_whitelist_off(message):
    if message.from_user.id != ADMIN_ID:
        return
    set_whitelist_on('0')
    bot.reply_to(message, "Whitelist выключен. Все могут писать.")

# ==== ОСНОВНАЯ ЛОГИКА ====
@bot.message_handler(func=lambda m: True, content_types=['text'])
def reply(message):
    chat_id = message.chat.id
    text = message.text or ""
    text_lower = text.lower().strip()
    user_id = message.from_user.id

    save_user(user_id, message.from_user.first_name, message.from_user.username)

    if is_whitelist_on() and user_id != ADMIN_ID and not is_whitelisted(user_id):
        return

    if chat_id in muted_chats:
        for phrase in UNMUTE_PHRASES:
            if phrase in text_lower:
                muted_chats.discard(chat_id)
                bot.reply_to(message, "Я вернулась! 😼")
                return
        return

    for phrase in MUTE_PHRASES:
        if phrase in text_lower:
            muted_chats.add(chat_id)
            bot.reply_to(message, "Ок, молчу 🤐 Напиши 'Эви, вернись'.")
            return

    bot_username = bot.get_me().username
    mentioned = f"@{bot_username}" in text or text_lower.startswith("эви") or "эви," in text_lower
    is_group = message.chat.type in ['group', 'supergroup']

    if is_group and not mentioned:
        save_message(user_id, chat_id, text, "user")
        return

    clean_text = text.replace(f"@{bot_username}", "").strip()
    if clean_text.lower().startswith("эви"):
        clean_text = clean_text[3:].strip(" ,.!?")

    if not clean_text:
        clean_text = "Привет!"

    mode = modes.get(chat_id, "normal")
    personality = PERSONALITIES.get(mode, PERSONALITIES["normal"])

    system_prompt = BASE_PROMPT + "\n" + personality

    if chat_id in rp_mode:
        system_prompt += "\n" + RP_PROMPT
        bot_anketa = get_anketa(ADMIN_ID, is_bot=True)
        user_anketa = get_anketa(user_id, is_bot=False)
        if bot_anketa:
            system_prompt += f"\nТвой персонаж: {bot_anketa}"
        if user_anketa:
            system_prompt += f"\nПерсонаж игрока: {user_anketa}"
    else:
        if "объясни" in text_lower:
            system_prompt += "\n" + EXPLAIN_PROMPT
        if "проанализируй" in text_lower or "анализ" in text_lower:
            system_prompt += "\n" + ANALYZE_PROMPT
        if "домашк" in text_lower or "дз" in text_lower:
            system_prompt += "\n" + HOMEWORK_PROMPT

    if user_id == ADMIN_ID:
        system_prompt += "\n" + ADMIN_EXTRA
    else:
        system_prompt += f"\nТы общаешься с {message.from_user.first_name}."

    memory = get_memory(chat_id, 50)
    messages_list = [{"role": "system", "content": system_prompt}]
    messages_list.extend(memory)
    messages_list.append({"role": "user", "content": clean_text})

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages_list,
            max_tokens=2000
        )
        answer = response.choices[0].message.content
        if not answer or not answer.strip():
            answer = "Хм, задумалась 🤔 Попробуй ещё раз."
        bot.reply_to(message, answer)
        save_message(user_id, chat_id, clean_text, "user")
        save_message(0, chat_id, answer, "assistant")
    except Exception as e:
        bot.reply_to(message, f"Ой, у меня сбой: {e}")

# ==== ЗАПУСК ====
init_db()
print("Эви запущена! Пакет 3 + полировка.")
bot.polling(none_stop=True)
