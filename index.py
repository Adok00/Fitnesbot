import telebot
import sqlite3
from telebot import types
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Инициализация бота
bot = telebot.TeleBot('7691058473:AAEwS77CoSmlkkm3pNvic5PPvU0HKf8Lbg4')

# Ваш chat_id как администратора
ADMIN_CHAT_ID = 330908912


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Создание таблицы, если она еще не существует
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (chat_id INTEGER PRIMARY KEY, 
                  age INTEGER, 
                  weight REAL, 
                  height REAL, 
                  goal TEXT, 
                  dislikes TEXT, 
                  injuries TEXT, 
                  equipment TEXT, 
                  workout_freq INTEGER, 
                  plan TEXT)''')

    # Проверка наличия столбца paid и добавление, если его нет
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if 'paid' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN paid INTEGER DEFAULT 0")

    # Изначально вы — оплаченный пользователь
    c.execute("INSERT OR IGNORE INTO users (chat_id, paid) VALUES (?, 1)", (ADMIN_CHAT_ID,))
    conn.commit()
    conn.close()


# Простая генерация плана
def generate_plan(data):
    username = data.get('username', 'друг')
    greeting = f"Привет, @{username}! Вот твой план:\n\n"

    if "похудеть" in data['goal'].lower():
        calories = 1800
        goal_text = "похудения"
    elif "набрать" in data['goal'].lower():
        calories = 2500
        goal_text = "набора массы"
    else:
        calories = 2000
        goal_text = "поддержания формы"

    workout_text = f"Тренировки ({data['workout_freq']} раз в неделю):\n"
    if data['workout_freq'] >= 3:
        workout_text += "- Приседания (3x10), отжимания (3x15), планка (3x30 сек)\n"
        if data['equipment'] != "ничего":
            workout_text += f"- С {data['equipment']}: подтягивания или жим (3x8)\n"
    else:
        workout_text += "- Ходьба или растяжка (20-30 мин)\n"

    if data['injuries'] != "нет":
        workout_text += f"Учти травмы: {data['injuries']}\n"

    food_text = f"Питание ({calories} ккал):\n"
    food_text += "- Завтрак: овсянка (200 г), яйцо\n"
    food_text += "- Обед: курица (150 г), рис (100 г)\n"
    food_text += "- Ужин: рыба (120 г), гречка (80 г)\n"
    if data['dislikes'] and data['dislikes'] != "ничего":
        food_text += f"Без {data['dislikes']}\n"

    return greeting + f"Цель: {goal_text}\n\n" + workout_text + "\n" + food_text


# Хранилище данных пользователей
user_data = {}


# Стартовая команда
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'username': message.from_user.username or "друг"}
    bot.send_message(chat_id, "Сколько тебе лет?")
    bot.register_next_step_handler(message, get_age)


# Сбор данных
def get_age(message):
    chat_id = message.chat.id
    text = message.text.strip()  # Удаляем пробелы в начале и конце
    try:
        # Проверяем, что введено только число
        if not text.isdigit():
            raise ValueError("Введено не число")

        age = int(text)
        if 10 <= age <= 100:
            user_data[chat_id]['age'] = age
            bot.send_message(chat_id, "Вес (кг) и рост (см) через пробел, например: 70 175")
            bot.register_next_step_handler(message, get_weight_height)
        else:
            bot.send_message(chat_id, "Возраст должен быть от 10 до 100 лет!")
            bot.register_next_step_handler(message, get_age)
    except ValueError:
        bot.send_message(chat_id, "Пожалуйста, введи возраст числом (например, 25)!")
        bot.register_next_step_handler(message, get_age)


def get_weight_height(message):
    chat_id = message.chat.id
    try:
        weight, height = map(float, message.text.split())
        if 30 <= weight <= 300 and 100 <= height <= 250:
            user_data[chat_id]['weight'] = weight
            user_data[chat_id]['height'] = height
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Похудеть", callback_data="goal_похудеть"))
            markup.add(types.InlineKeyboardButton("Набрать мышцы", callback_data="goal_набрать"))
            markup.add(types.InlineKeyboardButton("Поддерживать форму", callback_data="goal_поддерживать"))
            bot.send_message(chat_id, "Твоя цель?", reply_markup=markup)
        else:
            bot.send_message(chat_id, "Вес должен быть 30–300 кг, рост 100–250 см!")
            bot.register_next_step_handler(message, get_weight_height)
    except ValueError:
        bot.send_message(chat_id, "Введи вес и рост числами через пробел (например, 70 175)!")
        bot.register_next_step_handler(message, get_weight_height)


@bot.callback_query_handler(func=lambda call: call.data.startswith("goal_"))
def get_goal(call):
    chat_id = call.message.chat.id
    goal = call.data.split("_")[1]
    user_data[chat_id]['goal'] = goal
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"Цель: {goal}")
    bot.send_message(chat_id, "Что не любишь в еде? (через запятую или 'ничего')")
    bot.register_next_step_handler(call.message, get_dislikes)


def get_dislikes(message):
    chat_id = message.chat.id
    user_data[chat_id]['dislikes'] = message.text
    bot.send_message(chat_id, "Травмы? (опиши или 'нет')")
    bot.register_next_step_handler(message, get_injuries)


def get_injuries(message):
    chat_id = message.chat.id
    user_data[chat_id]['injuries'] = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Гантели", callback_data="equip_гантели"))
    markup.add(types.InlineKeyboardButton("Турник", callback_data="equip_турник"))
    markup.add(types.InlineKeyboardButton("Ничего", callback_data="equip_ничего"))
    bot.send_message(chat_id, "Оборудование?", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("equip_"))
def get_equipment(call):
    chat_id = call.message.chat.id
    equipment = call.data.split("_")[1]
    user_data[chat_id]['equipment'] = equipment
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"Оборудование: {equipment}")
    bot.send_message(chat_id, "Сколько раз в неделю будешь заниматься?")
    bot.register_next_step_handler(call.message, get_workout_freq)


def get_workout_freq(message):
    chat_id = message.chat.id
    try:
        freq = int(message.text)
        if 1 <= freq <= 7:
            user_data[chat_id]['workout_freq'] = freq
            plan = generate_plan(user_data[chat_id])

            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO users 
                         (chat_id, age, weight, height, goal, dislikes, injuries, equipment, workout_freq, plan) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (chat_id, user_data[chat_id]['age'], user_data[chat_id]['weight'],
                       user_data[chat_id]['height'], user_data[chat_id]['goal'],
                       user_data[chat_id]['dislikes'], user_data[chat_id]['injuries'],
                       user_data[chat_id]['equipment'], user_data[chat_id]['workout_freq'], plan))
            conn.commit()
            conn.close()

            if chat_id == ADMIN_CHAT_ID:
                bot.send_message(chat_id, f"{plan}\n\nТы уже в списке оплаченных!")
            else:
                bot.send_message(chat_id,
                                 "План готов! Стоимость: 5000 тенге. Оплати на карту Visa: 8778 648 44 86 и отправь чек через /confirm.")
        else:
            bot.send_message(chat_id, "От 1 до 7 тренировок!")
            bot.register_next_step_handler(message, get_workout_freq)
    except ValueError:
        bot.send_message(chat_id, "Число тренировок — число!")
        bot.register_next_step_handler(message, get_workout_freq)


# Подтверждение оплаты
@bot.message_handler(commands=['confirm'])
def confirm_payment(message):
    chat_id = message.chat.id
    if chat_id == ADMIN_CHAT_ID:
        bot.send_message(chat_id, "Ты уже оплачен!")
        return

    bot.send_message(chat_id, "Отправь скриншот оплаты.")
    bot.register_next_step_handler(message, process_payment_proof)


def process_payment_proof(message):
    chat_id = message.chat.id
    if message.photo or message.document:
        # Отправка уведомления администратору
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Да", callback_data=f"approve_{chat_id}"))
        if message.photo:
            bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id,
                           caption=f"Чек от @{message.from_user.username} (chat_id: {chat_id}). Подтвердить?",
                           reply_markup=markup)
        elif message.document:
            bot.send_document(ADMIN_CHAT_ID, message.document.file_id,
                              caption=f"Чек от @{message.from_user.username} (chat_id: {chat_id}). Подтвердить?",
                              reply_markup=markup)
        bot.send_message(chat_id, "Чек отправлен. Жди подтверждения!")
    else:
        bot.send_message(chat_id, "Отправь фото или документ!")
        bot.register_next_step_handler(message, process_payment_proof)


# Обработка подтверждения администратором
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_payment(call):
    if call.message.chat.id != ADMIN_CHAT_ID:
        return

    user_chat_id = int(call.data.split("_")[1])
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET paid = 1 WHERE chat_id = ?", (user_chat_id,))
    c.execute("SELECT plan FROM users WHERE chat_id = ?", (user_chat_id,))
    plan = c.fetchone()
    conn.commit()
    conn.close()

    if plan:
        bot.send_message(user_chat_id, f"Оплата подтверждена! Вот твой план:\n{plan[0]}")
        bot.edit_message_caption(chat_id=ADMIN_CHAT_ID, message_id=call.message.message_id,
                                 caption="Оплата подтверждена!")
    else:
        bot.send_message(user_chat_id, "Ошибка: план не найден. Напиши /start заново.")


# Просмотр плана
@bot.message_handler(commands=['myplan'])
def my_plan(message):
    chat_id = message.chat.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT plan, paid FROM users WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()

    if result:
        plan, paid = result
        if paid:
            bot.send_message(chat_id, plan)
        else:
            bot.send_message(chat_id,
                             "Ты еще не оплатил. Оплати на карту Visa: 8778 648 44 86 и отправь чек через /confirm.")
    else:
        bot.send_message(chat_id, "Создай план через /start!")


# Команда для проверки статуса пользователей (только для админа)
@bot.message_handler(commands=['status'])
def check_status(message):
    chat_id = message.chat.id
    if chat_id != ADMIN_CHAT_ID:
        bot.send_message(chat_id, "Эта команда доступна только администратору!")
        return

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT chat_id, paid FROM users")
    users = c.fetchall()
    conn.close()

    if not users:
        bot.send_message(chat_id, "В базе данных пока нет пользователей.")
        return

    status_message = "Статус пользователей:\n\n"
    for user in users:
        user_chat_id, paid = user
        # Получаем username через API Telegram
        try:
            user_info = bot.get_chat(user_chat_id)
            username = user_info.username if user_info.username else "Нет username"
        except Exception as e:
            username = "Не удалось получить username"
            logging.error(f"Ошибка получения username для chat_id {user_chat_id}: {e}")

        status = "Оплачено" if paid else "Не оплачено"
        status_message += f"Chat ID: {user_chat_id}, Username: @{username}, Статус: {status}\n"

    bot.send_message(chat_id, status_message)


# Запуск
if __name__ == '__main__':
    init_db()
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Ошибка: {e}")