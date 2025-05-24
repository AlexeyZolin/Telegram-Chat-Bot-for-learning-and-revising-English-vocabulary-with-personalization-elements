import telebot
from telebot import types
import re
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import datetime

TOKEN = "5584345667:AAFw-O7TloHMPVrQxeqeKDzA-nrWQTY4Fd4"
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения данных пользователей (уровень, тема, текущее задание, счёт и т.д.) в формате {user_id: user_info}
user_data = {}


# Клавиатуры
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Я знаю свой уровень"), types.KeyboardButton("Я не знаю свой уровень"))
    return markup


def get_levels():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("A1-A2"), types.KeyboardButton("B1-B2"))
    return markup


def get_topics():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Family and Friends"), types.KeyboardButton("Skills and Hobbies"),
               types.KeyboardButton("Education and Studying"), types.KeyboardButton("Work and Jobs"),
               types.KeyboardButton("Daily life and routine"), types.KeyboardButton("Travelling and Transport"),
               types.KeyboardButton("Health and Medicine"), types.KeyboardButton("Shopping"),
               types.KeyboardButton("Food"))
    return markup


def get_task_types():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("На основе текста"),
        types.KeyboardButton("На основе аудио"),
        types.KeyboardButton("На основе изображения")
    )
    return markup


# Инициализация планировщика
scheduler = BackgroundScheduler()
scheduler.start()

# Команда для настройки напоминаний
@bot.message_handler(commands=['setreminders'])
def set_reminder_command(message):
    user_id = message.chat.id

    # Создаем клавиатуру для выбора времени
    markup = types.InlineKeyboardMarkup(row_width=3)

    # Добавляем кнопки с разным временем
    times = [
        ("🌅 Утро (8:00)", "8"),
        ("☀️ День (12:00)", "12"),
        ("🌆 Вечер (18:00)", "18"),
        ("🌙 Ночь (21:00)", "21"),
        ("⏰ Другое время", "custom")
    ]

    for text, time in times:
        markup.add(types.InlineKeyboardButton(text, callback_data=f"reminder_time_{time}"))

    bot.send_message(
        user_id,
        "⏰ <b>Настройте ежедневные напоминания</b>\n\n"
        "Выберите удобное время для занятий английским:",
        reply_markup=markup,
        parse_mode='HTML'
    )


# Обработчик для выбора стандартного времени
@bot.callback_query_handler(
    func=lambda call: call.data.startswith('reminder_time_') and call.data.split('_')[2] != 'custom')
def set_standard_reminder(call):
    user_id = call.message.chat.id
    hour = int(call.data.split('_')[2])

    # Удаляем старые напоминания для этого пользователя
    remove_existing_reminders(user_id)

    # Добавляем новое напоминание
    add_reminder_job(user_id, hour,0)

    # Отправляем подтверждение
    bot.edit_message_text(
        f"✅ Напоминание установлено на {hour:02d}:00 каждый день.\n"
        "Вы всегда можете изменить его командой /setreminders \n"
        "Также можно отключить его командой /stopreminders",
        chat_id=user_id,
        message_id=call.message.message_id
    )


# Обработчик для выбора своего времени
@bot.callback_query_handler(func=lambda call: call.data == 'reminder_time_custom')
def ask_custom_time(call):
    user_id = call.message.chat.id
    msg = bot.send_message(
        user_id,
        "⌨️ Введите время в формате ЧЧ:ММ (например, 09:30 или 17:45):"
    )
    bot.register_next_step_handler(msg, process_custom_time)


def process_custom_time(message):
    user_id = message.chat.id
    try:
        # Парсим введенное время
        time_str = message.text.strip()
        hour, minute = map(int, time_str.split(':'))

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError

        # Удаляем старые напоминания
        remove_existing_reminders(user_id)

        # Добавляем новое напоминание
        add_reminder_job(user_id, hour, minute)

        bot.send_message(
            user_id,
            f"✅ Напоминание установлено на {hour:02d}:{minute:02d} каждый день.\n"
            "Изменить: /setreminders"
        )
    except:
        bot.send_message(
            user_id,
            "❌ Неверный формат времени. Пожалуйста, введите время в формате ЧЧ:ММ (например, 09:30).\n"
            "Попробуйте снова: /setreminders"
        )


# Команда для отключения напоминаний
@bot.message_handler(commands=['stopreminders'])
def stop_reminders_command(message):
    user_id = message.chat.id
    removed = remove_existing_reminders(user_id)

    if removed:
        bot.send_message(user_id, "🔕 Напоминания отключены. Включить снова: /setreminders")
    else:
        bot.send_message(user_id, "ℹ️ У вас нет активных напоминаний. Установить: /setreminders")


# Вспомогательные функции
def remove_existing_reminders(user_id):
    removed = False
    for job in scheduler.get_jobs():
        if job.name == f"reminder_{user_id}":
            job.remove()
            removed = True
    return removed


def add_reminder_job(user_id, hour, minute):
    scheduler.add_job(
        send_reminder_notification,
        trigger=CronTrigger(hour=hour, minute=minute),
        args=[user_id],
        name=f"reminder_{user_id}",
        id=f"reminder_{user_id}_{hour}_{minute}",
        replace_existing=True
    )


def send_reminder_notification(user_id):
    try:
        # Создаем клавиатуру с быстрыми действиями
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 Отложить на 1 час", callback_data="snooze_reminder")
        )

        bot.send_message(
            user_id,
            "⏰ <b>Время заниматься английским!</b>\n\n"
            "Не откладывайте на завтра то, что можно сделать сегодня! 🚀\n"
            "Попробуйте выполнить несколько заданий или выучить новые слова.",
            reply_markup=markup,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Ошибка отправки напоминания: {e}")


@bot.callback_query_handler(func=lambda call: call.data == 'snooze_reminder')
def handle_snooze(call):
    user_id = call.message.chat.id
    bot.edit_message_text(
        "Хорошо, напомню вам через час 👍",
        chat_id=user_id,
        message_id=call.message.message_id
    )
    # Добавляем отложенное напоминание
    scheduler.add_job(
        send_reminder_notification,
        trigger=CronTrigger(minute=datetime.datetime.now().minute, hour=datetime.datetime.now().hour + 1),
        args=[user_id],
        id=f"snooze_{user_id}_{datetime.datetime.now().timestamp()}",
        replace_existing=True
    )

# --- Обработчики команд ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"Добрый день, {message.from_user.first_name}! Знаете ли вы свой примерный уровень владения английским языком?",
                     reply_markup=get_main_menu())


@bot.message_handler(func=lambda message: message.text == "Я не знаю свой уровень")
def unknown_level(message):
    bot.send_message(message.chat.id,
                     "В таком случае пройдите, пожалуйста, короткий тест для определения примерного уровня: https://www.cambridgeenglish.org/test-your-english/general-english/")
    bot.send_message(message.chat.id, "Знаете ли вы свой уровень теперь?", reply_markup=get_main_menu())


@bot.message_handler(func=lambda message: message.text == "Я знаю свой уровень")
def known_level(message):
    bot.send_message(message.chat.id, "Выберите ваш уровень:", reply_markup=get_levels())


@bot.message_handler(func=lambda message: message.text in ["A1-A2", "B1-B2"])
def choose_topic_level(message):
    user_data[message.chat.id] = {"level": message.text, "current_task": 1, "score": 0}
    bot.send_message(message.chat.id, "Выберите тему:", reply_markup=get_topics())


@bot.message_handler(func=lambda message: message.text in [
    "Family and Friends", "Skills and Hobbies", "Education and Studying",
    "Work and Jobs", "Daily life and routine", "Travelling and Transport",
    "Health and Medicine", "Shopping", "Food"
])
def choose_topic(message):
    user_id = message.chat.id
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id].update({
        "topic": message.text,
        "current_task": 1,
        "score": 0
    })
    bot.send_message(user_id, f"Вы выбрали тему: {message.text}. Теперь выберите тип задания:",
                     reply_markup=get_task_types())


@bot.message_handler(
    func=lambda message: message.text in ["На основе текста", "На основе аудио", "На основе изображения"]
)
def choose_task_type(message):
    user_id = message.chat.id
    if user_id in user_data and "topic" in user_data[user_id]:
        user_data[user_id]["task_type"] = message.text
        # Устанавливаем количество заданий в зависимости от типа
        if message.text == "На основе изображения":
            user_data[user_id]["total_tasks"] = 3
        else:
            user_data[user_id]["total_tasks"] = 5

        topic = user_data[user_id]["topic"]
        task_type = message.text
        bot.send_message(user_id, f"Вы выбрали задания '{task_type}' по теме '{topic}'. Начинаем!")
        send_task(user_id)
    else:
        bot.send_message(user_id, "Ошибка: сначала выберите тему!", reply_markup=get_topics())


@bot.message_handler(commands=['a1a2'])
def handle_a1a2(message):
    user_id = message.chat.id
    user_data[user_id] = {"level": "A1-A2", "current_task": 1, "score": 0}
    bot.send_message(user_id, "Вы выбрали уровень A1-A2. Теперь выберите тему:",
                    reply_markup=get_topics())

@bot.message_handler(commands=['b1b2'])
def handle_b1b2(message):
    user_id = message.chat.id
    user_data[user_id] = {"level": "B1-B2", "current_task": 1, "score": 0}
    bot.send_message(user_id, "Вы выбрали уровень B1-B2. Теперь выберите тему:",
                    reply_markup=get_topics())


def send_task(user_id):
    if user_id not in user_data:
        return

    user_info = user_data[user_id]
    topic = user_info.get("topic")
    task_type = user_info.get("task_type")
    level = user_info.get("level", "A1-A2")
    current_task = user_info.get("current_task", 1)

    # Family and Friends - Text tasks
    if topic == "Family and Friends" and task_type == "На основе текста":
        if level == "A1-A2":
            send_text_task_family_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_text_task_family_b1b2(user_id, current_task)

    # Family and Friends - Image Tasks
    if topic == "Family and Friends" and task_type == "На основе изображения":
        if level == "A1-A2":
            send_image_task_family_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_image_task_family_b1b2(user_id, current_task)

    # Family and Friends - Audio tasks
    if topic == "Family and Friends" and task_type == "На основе аудио":
        if level == "A1-A2":
            send_audio_task_family_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_audio_task_family_b1b2(user_id, current_task)

    # Skills and Hobbies - Text tasks
    if topic == "Skills and Hobbies" and task_type == "На основе текста":
        if level == "A1-A2":
            send_text_task_skills_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_text_task_skills_b1b2(user_id, current_task)

    # Skills and Hobbies - Image Tasks
    if topic == "Skills and Hobbies" and task_type == "На основе изображения":
        if level == "A1-A2":
            send_image_task_skills_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_image_task_skills_b1b2(user_id, current_task)

    # Skills and Hobbies - Audio tasks
    if topic == "Skills and Hobbies" and task_type == "На основе аудио":
        if level == "A1-A2":
            send_audio_task_skills_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_audio_task_skills_b1b2(user_id, current_task)

    # Education and Studying - Text tasks
    if topic == "Education and Studying" and task_type == "На основе текста":
        if level == "A1-A2":
            send_text_task_education_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_text_task_education_b1b2(user_id, current_task)

    # Education and Studying - Image Tasks
    if topic == "Education and Studying" and task_type == "На основе изображения":
        if level == "A1-A2":
            send_image_task_education_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_image_task_education_b1b2(user_id, current_task)

    # Education and Studying - Audio tasks
    if topic == "Education and Studying" and task_type == "На основе аудио":
        if level == "A1-A2":
            send_audio_task_education_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_audio_task_education_b1b2(user_id, current_task)

    # Work and Jobs - Text tasks
    if topic == "Work and Jobs" and task_type == "На основе текста":
        if level == "A1-A2":
            send_text_task_work_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_text_task_work_b1b2(user_id, current_task)

    # Work and Jobs - Image Tasks
    if topic == "Work and Jobs" and task_type == "На основе изображения":
        if level == "A1-A2":
            send_image_task_work_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_image_task_work_b1b2(user_id, current_task)

    # Work and Jobs - Audio tasks
    if topic == "Work and Jobs" and task_type == "На основе аудио":
        if level == "A1-A2":
            send_audio_task_work_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_audio_task_work_b1b2(user_id, current_task)

    # Daily life and routine - Text tasks
    if topic == "Daily life and routine" and task_type == "На основе текста":
        if level == "A1-A2":
            send_text_task_daily_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_text_task_daily_b1b2(user_id, current_task)

    # Daily life and routine - Image Tasks
    if topic == "Daily life and routine" and task_type == "На основе изображения":
        if level == "A1-A2":
            send_image_task_daily_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_image_task_daily_b1b2(user_id, current_task)

    # Daily life and routine - Audio tasks
    if topic == "Daily life and routine" and task_type == "На основе аудио":
        if level == "A1-A2":
            send_audio_task_daily_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_audio_task_daily_b1b2(user_id, current_task)

    # Travelling and Transport - Text tasks
    if topic == "Travelling and Transport" and task_type == "На основе текста":
        if level == "A1-A2":
            send_text_task_travel_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_text_task_travel_b1b2(user_id, current_task)

    # Travelling and Transport - Image Tasks
    if topic == "Travelling and Transport" and task_type == "На основе изображения":
        if level == "A1-A2":
            send_image_task_travel_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_image_task_travel_b1b2(user_id, current_task)

    # Travelling and Transport - Audio tasks
    if topic == "Travelling and Transport" and task_type == "На основе аудио":
        if level == "A1-A2":
            send_audio_task_travel_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_audio_task_travel_b1b2(user_id, current_task)

    # Health and Medicine - Text tasks
    if topic == "Health and Medicine" and task_type == "На основе текста":
        if level == "A1-A2":
            send_text_task_health_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_text_task_health_b1b2(user_id, current_task)

    # Health and Medicine - Image Tasks
    if topic == "Health and Medicine" and task_type == "На основе изображения":
        if level == "A1-A2":
            send_image_task_health_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_image_task_health_b1b2(user_id, current_task)

    # Health and Medicine - Audio tasks
    if topic == "Health and Medicine" and task_type == "На основе аудио":
        if level == "A1-A2":
            send_audio_task_health_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_audio_task_health_b1b2(user_id, current_task)

    # Shopping - Text tasks
    if topic == "Shopping" and task_type == "На основе текста":
        if level == "A1-A2":
            send_text_task_shopping_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_text_task_shopping_b1b2(user_id, current_task)

    # Shopping - Image Tasks
    if topic == "Shopping" and task_type == "На основе изображения":
        if level == "A1-A2":
            send_image_task_shopping_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_image_task_shopping_b1b2(user_id, current_task)

    # Shopping - Audio tasks
    if topic == "Shopping" and task_type == "На основе аудио":
        if level == "A1-A2":
            send_audio_task_shopping_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_audio_task_shopping_b1b2(user_id, current_task)

    # Food - Text tasks
    if topic == "Food" and task_type == "На основе текста":
        if level == "A1-A2":
            send_text_task_food_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_text_task_food_b1b2(user_id, current_task)

    # Food - Image Tasks
    if topic == "Food" and task_type == "На основе изображения":
        if level == "A1-A2":
            send_image_task_food_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_image_task_food_b1b2(user_id, current_task)

    # Food - Audio tasks
    if topic == "Food" and task_type == "На основе аудио":
        if level == "A1-A2":
            send_audio_task_food_a1a2(user_id, current_task)
        elif level == "B1-B2":
            send_audio_task_food_b1b2(user_id, current_task)


# ==============================================
# Family and Friends - Text Tasks (A1-A2)
# ==============================================
def send_text_task_family_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('mother', callback_data='family_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('father', callback_data='family_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('stranger', callback_data='family_a1a2_correct_1')
        btn4 = types.InlineKeyboardButton('brother', callback_data='family_a1a2_wrong_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Выберите лишнее из списка:", reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Составьте предложение из слов:\n\n My, helps, sister, do, me, homework, my.",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_family_a1a2_2(m, user_id))

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("mother", callback_data="family_a1a2_correct_3")
        btn2 = types.InlineKeyboardButton("book", callback_data="family_a1a2_wrong_3")
        btn3 = types.InlineKeyboardButton("car", callback_data="family_a1a2_wrong_3")
        btn4 = types.InlineKeyboardButton("house", callback_data="family_a1a2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> Выберите правильный вариант для заполнения пропуска в предложении:\n\n"
                                  "This is my ________. She is very kind.",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("sad", callback_data="family_a1a2_correct_4")
        btn2 = types.InlineKeyboardButton("tall", callback_data="family_a1a2_wrong_4")
        btn3 = types.InlineKeyboardButton("fast", callback_data="family_a1a2_wrong_4")
        btn4 = types.InlineKeyboardButton("small", callback_data="family_a1a2_wrong_4")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>4/5.</b> Подберите антоним для слова <b>happy</b>:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        text = """<b>5/5.</b> Прочитайте текст и выберите правильное утверждение:\n\n
My name is Anna. I have a small family. There are four people in my family: my father, my mother, my brother, and me. My father's name is John. He is a teacher. My mother's name is Mary. She is a doctor. My brother's name is Tom. He is 10 years old. We like to spend time together, especially on weekends.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Anna has a big family.", callback_data="family_a1a2_wrong_5")
        btn2 = types.InlineKeyboardButton("Anna's father is a doctor.", callback_data="family_a1a2_wrong_5")
        btn3 = types.InlineKeyboardButton("Her brother's name is Tom.", callback_data="family_a1a2_correct_5")
        btn4 = types.InlineKeyboardButton("They don't spend time together.", callback_data="family_a1a2_wrong_5")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')


def check_text_task_family_a1a2_2(message, user_id):
    correct_sentence = "my sister helps me do my homework"
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer == correct_sentence:
        bot.send_message(user_id, "✅ Верно! Правильное предложение: 'My sister helps me do my homework.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Неправильно. Попробуйте ещё раз!")
        send_text_task_family_a1a2(user_id, 2)


# ==============================================
# Family and Friends - Text Tasks (B1-B2)
# ==============================================
def send_text_task_family_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('nephew', callback_data='family_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('niece', callback_data='family_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('cousin', callback_data='family_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('colleague', callback_data='family_b1b2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Choose the odd one out:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Make a sentence using these words:\n\nfamily, reunion, annual, our, next, is, week",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_family_b1b2_2(m, user_id))

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("generation gap", callback_data="family_b1b2_correct_3")
        btn2 = types.InlineKeyboardButton("age difference", callback_data="family_b1b2_wrong_3")
        btn3 = types.InlineKeyboardButton("time distance", callback_data="family_b1b2_wrong_3")
        btn4 = types.InlineKeyboardButton("year space", callback_data="family_b1b2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> Choose the correct option to fill in the gap:\n\n"
                                  "There is a ________ between my grandparents and me - we have very different views.",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        text = """<b>4/5.</b> Read the text and answer the question:\n\n
In many cultures, extended families live together, including grandparents, aunts, uncles and cousins. This family structure provides strong support systems but can also lead to conflicts due to different generations living under one roof.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Extended families always live harmoniously.",
                                          callback_data="family_b1b2_wrong_4")
        btn2 = types.InlineKeyboardButton("Extended families consist only of parents and children.",
                                          callback_data="family_b1b2_wrong_4")
        btn3 = types.InlineKeyboardButton("Extended families can experience generational conflicts.",
                                          callback_data="family_b1b2_correct_4")
        btn4 = types.InlineKeyboardButton("Extended families are rare in modern societies.",
                                          callback_data="family_b1b2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        text = """<b>5/5.</b> Read the text and choose the correct statement:\n\n
Nuclear families, consisting of parents and their children, have become more common in industrialized societies. This shift is often attributed to urbanization and the increasing mobility of the workforce. While nuclear families offer more privacy, they may lack the extensive support network of extended families.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Nuclear families are less common now than before.",
                                          callback_data="family_b1b2_wrong_5")
        btn2 = types.InlineKeyboardButton("Nuclear families consist of multiple generations.",
                                          callback_data="family_b1b2_wrong_5")
        btn3 = types.InlineKeyboardButton("Urbanization has contributed to the rise of nuclear families.",
                                          callback_data="family_b1b2_correct_5")
        btn4 = types.InlineKeyboardButton("Nuclear families provide more support than extended families.",
                                          callback_data="family_b1b2_wrong_5")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')


def check_text_task_family_b1b2_2(message, user_id):
    correct_answers = [
        "our annual family reunion is next week",
        "the annual family reunion is next week",
        "next week is our annual family reunion"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Correct! A possible answer: 'Our annual family reunion is next week.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Incorrect. Try again!")
        send_text_task_family_b1b2(user_id, 2)


# ==============================================
# Skills and Hobbies - Text Tasks (A1-A2)
# ==============================================
def send_text_task_skills_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('swimming', callback_data='skills_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('reading', callback_data='skills_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('cooking', callback_data='skills_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('cleaning', callback_data='skills_a1a2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Выберите лишнее из списка:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id, "<b>2/5.</b> Составьте предложение из слов:\n\nplay, I, guitar, the, can",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_skills_a1a2_2(m, user_id))

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("drawing", callback_data="skills_a1a2_correct_3")
        btn2 = types.InlineKeyboardButton("eating", callback_data="skills_a1a2_wrong_3")
        btn3 = types.InlineKeyboardButton("sleeping", callback_data="skills_a1a2_wrong_3")
        btn4 = types.InlineKeyboardButton("showering", callback_data="skills_a1a2_wrong_3")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>3/5.</b> Какое из этих занятий считается хобби?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        text = """<b>4/5.</b> Прочитайте текст и выберите верное утверждение:\n\n
My hobby is photography. I like taking pictures of nature. I have a small camera. On weekends, I go to the park to take photos.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("I like taking pictures of cars.", callback_data="skills_a1a2_wrong_4")
        btn2 = types.InlineKeyboardButton("My hobby is photography.", callback_data="skills_a1a2_correct_4")
        btn3 = types.InlineKeyboardButton("I go to the park every day.", callback_data="skills_a1a2_wrong_4")
        btn4 = types.InlineKeyboardButton("I have a big camera.", callback_data="skills_a1a2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("hobby", callback_data="skills_a1a2_correct_5")
        btn2 = types.InlineKeyboardButton("job", callback_data="skills_a1a2_wrong_5")
        btn3 = types.InlineKeyboardButton("work", callback_data="skills_a1a2_wrong_5")
        btn4 = types.InlineKeyboardButton("task", callback_data="skills_a1a2_wrong_5")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>5/5.</b> Какое слово означает занятие для удовольствия в свободное время?",
                         reply_markup=markup, parse_mode='html')


def check_text_task_skills_a1a2_2(message, user_id):
    correct_answers = [
        "i can play the guitar",
        "can i play the guitar"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Верно! Один из возможных вариантов: 'I can play the guitar.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Неправильно. Попробуйте ещё раз!")
        send_text_task_skills_a1a2(user_id, 2)


# ==============================================
# Skills and Hobbies - Text Tasks (B1-B2)
# ==============================================
def send_text_task_skills_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('knitting', callback_data='skills_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('woodworking', callback_data='skills_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('pottery', callback_data='skills_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('watching TV', callback_data='skills_b1b2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Choose the least active hobby from the list:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Make a sentence using these words:\n\nimprove, practice, to, need, your, You, regularly, skills, to",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_skills_b1b2_2(m, user_id))

    elif task_num == 3:
        text = """<b>3/5.</b> Read the text and choose the correct statement:\n\n
Developing new skills can enhance cognitive function and mental wellbeing. Studies show that learning activities like playing musical instruments or speaking foreign languages can create new neural pathways in the brain.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Learning new skills has no effect on the brain.",
                                          callback_data="skills_b1b2_wrong_3")
        btn2 = types.InlineKeyboardButton("Only physical exercise benefits mental wellbeing.",
                                          callback_data="skills_b1b2_wrong_3")
        btn3 = types.InlineKeyboardButton("Learning can create new neural pathways.",
                                          callback_data="skills_b1b2_correct_3")
        btn4 = types.InlineKeyboardButton("Musical instruments don't help cognitive function.",
                                          callback_data="skills_b1b2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("masterclass", callback_data="skills_b1b2_correct_4")
        btn2 = types.InlineKeyboardButton("workshop", callback_data="skills_b1b2_wrong_4")
        btn3 = types.InlineKeyboardButton("seminar", callback_data="skills_b1b2_wrong_4")
        btn4 = types.InlineKeyboardButton("lecture", callback_data="skills_b1b2_wrong_4")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id,
                         "<b>4/5.</b> Which word means a session where an expert teaches a skill to a small group?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        text = """<b>5/5.</b> Read the text and choose the correct statement:\n\n
The concept of "lifelong learning" emphasizes continuous skill development throughout one's life. In today's rapidly changing job market, adaptability and willingness to learn new skills are highly valued by employers across various industries.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Learning should stop after formal education.",
                                          callback_data="skills_b1b2_wrong_5")
        btn2 = types.InlineKeyboardButton("Employers value only existing skills, not adaptability.",
                                          callback_data="skills_b1b2_wrong_5")
        btn3 = types.InlineKeyboardButton("Continuous learning is important in modern job markets.",
                                          callback_data="skills_b1b2_correct_5")
        btn4 = types.InlineKeyboardButton("Skills become obsolete less quickly today than before.",
                                          callback_data="skills_b1b2_wrong_5")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')


def check_text_task_skills_b1b2_2(message, user_id):
    correct_answers = [
        "you need to practice regularly to improve your skills",
        "to improve your skills you need to practice regularly",
        "you need to regularly practice your skills to improve"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Correct! A possible answer: 'You need to practice regularly to improve your skills.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Incorrect. Try again!")
        send_text_task_skills_b1b2(user_id, 2)


# ==============================================
# Education and Studying - Text Tasks (A1-A2)
# ==============================================
def send_text_task_education_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('pen', callback_data='education_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('book', callback_data='education_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('notebook', callback_data='education_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('apple', callback_data='education_a1a2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Выберите лишнее из списка:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id, "<b>2/5.</b> Составьте предложение из слов:\n\ngo, I, to, college, every, day",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_education_a1a2_2(m, user_id))

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("teacher", callback_data="education_a1a2_correct_3")
        btn2 = types.InlineKeyboardButton("doctor", callback_data="education_a1a2_wrong_3")
        btn3 = types.InlineKeyboardButton("driver", callback_data="education_a1a2_wrong_3")
        btn4 = types.InlineKeyboardButton("cook", callback_data="education_a1a2_wrong_3")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>3/5.</b> Кто работает в школе и учит детей?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        text = """<b>4/5.</b> Прочитайте текст и выберите верное утверждение:\n\n
I'm a student. I study at university. My favorite subject is history. I have classes from Monday to Friday. On weekends I rest.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("I'm a teacher.", callback_data="education_a1a2_wrong_4")
        btn2 = types.InlineKeyboardButton("My favorite subject is math.", callback_data="education_a1a2_wrong_4")
        btn3 = types.InlineKeyboardButton("I have classes on weekdays.", callback_data="education_a1a2_correct_4")
        btn4 = types.InlineKeyboardButton("I study at school.", callback_data="education_a1a2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("homework", callback_data="education_a1a2_correct_5")
        btn2 = types.InlineKeyboardButton("housework", callback_data="education_a1a2_wrong_5")
        btn3 = types.InlineKeyboardButton("workbook", callback_data="education_a1a2_wrong_5")
        btn4 = types.InlineKeyboardButton("workshop", callback_data="education_a1a2_wrong_5")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>5/5.</b> Какое слово означает задания, которые ученики делают дома?",
                         reply_markup=markup, parse_mode='html')


def check_text_task_education_a1a2_2(message, user_id):
    correct_answers = [
        "i go to college every day",
        "every day i go to college"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Верно! Один из возможных вариантов: 'I go to college every day.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Неправильно. Попробуйте ещё раз!")
        send_text_task_education_a1a2(user_id, 2)


# ==============================================
# Education and Studying - Text Tasks (B1-B2)
# ==============================================
def send_text_task_education_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('bachelor', callback_data='education_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('master', callback_data='education_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('PhD', callback_data='education_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('teacher', callback_data='education_b1b2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Choose the odd one out:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Make a sentence using these words:\n\neffective, is, technique, This, learning, very, a",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_education_b1b2_2(m, user_id))

    elif task_num == 3:
        text = """<b>3/5.</b> Read the text and choose the correct statement:\n\n
The flipped classroom model reverses traditional teaching methods. Students study new content at home through videos or readings, then use class time for discussions and problem-solving. This approach promotes active learning and better retention of information.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("In flipped classrooms, teachers lecture during class time.",
                                          callback_data="education_b1b2_wrong_3")
        btn2 = types.InlineKeyboardButton("Students study new material at home in this model.",
                                          callback_data="education_b1b2_correct_3")
        btn3 = types.InlineKeyboardButton("This method decreases information retention.",
                                          callback_data="education_b1b2_wrong_3")
        btn4 = types.InlineKeyboardButton("Flipped classrooms discourage active participation.",
                                          callback_data="education_b1b2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("critical thinking", callback_data="education_b1b2_correct_4")
        btn2 = types.InlineKeyboardButton("memorization", callback_data="education_b1b2_wrong_4")
        btn3 = types.InlineKeyboardButton("repetition", callback_data="education_b1b2_wrong_4")
        btn4 = types.InlineKeyboardButton("copying", callback_data="education_b1b2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id,
                         "<b>4/5.</b> Which concept means the ability to analyze facts and form your own judgments?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        text = """<b>5/5.</b> Read the text and choose the correct statement:\n\n
Online education has become increasingly popular, offering flexibility and accessibility. However, it requires strong self-discipline and time management skills. Blended learning, combining online and in-person instruction, is emerging as an effective compromise.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Online education doesn't require any discipline.",
                                          callback_data="education_b1b2_wrong_5")
        btn2 = types.InlineKeyboardButton("Blended learning combines different teaching methods.",
                                          callback_data="education_b1b2_correct_5")
        btn3 = types.InlineKeyboardButton("Online education is becoming less popular.",
                                          callback_data="education_b1b2_wrong_5")
        btn4 = types.InlineKeyboardButton("There are no benefits to online learning.",
                                          callback_data="education_b1b2_wrong_5")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')


def check_text_task_education_b1b2_2(message, user_id):
    correct_answers = [
        "this is a very effective learning technique",
        "a very effective learning technique this is",
        "this learning technique is very effective"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Correct! A possible answer: 'This is a very effective learning technique.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Incorrect. Try again!")
        send_text_task_education_b1b2(user_id, 2)

# ==============================================
# Work and Jobs - Text Tasks (A1-A2)
# ==============================================
def send_text_task_work_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('doctor', callback_data='work_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('teacher', callback_data='work_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('driver', callback_data='work_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('neighbour', callback_data='work_a1a2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Выберите лишнее из списка:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id, "<b>2/5.</b> Составьте предложение из слов:\n\nworks, hospital, in, a, She",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_work_a1a2_2(m, user_id))

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Monday to Friday", callback_data="work_a1a2_correct_3")
        btn2 = types.InlineKeyboardButton("every weekend", callback_data="work_a1a2_wrong_3")
        btn3 = types.InlineKeyboardButton("only Sundays", callback_data="work_a1a2_wrong_3")
        btn4 = types.InlineKeyboardButton("never", callback_data="work_a1a2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> Выберите типичные рабочие дни:\n\n"
                                  "I work from ________.",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        text = """<b>4/5.</b> Прочитайте текст и выберите верное утверждение:\n\n
My name is Jake. I'm a waiter. I work in a restaurant. My job is to take orders and serve food. I work from 10 am to 6 pm, Tuesday to Sunday. Monday is my day off.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Jake is a chef.", callback_data="work_a1a2_wrong_4")
        btn2 = types.InlineKeyboardButton("Jake works every day.", callback_data="work_a1a2_wrong_4")
        btn3 = types.InlineKeyboardButton("Jake takes orders.", callback_data="work_a1a2_correct_4")
        btn4 = types.InlineKeyboardButton("Jake works in a hospital.", callback_data="work_a1a2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("salary", callback_data="work_a1a2_correct_5")
        btn2 = types.InlineKeyboardButton("holiday", callback_data="work_a1a2_wrong_5")
        btn3 = types.InlineKeyboardButton("weekend", callback_data="work_a1a2_wrong_5")
        btn4 = types.InlineKeyboardButton("break", callback_data="work_a1a2_wrong_5")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>5/5.</b> Какое слово обозначает денежное вознаграждение за работу?",
                         reply_markup=markup, parse_mode='html')


def check_text_task_work_a1a2_2(message, user_id):
    correct_answers = [
        "she works in a hospital",
        "in a hospital she works"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Верно! Один из возможных вариантов: 'She works in a hospital.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Неправильно. Попробуйте ещё раз!")
        send_text_task_work_a1a2(user_id, 2)


# ==============================================
# Work and Jobs - Text Tasks (B1-B2)
# ==============================================
def send_text_task_work_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('freelancer', callback_data='work_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('remote worker', callback_data='work_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('entrepreneur', callback_data='work_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('office plant', callback_data='work_b1b2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Choose the odd one out:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Make a sentence using these words:\n\nrequires, This, degree, job, a, university",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_work_b1b2_2(m, user_id))

    elif task_num == 3:
        text = """<b>3/5.</b> Read the text and choose the correct statement:\n\n
The gig economy refers to a labor market characterized by short-term contracts or freelance work as opposed to permanent jobs. Platforms like Uber and Fiverr have facilitated this trend, offering flexibility but often lacking benefits like health insurance or paid leave.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("The gig economy offers only permanent positions.",
                                          callback_data="work_b1b2_wrong_3")
        btn2 = types.InlineKeyboardButton("Gig workers typically receive full benefits.",
                                          callback_data="work_b1b2_wrong_3")
        btn3 = types.InlineKeyboardButton("The gig economy is characterized by short-term work.",
                                          callback_data="work_b1b2_correct_3")
        btn4 = types.InlineKeyboardButton("Traditional jobs are disappearing completely.",
                                          callback_data="work_b1b2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("resume", callback_data="work_b1b2_correct_4")
        btn2 = types.InlineKeyboardButton("recipe", callback_data="work_b1b2_wrong_4")
        btn3 = types.InlineKeyboardButton("receipt", callback_data="work_b1b2_wrong_4")
        btn4 = types.InlineKeyboardButton("report", callback_data="work_b1b2_wrong_4")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>4/5.</b> Which word is used when applying for jobs?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        text = """<b>5/5.</b> Read the text and choose the correct statement:\n\n
Work-life balance has become increasingly important in modern society. Many companies now offer flexible working hours, remote work options, and wellness programs to help employees maintain this balance. Studies show that good work-life balance leads to higher productivity and job satisfaction.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Flexible hours decrease productivity.", callback_data="work_b1b2_wrong_5")
        btn2 = types.InlineKeyboardButton("Work-life balance is becoming less important.",
                                          callback_data="work_b1b2_wrong_5")
        btn3 = types.InlineKeyboardButton("Companies are adopting flexible work options.",
                                          callback_data="work_b1b2_correct_5")
        btn4 = types.InlineKeyboardButton("Wellness programs are rare in companies.", callback_data="work_b1b2_wrong_5")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')


def check_text_task_work_b1b2_2(message, user_id):
    correct_answers = [
        "this job requires a university degree",
        "a university degree this job requires"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Correct! A possible answer: 'This job requires a university degree.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Incorrect. Try again!")
        send_text_task_work_b1b2(user_id, 2)


# ==============================================
# Daily life and routine - Text Tasks (A1-A2)
# ==============================================
def send_text_task_daily_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('wake up', callback_data='daily_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('brush teeth', callback_data='daily_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('go to work', callback_data='daily_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('fly to the moon', callback_data='daily_a1a2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Выберите лишнее из списка:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Составьте предложение из слов:\n\nget, I, at, up, 7, usually",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_daily_a1a2_2(m, user_id))

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("morning", callback_data="daily_a1a2_correct_3")
        btn2 = types.InlineKeyboardButton("night", callback_data="daily_a1a2_wrong_3")
        btn3 = types.InlineKeyboardButton("evening", callback_data="daily_a1a2_wrong_3")
        btn4 = types.InlineKeyboardButton("afternoon", callback_data="daily_a1a2_wrong_3")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>3/5.</b> В какое время люди обычно завтракают?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        text = """<b>4/5.</b> Прочитайте текст и выберите верное утверждение:\n\n
My daily routine is simple. I wake up at 7 am, take a shower, and have breakfast. At 8 am I go to school. After school, I do my homework and play with friends. I have dinner at 7 pm and go to bed at 10 pm.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("I wake up at 6 am.", callback_data="daily_a1a2_wrong_4")
        btn2 = types.InlineKeyboardButton("I have dinner at 7 pm.", callback_data="daily_a1a2_correct_4")
        btn3 = types.InlineKeyboardButton("I go to school at 9 am.", callback_data="daily_a1a2_wrong_4")
        btn4 = types.InlineKeyboardButton("I never do homework.", callback_data="daily_a1a2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("always", callback_data="daily_a1a2_correct_5")
        btn2 = types.InlineKeyboardButton("never", callback_data="daily_a1a2_wrong_5")
        btn3 = types.InlineKeyboardButton("sometimes", callback_data="daily_a1a2_wrong_5")
        btn4 = types.InlineKeyboardButton("rarely", callback_data="daily_a1a2_wrong_5")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>5/5.</b> Какое слово означает 'всегда'?",
                         reply_markup=markup, parse_mode='html')


def check_text_task_daily_a1a2_2(message, user_id):
    correct_answers = [
        "i usually get up at 7",
        "usually i get up at 7"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Верно! Один из возможных вариантов: 'I usually get up at 7.")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Неправильно. Попробуйте ещё раз!")
        send_text_task_daily_a1a2(user_id, 2)


# ==============================================
# Daily life and routine - Text Tasks (B1-B2)
# ==============================================
def send_text_task_daily_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('commute', callback_data='daily_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('errands', callback_data='daily_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('chores', callback_data='daily_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('adventure', callback_data='daily_b1b2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Choose the odd one out:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Make a sentence using these words:\n\nschedule, busy, a, have, I, very",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_daily_b1b2_2(m, user_id))

    elif task_num == 3:
        text = """<b>3/5.</b> Read the text and choose the correct statement:\n\n
Time management is crucial for productivity. Techniques like the Pomodoro method (working in 25-minute intervals with short breaks) and time blocking (allocating specific time slots for tasks) can help people optimize their daily routines.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("The Pomodoro method involves 60-minute work sessions.",
                                          callback_data="daily_b1b2_wrong_3")
        btn2 = types.InlineKeyboardButton("Time blocking means doing all tasks at once.",
                                          callback_data="daily_b1b2_wrong_3")
        btn3 = types.InlineKeyboardButton("Time management techniques can improve productivity.",
                                          callback_data="daily_b1b2_correct_3")
        btn4 = types.InlineKeyboardButton("Breaks decrease overall productivity.", callback_data="daily_b1b2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("procrastination", callback_data="daily_b1b2_correct_4")
        btn2 = types.InlineKeyboardButton("productivity", callback_data="daily_b1b2_wrong_4")
        btn3 = types.InlineKeyboardButton("punctuality", callback_data="daily_b1b2_wrong_4")
        btn4 = types.InlineKeyboardButton("preparation", callback_data="daily_b1b2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> Which word means 'delaying or postponing tasks'?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        text = """<b>5/5.</b> Read the text and choose the correct statement:\n\n
The concept of "morning routines" has gained popularity, with many successful people advocating for starting the day with meditation, exercise, or journaling. Research suggests that how we begin our morning can significantly impact our productivity and mood throughout the day.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Morning routines have no effect on productivity.",
                                          callback_data="daily_b1b2_wrong_5")
        btn2 = types.InlineKeyboardButton("Only unsuccessful people have morning routines.",
                                          callback_data="daily_b1b2_wrong_5")
        btn3 = types.InlineKeyboardButton("Morning routines can include meditation or exercise.",
                                          callback_data="daily_b1b2_correct_5")
        btn4 = types.InlineKeyboardButton("Research shows morning routines are harmful.",
                                          callback_data="daily_b1b2_wrong_5")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')


def check_text_task_daily_b1b2_2(message, user_id):
    correct_answers = [
        "i have a very busy schedule",
        "a very busy schedule i have"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Correct! A possible answer: 'I have a very busy schedule.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Incorrect. Try again!")
        send_text_task_daily_b1b2(user_id, 2)


# ==============================================
# Travelling and Transport - Text Tasks (A1-A2)
# ==============================================
def send_text_task_travel_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('bus', callback_data='travel_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('train', callback_data='travel_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('plane', callback_data='travel_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('book', callback_data='travel_a1a2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Выберите лишнее из списка:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id, "<b>2/5.</b> Составьте предложение из слов:\n\nby, go, I, work, to, bus",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_travel_a1a2_2(m, user_id))

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("ticket", callback_data="travel_a1a2_correct_3")
        btn2 = types.InlineKeyboardButton("book", callback_data="travel_a1a2_wrong_3")
        btn3 = types.InlineKeyboardButton("pen", callback_data="travel_a1a2_wrong_3")
        btn4 = types.InlineKeyboardButton("phone", callback_data="travel_a1a2_wrong_3")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>3/5.</b> Что нужно купить, чтобы сесть на поезд?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        text = """<b>4/5.</b> Прочитайте текст и выберите правильный ответ:\n\n
I'm going to London next month. I'll fly there by plane. The flight takes 3 hours. I've already booked my ticket and hotel. I'm very excited!
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("I'm going by train.", callback_data="travel_a1a2_wrong_4")
        btn2 = types.InlineKeyboardButton("The flight takes 5 hours.", callback_data="travel_a1a2_wrong_4")
        btn3 = types.InlineKeyboardButton("I've booked my ticket.", callback_data="travel_a1a2_correct_4")
        btn4 = types.InlineKeyboardButton("I'm not excited.", callback_data="travel_a1a2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("passport", callback_data="travel_a1a2_correct_5")
        btn2 = types.InlineKeyboardButton("book", callback_data="travel_a1a2_wrong_5")
        btn3 = types.InlineKeyboardButton("pen", callback_data="travel_a1a2_wrong_5")
        btn4 = types.InlineKeyboardButton("map", callback_data="travel_a1a2_wrong_5")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>5/5.</b> Что обязательно необходимо для поездки в другую страну?",
                         reply_markup=markup, parse_mode='html')


def check_text_task_travel_a1a2_2(message, user_id):
    correct_answers = [
        "i go to work by bus",
        "by bus i go to work"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Верно! Один из возможных вариантов: 'I go to work by bus.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Неправильно. Попробуйте ещё раз!")
        send_text_task_travel_a1a2(user_id, 2)


# ==============================================
# Travelling and Transport - Text Tasks (B1-B2)
# ==============================================
def send_text_task_travel_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('boarding pass', callback_data='travel_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('itinerary', callback_data='travel_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('layover', callback_data='travel_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('shopping list', callback_data='travel_b1b2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Choose the odd one out:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Make a sentence using these words:\n\nprefer, I, travelling, train, by, to, plane",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_travel_b1b2_2(m, user_id))

    elif task_num == 3:
        text = """<b>3/5.</b> Read the text and choose the correct statement:\n\n
Sustainable tourism aims to minimize the negative impact of travel on the environment and local cultures. This includes choosing eco-friendly accommodations, using public transportation, and respecting local customs and traditions.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Sustainable tourism ignores local cultures.",
                                          callback_data="travel_b1b2_wrong_3")
        btn2 = types.InlineKeyboardButton("It encourages using private jets.", callback_data="travel_b1b2_wrong_3")
        btn3 = types.InlineKeyboardButton("It aims to reduce environmental impact.",
                                          callback_data="travel_b1b2_correct_3")
        btn4 = types.InlineKeyboardButton("Sustainable tourism promotes mass tourism.",
                                          callback_data="travel_b1b2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("jet lag", callback_data="travel_b1b2_correct_4")
        btn2 = types.InlineKeyboardButton("time difference", callback_data="travel_b1b2_wrong_4")
        btn3 = types.InlineKeyboardButton("flight delay", callback_data="travel_b1b2_wrong_4")
        btn4 = types.InlineKeyboardButton("boarding time", callback_data="travel_b1b2_wrong_4")
        markup.row(btn1, btn3)
        markup.row(btn2, btn4)
        bot.send_message(user_id,
                         "<b>4/5.</b> What is the term for tiredness after a long flight across time zones?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        text = """<b>5/5.</b> Read the text and choose the correct statement:\n\n
The rise of budget airlines has made air travel more accessible to the general public. While these airlines offer lower fares, they often charge extra for services like checked baggage and onboard meals. This business model has revolutionized the travel industry.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Budget airlines include all services in the ticket price.",
                                          callback_data="travel_b1b2_wrong_5")
        btn2 = types.InlineKeyboardButton("Budget airlines have made air travel more expensive.",
                                          callback_data="travel_b1b2_wrong_5")
        btn3 = types.InlineKeyboardButton("Budget airlines often charge extra for checked baggage.",
                                          callback_data="travel_b1b2_correct_5")
        btn4 = types.InlineKeyboardButton("Budget airlines haven't affected the travel industry.",
                                          callback_data="travel_b1b2_wrong_5")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')


def check_text_task_travel_b1b2_2(message, user_id):
    correct_answers = [
        "i prefer travelling by train to plane",
        "I prefer travelling by plane to train"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Correct! A possible answer: 'I prefer travelling by train to plane.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Incorrect. Try again!")
        send_text_task_travel_b1b2(user_id, 2)


# ==============================================
# Health and Medicine - Text Tasks (A1-A2)
# ==============================================
def send_text_task_health_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('headache', callback_data='health_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('fever', callback_data='health_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('cough', callback_data='health_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('rain', callback_data='health_a1a2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Выберите лишнее из списка:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id, "<b>2/5.</b> Составьте предложение из слов:\n\nsee, I, doctor, must, a",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_health_a1a2_2(m, user_id))

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("hospital", callback_data="health_a1a2_correct_3")
        btn2 = types.InlineKeyboardButton("school", callback_data="health_a1a2_wrong_3")
        btn3 = types.InlineKeyboardButton("shop", callback_data="health_a1a2_wrong_3")
        btn4 = types.InlineKeyboardButton("park", callback_data="health_a1a2_wrong_3")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>3/5.</b> Куда идут люди, когда очень плохо себя чувствуют?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        text = """<b>4/5.</b> Прочитайте текст и выберите верное утверждение:\n\n
I don't feel well today. I have a headache and a sore throat. My temperature is 38.5°C. I think I have the flu. I'll take some medicine and stay in bed.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("I have a broken leg.", callback_data="health_a1a2_wrong_4")
        btn2 = types.InlineKeyboardButton("My temperature is normal.", callback_data="health_a1a2_wrong_4")
        btn3 = types.InlineKeyboardButton("I have a headache.", callback_data="health_a1a2_correct_4")
        btn4 = types.InlineKeyboardButton("I'll go to work.", callback_data="health_a1a2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("fast food", callback_data="health_a1a2_wrong_5")
        btn2 = types.InlineKeyboardButton("pills", callback_data="health_a1a2_correct_5")
        btn3 = types.InlineKeyboardButton("phone", callback_data="health_a1a2_wrong_5")
        btn4 = types.InlineKeyboardButton("glass", callback_data="health_a1a2_wrong_5")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>5/5.</b> Что поможет выздороветь?",
                         reply_markup=markup, parse_mode='html')


def check_text_task_health_a1a2_2(message, user_id):
    correct_answers = [
        "i must see a doctor",
        "must i see a doctor"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Верно! Один из возможных вариантов: 'I must see the doctor.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Неправильно. Попробуйте ещё раз!")
        send_text_task_health_a1a2(user_id, 2)


# ==============================================
# Health and Medicine - Text Tasks (B1-B2)
# ==============================================
def send_text_task_health_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('antibiotics', callback_data='health_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('vaccination', callback_data='health_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('diagnosis', callback_data='health_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('vacation', callback_data='health_b1b2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Choose the odd one out:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Make a sentence using these words:\n\nshould, lifestyle, healthier, adopt, a, People",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_health_b1b2_2(m, user_id))

    elif task_num == 3:
        text = """<b>3/5.</b> Read the text and choose the correct statement:\n\n
Preventive healthcare focuses on disease prevention rather than treatment. Regular exercise, balanced nutrition, and routine medical check-ups can help prevent many chronic conditions and improve overall quality of life.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Preventive healthcare only treats existing diseases.",
                                          callback_data="health_b1b2_wrong_3")
        btn2 = types.InlineKeyboardButton("Regular exercise can help prevent chronic conditions.",
                                          callback_data="health_b1b2_correct_3")
        btn3 = types.InlineKeyboardButton("Preventive healthcare worsens quality of life.",
                                          callback_data="health_b1b2_wrong_3")
        btn4 = types.InlineKeyboardButton("Medical check-ups are unnecessary for prevention.",
                                          callback_data="health_b1b2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("placebo", callback_data="health_b1b2_correct_4")
        btn2 = types.InlineKeyboardButton("antibiotic", callback_data="health_b1b2_wrong_4")
        btn3 = types.InlineKeyboardButton("vaccine", callback_data="health_b1b2_wrong_4")
        btn4 = types.InlineKeyboardButton("painkiller", callback_data="health_b1b2_wrong_4")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id,
                         "<b>4/5.</b> What is the term for a substance with no therapeutic effect used in research?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        text = """<b>5/5.</b> Read the text and choose the correct statement:\n\n
Mental health is as important as physical health. Conditions like depression and anxiety are common but treatable. Seeking professional help, maintaining social connections, and practicing self-care can significantly improve mental wellbeing.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Mental health is less important than physical health.",
                                          callback_data="health_b1b2_wrong_5")
        btn2 = types.InlineKeyboardButton("Depression is always untreatable.", callback_data="health_b1b2_wrong_5")
        btn3 = types.InlineKeyboardButton("Social connections can improve mental wellbeing.",
                                          callback_data="health_b1b2_correct_5")
        btn4 = types.InlineKeyboardButton("Self-care worsens mental health.", callback_data="health_b1b2_wrong_5")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')


def check_text_task_health_b1b2_2(message, user_id):
    correct_answers = [
        "people should adopt a healthier lifestyle",
        "a healthier lifestyle people should adopt"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Correct! A possible answer: 'People should adopt a healthier lifestyle.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Incorrect. Try again!")
        send_text_task_health_b1b2(user_id, 2)


# ==============================================
# Shopping - Text Tasks (A1-A2)
# ==============================================
def send_text_task_shopping_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('dress', callback_data='shop_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('shoes', callback_data='shop_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('shirt', callback_data='shop_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('jewelry', callback_data='shop_a1a2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Выберите лишнее из списка:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id, "<b>2/5.</b> Составьте предложение из слов:\n\nbuy, to, I, milk, some, need",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_shop_a1a2_2(m, user_id))

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("cash", callback_data="shop_a1a2_correct_3")
        btn2 = types.InlineKeyboardButton("book", callback_data="shop_a1a2_wrong_3")
        btn3 = types.InlineKeyboardButton("card", callback_data="shop_a1a2_correct_3")
        btn4 = types.InlineKeyboardButton("phone", callback_data="shop_a1a2_wrong_3")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>3/5.</b> Чем можно расплатиться в магазине?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        text = """<b>4/5.</b> Прочитайте текст и выберите верное утверждение:\n\n
I went shopping yesterday. I bought a new jacket and a pair of jeans. The jacket was $50 and the jeans were $30. I paid with my credit card.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("I bought a dress.", callback_data="shop_a1a2_wrong_4")
        btn2 = types.InlineKeyboardButton("The jeans were $30.", callback_data="shop_a1a2_correct_4")
        btn3 = types.InlineKeyboardButton("I paid with cash.", callback_data="shop_a1a2_wrong_4")
        btn4 = types.InlineKeyboardButton("I went shopping today.", callback_data="shop_a1a2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("supermarket", callback_data="shop_a1a2_correct_5")
        btn2 = types.InlineKeyboardButton("school", callback_data="shop_a1a2_wrong_5")
        btn3 = types.InlineKeyboardButton("hospital", callback_data="shop_a1a2_wrong_5")
        btn4 = types.InlineKeyboardButton("park", callback_data="shop_a1a2_wrong_5")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>5/5.</b> Где можно купить продукты?",
                         reply_markup=markup, parse_mode='html')


def check_text_task_shop_a1a2_2(message, user_id):
    correct_answers = [
        "i need to buy some milk",
        "to buy some milk i need"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Верно! Один из возможных вариантов: 'I need to buy some milk.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Неправильно. Попробуйте ещё раз!")
        send_text_task_shopping_a1a2(user_id, 2)


# ==============================================
# Shopping - Text Tasks (B1-B2)
# ==============================================
def send_text_task_shopping_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('bargain', callback_data='shop_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('discount', callback_data='shop_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('receipt', callback_data='shop_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('sunshine', callback_data='shop_b1b2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Choose the odd one out:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Make a sentence using these words:\n\ncomparison, do, shopping, some, should, You, before, online",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_shop_b1b2_2(m, user_id))

    elif task_num == 3:
        text = """<b>3/5.</b> Read the text and choose the correct statement:\n\n
Impulse buying refers to unplanned purchases made without careful consideration. Retailers often encourage this behavior through strategic product placement, limited-time offers, and attractive displays near checkout counters.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Impulse buying is always carefully planned.",
                                          callback_data="shop_b1b2_wrong_3")
        btn2 = types.InlineKeyboardButton("Retailers discourage impulse buying.", callback_data="shop_b1b2_wrong_3")
        btn3 = types.InlineKeyboardButton("Limited-time offers can encourage impulse buying.",
                                          callback_data="shop_b1b2_correct_3")
        btn4 = types.InlineKeyboardButton("Product placement has no effect on purchases.",
                                          callback_data="shop_b1b2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("civil rights", callback_data="shop_b1b2_correct_4")
        btn2 = types.InlineKeyboardButton("moral rights", callback_data="shop_b1b2_wrong_4")
        btn3 = types.InlineKeyboardButton("consumer rights", callback_data="shop_b1b2_correct_4")
        btn4 = types.InlineKeyboardButton("human rights", callback_data="shop_b1b2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> What are the rights of consumers to return faulty goods called?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        text = """<b>5/5.</b> Read the text and choose the correct statement:\n\n
E-commerce has grown significantly with the rise of the internet. Online shopping offers convenience and often lower prices, but customers miss the tactile experience of physical stores and may face issues with product returns or delivery delays.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Online shopping is less convenient than traditional shopping.",
                                          callback_data="shop_b1b2_wrong_5")
        btn2 = types.InlineKeyboardButton("E-commerce hasn't grown with internet development.",
                                          callback_data="shop_b1b2_wrong_5")
        btn3 = types.InlineKeyboardButton("Online shopping may have delivery issues.",
                                          callback_data="shop_b1b2_correct_5")
        btn4 = types.InlineKeyboardButton("Physical stores don't offer tactile experiences.",
                                          callback_data="shop_b1b2_wrong_5")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')


def check_text_task_shop_b1b2_2(message, user_id):
    correct_answers = [
        "you should do some comparison before shopping online",
        "you should do some comparison before online shopping"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id,
                         "✅ Correct! A possible answer: 'You should do some comparison before shopping online.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Incorrect. Try again!")
        send_text_task_shopping_b1b2(user_id, 2)


# ==============================================
# Food - Text Tasks (A1-A2)
# ==============================================
def send_text_task_food_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('apple', callback_data='food_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('banana', callback_data='food_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('orange', callback_data='food_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('potato', callback_data='food_a1a2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Выберите лишнее из списка:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id, "<b>2/5.</b> Составьте предложение из слов:\n\nlike, I, drink, coffee, to",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_food_a1a2_2(m, user_id))

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("breakfast", callback_data="food_a1a2_correct_3")
        btn2 = types.InlineKeyboardButton("lunch", callback_data="food_a1a2_wrong_3")
        btn3 = types.InlineKeyboardButton("dinner", callback_data="food_a1a2_wrong_3")
        btn4 = types.InlineKeyboardButton("meal", callback_data="food_a1a2_wrong_3")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>3/5.</b> Как называется утренний прием пищи?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        text = """<b>4/5.</b> Прочитайте текст и выберите верное утверждение:\n\n
My favorite food is pizza. I like it with pepperoni. I usually eat pizza on weekends. Sometimes I order it from a restaurant near my home.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("I like pizza with pepperoni.",callback_data="food_a1a2_correct_4")
        btn2 = types.InlineKeyboardButton("I eat pizza every day.", callback_data="food_a1a2_wrong_4")
        btn3 = types.InlineKeyboardButton("I don't like pizza.", callback_data="food_a1a2_wrong_4")
        btn4 = types.InlineKeyboardButton("I never order pizza.", callback_data="food_a1a2_wrong_4")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("vegetables", callback_data="food_a1a2_correct_5")
        btn2 = types.InlineKeyboardButton("alcohol", callback_data="food_a1a2_wrong_5")
        btn3 = types.InlineKeyboardButton("fast food", callback_data="food_a1a2_wrong_5")
        btn4 = types.InlineKeyboardButton("cigarettes", callback_data="food_a1a2_wrong_5")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id, "<b>5/5.</b> Что из этого полезно для здоровья?",
                         reply_markup=markup, parse_mode='html')


def check_text_task_food_a1a2_2(message, user_id):
    correct_answers = [
        "i like to drink coffee",
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id, "✅ Верно!")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Неправильно. Попробуйте ещё раз!")
        send_text_task_food_a1a2(user_id, 2)

# ==============================================
# Food - Text Tasks (B1-B2)
# ==============================================
def send_text_task_food_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('carbohydrates', callback_data='food_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('proteins', callback_data='food_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('vitamins', callback_data='food_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('hormones', callback_data='food_b1b2_correct_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_message(user_id, "<b>1/5.</b> Choose the odd one out:",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        msg = bot.send_message(user_id,
                               "<b>2/5.</b> Make a sentence using these words:\n\nbalanced, diet, A, include, should, all, groups, food, of",
                               parse_mode='html')
        bot.register_next_step_handler(msg, lambda m: check_text_task_food_b1b2_2(m, user_id))

    elif task_num == 3:
        text = """<b>3/5.</b> Read the text and choose the correct statement:\n\n
Organic farming avoids the use of synthetic pesticides and fertilizers. While organic products are often more expensive, many consumers prefer them due to perceived health benefits and environmental concerns.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Organic farming uses synthetic pesticides.",
                                          callback_data="food_b1b2_wrong_3")
        btn2 = types.InlineKeyboardButton("Organic products are usually cheaper.", callback_data="food_b1b2_wrong_3")
        btn3 = types.InlineKeyboardButton("Some consumers choose organic for health reasons.",
                                          callback_data="food_b1b2_correct_3")
        btn4 = types.InlineKeyboardButton("Organic farming harms the environment more.",
                                          callback_data="food_b1b2_wrong_3")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("vegan", callback_data="food_b1b2_correct_4")
        btn2 = types.InlineKeyboardButton("vegetarian", callback_data="food_b1b2_wrong_4")
        btn3 = types.InlineKeyboardButton("pescatarian", callback_data="food_b1b2_wrong_4")
        btn4 = types.InlineKeyboardButton("omnivore", callback_data="food_b1b2_wrong_4")
        markup.row(btn1, btn2, btn3, btn4)
        bot.send_message(user_id,
                         "<b>4/5.</b> What do you call a person who doesn't consume any animal products?",
                         reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        text = """<b>5/5.</b> Read the text and choose the correct statement:\n\n
Food waste is a significant global issue, with about one-third of all food produced being wasted. Reducing food waste can help address hunger, save money, and reduce environmental impact. Simple measures like proper meal planning and storage can make a big difference.
"""
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("All food produced is consumed.", callback_data="food_b1b2_wrong_5")
        btn2 = types.InlineKeyboardButton("Food waste has no environmental impact.", callback_data="food_b1b2_wrong_5")
        btn3 = types.InlineKeyboardButton("Meal planning can help reduce food waste.",
                                          callback_data="food_b1b2_correct_5")
        btn4 = types.InlineKeyboardButton("Food waste is not a global problem.", callback_data="food_b1b2_wrong_5")
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, text, reply_markup=markup, parse_mode='html')


def check_text_task_food_b1b2_2(message, user_id):
    correct_answers = [
        "a balanced diet should include all food groups",
        "all food groups a balanced diet should include",
        "a balanced diet should include all groups of food"
    ]
    user_answer = re.sub(r"[^\w\s]", "", message.text.lower()).strip()

    if user_answer in correct_answers:
        bot.send_message(user_id,
                         "✅ Correct! A possible answer: 'A balanced diet should include all food groups.'")
        user_data[user_id]["current_task"] = 3
        user_data[user_id]["score"] = user_data.get(user_id, {}).get("score", 0) + 1
        send_task(user_id)
    else:
        bot.send_message(user_id, "❌ Incorrect. Try again!")
        send_text_task_food_b1b2(user_id, 2)

# ==============================================
# Family and Friends - Image Tasks (A1-A2)
# ==============================================
def send_image_task_family_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Friends', callback_data='family_img_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('Family', callback_data='family_img_a1a2_correct_1')
        btn3 = types.InlineKeyboardButton('Colleagues', callback_data='family_img_a1a2_wrong_1')
        markup.row(btn1, btn2, btn3)
        bot.send_photo(user_id, photo=open('images/family.jpg', 'rb'),
                      caption="<b>1/3.</b> Какое слово лучше всего описывает изображение?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('mother', callback_data='family_img_a1a2_correct_2')
        btn2 = types.InlineKeyboardButton('father', callback_data='family_img_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('sister', callback_data='family_img_a1a2_wrong_2')
        btn4 = types.InlineKeyboardButton('teacher', callback_data='family_img_a1a2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/mother.jpg', 'rb'),
                      caption="<b>2/3.</b> Кто изображен на картинке?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('They are working.', callback_data='family_img_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('They are having a picnic.', callback_data='family_img_a1a2_correct_3')
        btn3 = types.InlineKeyboardButton('They are studying.', callback_data='family_img_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/family_picnic.jpg', 'rb'),
                      caption="<b>3/3.</b> Что делает эта семья?",
                      reply_markup=markup, parse_mode='html')



# ==============================================
# Family and Friends - Image Tasks (B1-B2)
# ==============================================
def send_image_task_family_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Nuclear family', callback_data='family_img_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Extended family', callback_data='family_img_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('Single-parent family', callback_data='family_img_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/extended_family.jpeg', 'rb'),
                      caption="<b>1/3.</b> What type of family is shown in the picture?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('business meeting', callback_data='family_img_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('family reunion', callback_data='family_img_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('school lesson', callback_data='family_img_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('sports event', callback_data='family_img_b1b2_wrong_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        with open('images/family_reunion.jpeg', 'rb') as photo:
            bot.send_photo(user_id, photo, caption="<b>2/3.</b> What is happening in the picture?",
                          reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('supportive', callback_data='family_img_b1b2_correct_3')
        btn2 = types.InlineKeyboardButton('tense', callback_data='family_img_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('neutral', callback_data='family_img_b1b2_wrong_3')
        markup.row(btn1 )
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/supportive_family.jpg', 'rb'),
                      caption="<b>3/3.</b> What kind of relationship might there be between family members?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Skills and Hobbies - Image Tasks (A1-A2)
# ==============================================
def send_image_task_skills_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Playing football', callback_data='skills_img_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('Playing the guitar', callback_data='skills_img_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('Reading a book', callback_data='skills_img_a1a2_correct_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/reading.jpeg', 'rb'),
                      caption="<b>1/3.</b> Что делает человек на картинке?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Drawing', callback_data='skills_img_a1a2_correct_2')
        btn2 = types.InlineKeyboardButton('Swimming', callback_data='skills_img_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('Cooking', callback_data='skills_img_a1a2_wrong_2')
        btn4 = types.InlineKeyboardButton('Sleeping', callback_data='skills_img_a1a2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/drawing.jpeg', 'rb'),
                      caption="<b>2/3.</b> Какое хобби изображено?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('They are working.', callback_data='skills_img_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('They are exercising.', callback_data='skills_img_a1a2_correct_3')
        btn3 = types.InlineKeyboardButton('They are eating.', callback_data='skills_img_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/sports.jpeg', 'rb'),
                      caption="<b>3/3.</b> Что делают эти люди?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Skills and Hobbies - Image Tasks (B1-B2)
# ==============================================
def send_image_task_skills_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Business meeting', callback_data='skills_img_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Gardening workshop', callback_data='skills_img_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('Art class', callback_data='skills_img_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/gardening_workshop.jpeg', 'rb'),
                      caption="<b>1/3.</b> What is happening in the picture?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Graphic design', callback_data='skills_img_b1b2_correct_2')
        btn2 = types.InlineKeyboardButton('Medical operation', callback_data='skills_img_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Carpentry', callback_data='skills_img_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('Teaching', callback_data='skills_img_b1b2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/design.jpeg', 'rb'),
                      caption="<b>2/3.</b> What skill is being demonstrated?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Watching TV', callback_data='skills_img_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('Online learning', callback_data='skills_img_b1b2_correct_3')
        btn3 = types.InlineKeyboardButton('Playing games', callback_data='skills_img_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/online_learning.jpeg', 'rb'),
                      caption="<b>3/3.</b> What is the person doing?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Education and Studying - Image Tasks (A1-A2)
# ==============================================
def send_image_task_education_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Hospital', callback_data='edu_img_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('School', callback_data='edu_img_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('Restaurant', callback_data='edu_img_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('Library', callback_data='edu_img_a1a2_correct_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_photo(user_id, photo=open('images/library.jpeg', 'rb'),
                      caption="<b>1/3.</b> Что это за место?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Workplace', callback_data='edu_img_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('University canteen', callback_data='edu_img_a1a2_correct_2')
        btn3 = types.InlineKeyboardButton('Clothing shop', callback_data='edu_img_a1a2_wrong_2')
        btn4 = types.InlineKeyboardButton('Drugstore', callback_data='edu_img_a1a2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/canteen.jpeg', 'rb'),
                      caption="<b>2/3.</b> Куда студенты ходят на обед?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Taking an exam', callback_data='edu_img_a1a2_correct_3')
        btn2 = types.InlineKeyboardButton('Relaxing', callback_data='edu_img_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('Giving a presentation', callback_data='edu_img_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/exam.jpg', 'rb'),
                      caption="<b>3/3.</b> Что делают эти обучающиеся?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Education and Studying - Image Tasks (B1-B2)
# ==============================================
def send_image_task_education_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Discussion between partners', callback_data='edu_img_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('University lecture', callback_data='edu_img_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('College graduation', callback_data='edu_img_b1b2_correct_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/graduation.jpeg', 'rb'),
                      caption="<b>1/3.</b> What event is on the picture?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Maths', callback_data='edu_img_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('Chemistry', callback_data='edu_img_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Biology', callback_data='edu_img_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('Geography', callback_data='edu_img_b1b2_correct_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/geography_class.jpg', 'rb'),
                      caption="<b>2/3.</b> What is this class?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Having a party', callback_data='edu_img_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('Working on a group project', callback_data='edu_img_b1b2_correct_3')
        btn3 = types.InlineKeyboardButton('Watching a movie', callback_data='edu_img_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/group_project.jpeg', 'rb'),
                      caption="<b>3/3.</b> What are they doing?",
                      reply_markup=markup, parse_mode='html')

# ==============================================
# Work and Jobs - Image Tasks (A1-A2)
# ==============================================
def send_image_task_work_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Office', callback_data='work_img_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('School', callback_data='work_img_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('Hospital', callback_data='work_img_a1a2_correct_1')
        markup.row(btn1, btn2, btn3)
        bot.send_photo(user_id, photo=open('images/doctors.jpeg', 'rb'),
                      caption="<b>1/3.</b> Где работают эти люди?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Doctor', callback_data='work_img_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('Teacher', callback_data='work_img_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('Driver', callback_data='work_img_a1a2_correct_2')
        btn4 = types.InlineKeyboardButton('Farmer', callback_data='work_img_a1a2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/driver.jpeg', 'rb'),
                      caption="<b>2/3.</b> Человек какой профессии изображен на картинке?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Having lunch', callback_data='work_img_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('Job interview', callback_data='work_img_a1a2_correct_3')
        btn3 = types.InlineKeyboardButton('Business meeting', callback_data='work_img_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/job_interview.jpg', 'rb'),
                      caption="<b>3/3.</b> Что происходит на этом изображении?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Work and Jobs - Image Tasks (B1-B2)
# ==============================================
def send_image_task_work_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Remote work', callback_data='work_img_b1b2_correct_1')
        btn2 = types.InlineKeyboardButton('Vacation', callback_data='work_img_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('Business trip', callback_data='work_img_b1b2_wrong_1')
        markup.row(btn1, btn2, btn3)
        bot.send_photo(user_id, photo=open('images/remote_work.jpg', 'rb'),
                      caption="<b>1/3.</b> What work style is shown?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Salary negotiation', callback_data='work_img_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('Team building', callback_data='work_img_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Career ladder', callback_data='work_img_b1b2_correct_2')
        btn4 = types.InlineKeyboardButton('Job fair', callback_data='work_img_b1b2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/career.jpg', 'rb'),
                      caption="<b>2/3.</b> What concept does this image represent?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Work-life balance', callback_data='work_img_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('Burnout', callback_data='work_img_b1b2_correct_3')
        btn3 = types.InlineKeyboardButton('Team celebration', callback_data='work_img_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/burnout.jpg', 'rb'),
                      caption="<b>3/3.</b> What is shown in the picture?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Daily life and Routine - Image Tasks (A1-A2)
# ==============================================
def send_image_task_daily_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Brushing teeth', callback_data='daily_img_a1a2_correct_1')
        btn2 = types.InlineKeyboardButton('Washing dishes', callback_data='daily_img_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('Cooking dinner', callback_data='daily_img_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/brushing_teeth.jpg', 'rb'),
                      caption="<b>1/3.</b> Какое каждодневное действие изображено на картинке?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Recipe', callback_data='daily_img_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('Shopping list', callback_data='daily_img_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('Daily schedule', callback_data='daily_img_a1a2_correct_2')
        btn4 = types.InlineKeyboardButton('Calendar', callback_data='daily_img_a1a2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/schedule.jpg', 'rb'),
                      caption="<b>2/3.</b> Что изображено на этом фото?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Going to work', callback_data='daily_img_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('Having dinner', callback_data='daily_img_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('Playing board games', callback_data='daily_img_a1a2_wrong_3')
        btn4 = types.InlineKeyboardButton('Shopping for food', callback_data='daily_img_a1a2_correct_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_photo(user_id, photo=open('images/shopping.jpg', 'rb'),
                      caption="<b>3/3.</b> Что они делают?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Daily life and Routine - Image Tasks (B1-B2)
# ==============================================
def send_image_task_daily_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Meeting his friends', callback_data='daily_img_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Commuting to work', callback_data='daily_img_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('Going to the store', callback_data='daily_img_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/commute.jpg', 'rb'),
                      caption="<b>1/3.</b> What is this person doing?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Work-life balance', callback_data='daily_img_b1b2_correct_2')
        btn2 = types.InlineKeyboardButton('Financial planning', callback_data='daily_img_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Health diet', callback_data='daily_img_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('Time management', callback_data='daily_img_b1b2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/work_life_balance.jpg', 'rb'),
                      caption="<b>2/3.</b> What concept does this represent?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Meditation', callback_data='daily_img_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('Jogging', callback_data='daily_img_b1b2_correct_3')
        btn3 = types.InlineKeyboardButton('Sleeping', callback_data='daily_img_b1b2_wrong_3')
        btn4 = types.InlineKeyboardButton('Exercising', callback_data='daily_img_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_photo(user_id, photo=open('images/jogging.jpg', 'rb'),
                      caption="<b>3/3.</b> What morning routine is this?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Travelling and Transport - Image Tasks (A1-A2)
# ==============================================
def send_image_task_travel_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Airport', callback_data='travel_img_a1a2_correct_1')
        btn2 = types.InlineKeyboardButton('Train station', callback_data='travel_img_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('Bus stop', callback_data='travel_img_a1a2_wrong_1')
        markup.row(btn1, btn2, btn3)
        bot.send_photo(user_id, photo=open('images/airport.jpg', 'rb'),
                      caption="<b>1/3.</b> Что это за место?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Backpack', callback_data='travel_img_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('Hand luggage', callback_data='travel_img_a1a2_correct_2')
        btn3 = types.InlineKeyboardButton('Baggage', callback_data='travel_img_a1a2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/hand_luggage.jpg', 'rb'),
                      caption="<b>2/3.</b> Что она катит за собой?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Small town', callback_data='travel_img_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('Province', callback_data='travel_img_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('Capital city', callback_data='travel_img_a1a2_correct_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/london.jpg', 'rb'),
                      caption="<b>3/3.</b> Каким городом является Лондон?",
                      reply_markup=markup, parse_mode='html')



# ==============================================
# Travelling and Transport - Image Tasks (B1-B2)
# ==============================================
def send_image_task_travel_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Ecotourism', callback_data='travel_img_b1b2_correct_1')
        btn2 = types.InlineKeyboardButton('Business travel', callback_data='travel_img_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('Adventure sports', callback_data='travel_img_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('Cultural tourism', callback_data='travel_img_b1b2_wrong_1')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/ecotourism.jpg', 'rb'),
                      caption="<b>1/3.</b> What type of tourism is shown?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Train delay', callback_data='travel_img_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('Public holiday', callback_data='travel_img_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Rush hour', callback_data='travel_img_b1b2_correct_2')
        btn4 = types.InlineKeyboardButton('Tourist season', callback_data='travel_img_b1b2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/rush_hour.jpg', 'rb'),
                      caption="<b>2/3.</b> What situation is this?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('The Backpacker', callback_data='travel_img_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('The Planner', callback_data='travel_img_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('The Shopper', callback_data='travel_img_b1b2_correct_3')
        btn4 = types.InlineKeyboardButton('The Luxury Traveller', callback_data='travel_img_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_photo(user_id, photo=open('images/shopper.jpg', 'rb'),
                      caption="<b>3/3.</b> What type of traveller are they?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Health and Medicine - Image Tasks (A1-A2)
# ==============================================
def send_image_task_health_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Ambulance car', callback_data='health_img_a1a2_correct_1')
        btn2 = types.InlineKeyboardButton('School bus', callback_data='health_img_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('Police truck', callback_data='health_img_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2, btn3)
        bot.send_photo(user_id, photo=open('images/ambulance.jpg', 'rb'),
                      caption="<b>1/3.</b> Как называется этот специальный автомобиль?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Doctor', callback_data='health_img_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('Nurse', callback_data='health_img_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('Dentist', callback_data='health_img_a1a2_wrong_2')
        btn4 = types.InlineKeyboardButton('Pharmacist', callback_data='health_img_a1a2_correct_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/pharmacist.jpg', 'rb'),
                      caption="<b>2/3.</b> Какое слово подходит для описания этого специалиста?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Eye drops', callback_data='health_img_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('Pills', callback_data='health_img_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('Capsules', callback_data='health_img_a1a2_wrong_3')
        btn4 = types.InlineKeyboardButton('Cough syrup', callback_data='health_img_a1a2_correct_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_photo(user_id, photo=open('images/cough_syrup.jpg', 'rb'),
                      caption="<b>3/3.</b> Как называется изображенный на картинке тип лекарства?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Health and Medicine - Image Tasks (B1-B2)
# ==============================================
def send_image_task_health_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Telemedicine', callback_data='health_img_b1b2_correct_1')
        btn2 = types.InlineKeyboardButton('Online teaching', callback_data='health_img_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('Video conference', callback_data='health_img_b1b2_wrong_1')
        markup.row(btn2, btn3)
        markup.row(btn1)
        bot.send_photo(user_id, photo=open('images/telemedicine.jpg', 'rb'),
                      caption="<b>1/3.</b> What medical practice is shown?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Vaccination', callback_data='health_img_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('Temperature measurement', callback_data='health_img_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Blood pressure check', callback_data='health_img_b1b2_correct_2')
        btn4 = types.InlineKeyboardButton('First aid', callback_data='health_img_b1b2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_photo(user_id, photo=open('images/blood_pressure.jpg', 'rb'),
                      caption="<b>2/3.</b> What health check is this?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Yoga practice', callback_data='health_img_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('Dancing class', callback_data='health_img_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('Martial arts', callback_data='health_img_b1b2_correct_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/martial_arts.jpg', 'rb'),
                      caption="<b>3/3.</b> What wellness activity is this?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Shopping - Image Tasks (A1-A2)
# ==============================================
def send_image_task_shopping_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Supermarket', callback_data='shop_img_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('Shop around the corner', callback_data='shop_img_a1a2_correct_1')
        btn3 = types.InlineKeyboardButton('Hypermarket', callback_data='shop_img_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/around_the_corner.jpg', 'rb'),
                      caption="<b>1/3.</b> Как называется подобный продуктовый магазин?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Music shop', callback_data='shop_img_a1a2_correct_2')
        btn2 = types.InlineKeyboardButton('Electronics store', callback_data='shop_img_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('Bookshop', callback_data='shop_img_a1a2_wrong_2')
        btn4 = types.InlineKeyboardButton('Pharmacy', callback_data='shop_img_a1a2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/music_shop.jpg', 'rb'),
                      caption="<b>2/3.</b> На чем специализируется этот магазин?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Returning items', callback_data='shop_img_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('Asking for help', callback_data='shop_img_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('Paying at checkout', callback_data='shop_img_a1a2_correct_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/paying.jpg', 'rb'),
                      caption="<b>3/3.</b> Что делает клиент на этой картинке?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Shopping - Image Tasks (B1-B2)
# ==============================================
def send_image_task_shopping_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Online shopping', callback_data='shop_img_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Wholesale Shopping', callback_data='shop_img_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('Retail shopping', callback_data='shop_img_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('Second-hand Shopping', callback_data='shop_img_b1b2_correct_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_photo(user_id, photo=open('images/second_hand.jpg', 'rb'),
                      caption="<b>1/3.</b> What activity is shown?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Price comparison', callback_data='shop_img_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('Product testing', callback_data='shop_img_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Quality check', callback_data='shop_img_b1b2_correct_2')
        btn4 = types.InlineKeyboardButton('Discount hunting', callback_data='shop_img_b1b2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/quality_check.jpg', 'rb'),
                      caption="<b>2/3.</b> What shopping strategy is this?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Impulse buying', callback_data='shop_img_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('Planned purchase', callback_data='shop_img_b1b2_correct_3')
        btn3 = types.InlineKeyboardButton('Returning goods', callback_data='shop_img_b1b2_wrong_3')
        btn4 = types.InlineKeyboardButton('Subscription Shopping', callback_data='shop_img_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_photo(user_id, photo=open('images/planned_purchase.jpg', 'rb'),
                      caption="<b>3/3.</b> What buying behavior is shown?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Food - Image Tasks (A1-A2)
# ==============================================
def send_image_task_food_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Restaurant', callback_data='food_img_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('Cafe', callback_data='food_img_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('Bar', callback_data='food_img_a1a2_correct_1')
        markup.row(btn1, btn2, btn3)
        bot.send_photo(user_id, photo=open('images/bar.jpg', 'rb'),
                      caption="<b>1/3.</b> Что это за место?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Soup', callback_data='food_img_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('Salad', callback_data='food_img_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('Pasta', callback_data='food_img_a1a2_correct_2')
        btn4 = types.InlineKeyboardButton('Dessert', callback_data='food_img_a1a2_wrong_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/pasta.jpg', 'rb'),
                      caption="<b>2/3.</b> Какое блюдо изображено на фото?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Breakfast', callback_data='food_img_a1a2_correct_3')
        btn2 = types.InlineKeyboardButton('Lunch', callback_data='food_img_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('Dinner', callback_data='food_img_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/breakfast.jpg', 'rb'),
                      caption="<b>3/3.</b> Какой прием пищи изображен на картинке?",
                      reply_markup=markup, parse_mode='html')

# ==============================================
# Food - Image Tasks (B1-B2)
# ==============================================
def send_image_task_food_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Vitamins', callback_data='food_img_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Minerals', callback_data='food_img_b1b2_wrong_1')
        btn3 = types.InlineKeyboardButton('Carbohydrates', callback_data='food_img_b1b2_correct_1')
        btn4 = types.InlineKeyboardButton('Fiber', callback_data='food_img_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_photo(user_id, photo=open('images/fastfood.jpg', 'rb'),
                      caption="<b>1/3.</b> This food is rich in...",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Food blogger', callback_data='food_img_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('Chef', callback_data='food_img_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Waiter', callback_data='food_img_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('Nutritionist', callback_data='food_img_b1b2_correct_2')
        markup.row(btn1, btn2)
        markup.row(btn3, btn4)
        bot.send_photo(user_id, photo=open('images/nutritionist.jpg', 'rb'),
                      caption="<b>2/3.</b> Who is this person?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Grab to go', callback_data='food_img_b1b2_correct_3')
        btn2 = types.InlineKeyboardButton('Cook at home', callback_data='food_img_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('Eat out in a restaurant', callback_data='food_img_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        bot.send_photo(user_id, photo=open('images/to_go.jpg', 'rb'),
                      caption="<b>3/3.</b> What way of having a meal is shown?",
                      reply_markup=markup, parse_mode='html')




# ==============================================
# Family and Friends - Audio Tasks (A1-A2)
# ==============================================
def send_audio_task_family_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Alex describes his job and daily routine.', callback_data='family_audio_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('Alex explains why he wants to move to another city.', callback_data='family_audio_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('Alex talks about his family and friends.', callback_data='family_audio_a1a2_correct_1')
        btn4 = types.InlineKeyboardButton('Alex speaks about his favorite hobbies.', callback_data='family_audio_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/family_a1a2.mp3', 'rb'),
                       caption="<b>1/5.</b> Прослушайте аудиозапись и выполните задания. В чем заключается главная идея?",
                       reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('They are not important to him', callback_data='family_audio_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('They never have fun together', callback_data='family_audio_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('They support each other', callback_data='family_audio_a1a2_correct_2')
        btn4 = types.InlineKeyboardButton("They don't like him", callback_data='family_audio_a1a2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What does Alex say about his friends?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Playing football and going to the cinema', callback_data='family_audio_a1a2_correct_3')
        btn2 = types.InlineKeyboardButton('Playing video games and reading books', callback_data='family_audio_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('Traveling and cooking', callback_data='family_audio_a1a2_wrong_3')
        btn4 = types.InlineKeyboardButton('Swimming and cycling', callback_data='family_audio_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What does Alex like doing with his best friend John?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Alex’s best friend', callback_data='family_audio_a1a2_wrong_4')
        btn2 = types.InlineKeyboardButton('Alex’s brother', callback_data='family_audio_a1a2_wrong_4')
        btn3 = types.InlineKeyboardButton('Alex’s son', callback_data='family_audio_a1a2_correct_4')
        btn4 = types.InlineKeyboardButton("Alex’s father", callback_data='family_audio_a1a2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> Who is Tom?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('They help him with work', callback_data='family_audio_a1a2_wrong_5')
        btn2 = types.InlineKeyboardButton('They make him happy', callback_data='family_audio_a1a2_correct_5')
        btn3 = types.InlineKeyboardButton('They live far away', callback_data='family_audio_a1a2_wrong_5')
        btn4 = types.InlineKeyboardButton('They are very rich', callback_data='family_audio_a1a2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> Why are his family and friends important to him?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Family and Friends - Audio Tasks (B1-B2)
# ==============================================
def send_audio_task_family_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Modern work challenges', callback_data='family_audio_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Changes in family structures and relationships', callback_data='family_audio_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('History of family traditions', callback_data='family_audio_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('Impact of technology on education', callback_data='family_audio_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/family_b1b2.mp3', 'rb'),
                       caption="<b>1/5.</b> Listen and complete the tasks. What is the audio mainly about?",
                       reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Only nuclear families still exist today', callback_data='family_audio_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('People no longer value family connections', callback_data='family_audio_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Different family types are now common', callback_data='family_audio_b1b2_correct_2')
        btn4 = types.InlineKeyboardButton('Traditional families have completely disappeared', callback_data='family_audio_b1b2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What is said about modern family structures?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('They live far away and rarely visit', callback_data='family_audio_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('They dislike modern technology', callback_data='family_audio_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton("They don't share stories with younger generations", callback_data='family_audio_b1b2_wrong_3')
        btn4 = types.InlineKeyboardButton('They organize family dinners and preserve traditions', callback_data='family_audio_b1b2_correct_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What role do the author's grandparents play in the family?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Through social media only', callback_data='family_audio_b1b2_wrong_4')
        btn2 = types.InlineKeyboardButton('Through childhood friends and interest groups', callback_data='family_audio_b1b2_correct_4')
        btn3 = types.InlineKeyboardButton('Only through work colleagues', callback_data='family_audio_b1b2_wrong_4')
        btn4 = types.InlineKeyboardButton('By traveling to different countries', callback_data='family_audio_b1b2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> How has the author developed friendships?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('They help with financial stability', callback_data='family_audio_b1b2_wrong_5')
        btn2 = types.InlineKeyboardButton('They provide emotional support & create memories', callback_data='family_audio_b1b2_correct_5')
        btn3 = types.InlineKeyboardButton('They allow for professional networking', callback_data='family_audio_b1b2_wrong_5')
        btn4 = types.InlineKeyboardButton('They replace the need for hobbies', callback_data='family_audio_b1b2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> Why are family and friend gatherings important to the author?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Skills and Hobbies - Audio Tasks (A1-A2)
# ==============================================
def send_audio_task_skills_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('James discusses his work problems.', callback_data='skills_audio_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('James describes his hobbies and free time.', callback_data='skills_audio_a1a2_correct_1')
        btn3 = types.InlineKeyboardButton('James explains his travel plans.', callback_data='skills_audio_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('James talks about his childhood.', callback_data='skills_audio_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/skills_a1a2.mp3', 'rb'),
                       caption="<b>1/5.</b> Прослушайте запись и выполните задания. В чем заключается главная идея?",
                       reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('On Mondays and Wednesdays', callback_data='skills_audio_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('On weekends', callback_data='skills_audio_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('On Tuesdays and Fridays', callback_data='skills_audio_a1a2_correct_2')
        btn4 = types.InlineKeyboardButton("Every evening", callback_data='skills_audio_a1a2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> When does James play tennis?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('His brother', callback_data='skills_audio_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('His friend', callback_data='skills_audio_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('His brother-in-law', callback_data='skills_audio_a1a2_correct_3')
        btn4 = types.InlineKeyboardButton('His teacher', callback_data='skills_audio_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> Who teaches James to play guitar?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Because it helps him relax', callback_data='skills_audio_a1a2_correct_4')
        btn2 = types.InlineKeyboardButton('Because his friends do it', callback_data='skills_audio_a1a2_wrong_4')
        btn3 = types.InlineKeyboardButton('Because it is easy', callback_data='skills_audio_a1a2_wrong_4')
        btn4 = types.InlineKeyboardButton("Because he has to", callback_data='skills_audio_a1a2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> Why does James like reading books?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Tennis and gardening', callback_data='skills_audio_a1a2_wrong_5')
        btn2 = types.InlineKeyboardButton('Tennis and photography', callback_data='skills_audio_a1a2_correct_5')
        btn3 = types.InlineKeyboardButton('Cooking and photography', callback_data='skills_audio_a1a2_wrong_5')
        btn4 = types.InlineKeyboardButton('Reading and gardening', callback_data='skills_audio_a1a2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> What are James's two main hobbies?",
                      reply_markup=markup, parse_mode='html')

# ==============================================
# Skills and Hobbies - Audio Tasks (B1-B2)
# ==============================================
def send_audio_task_skills_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('The difficulties of modern education', callback_data='skills_audio_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('The importance of learning different skills', callback_data='skills_audio_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('How to choose a university', callback_data='skills_audio_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('The best jobs in modern world', callback_data='skills_audio_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/skills_b1b2.mp3', 'rb'),
                     caption="<b>1/5.</b> Listen and complete the tasks. What is the audio about?",
                     reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Photography and languages', callback_data='skills_audio_b1b2_correct_2')
        btn2 = types.InlineKeyboardButton('Dancing and singing', callback_data='skills_audio_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Writing and drawing', callback_data='skills_audio_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('Swimming and running', callback_data='skills_audio_b1b2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> Which skills helped the speaker in work?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('From university professors', callback_data='skills_audio_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('From books only', callback_data='skills_audio_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('From work colleagues', callback_data='skills_audio_b1b2_wrong_3')
        btn4 = types.InlineKeyboardButton('From online courses and apps', callback_data='skills_audio_b1b2_correct_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> How does the speaker learn new skills?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Chess and cooking', callback_data='skills_audio_b1b2_correct_4')
        btn2 = types.InlineKeyboardButton('Football and basketball', callback_data='skills_audio_b1b2_wrong_4')
        btn3 = types.InlineKeyboardButton('Reading and writing', callback_data='skills_audio_b1b2_wrong_4')
        btn4 = types.InlineKeyboardButton('Music and art', callback_data='skills_audio_b1b2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> Which hobbies improved other skills?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Because they are easy', callback_data='skills_audio_b1b2_wrong_5')
        btn2 = types.InlineKeyboardButton('Because they help in different situations', callback_data='skills_audio_b1b2_correct_5')
        btn3 = types.InlineKeyboardButton('Because everyone learns them', callback_data='skills_audio_b1b2_wrong_5')
        btn4 = types.InlineKeyboardButton('Because teachers recommend them', callback_data='skills_audio_b1b2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> Why is learning different skills useful?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Education and Studying - Audio Tasks (A1-A2)
# ==============================================
def send_audio_task_education_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('A teacher talking about school rules', callback_data='edu_audio_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('A student describing her school day', callback_data='edu_audio_a1a2_correct_1')
        btn3 = types.InlineKeyboardButton('A parent discussing school choices', callback_data='edu_audio_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('A principal giving a speech', callback_data='edu_audio_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/education_a1a2.mp3', 'rb'),
                       caption="<b>1/5.</b> Прослушайте запись и выполните задания. Кто говорит на записи?",
                       reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Math and Science', callback_data='edu_audio_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton("PE and Geography", callback_data='edu_audio_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('Art and Music', callback_data='edu_audio_a1a2_wrong_2')
        btn4 = types.InlineKeyboardButton('English and History', callback_data='edu_audio_a1a2_correct_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What are the speaker's favorite subjects?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('At 8:00 am', callback_data='edu_audio_a1a2_correct_3')
        btn2 = types.InlineKeyboardButton('At 9:00 am', callback_data='edu_audio_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('At 10:00 am', callback_data='edu_audio_a1a2_wrong_3')
        btn4 = types.InlineKeyboardButton('At 7:30 am', callback_data='edu_audio_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What time does school start?",
                      reply_markup=markup, parse_mode='html')


    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Because it is easy', callback_data='edu_audio_a1a2_wrong_5')
        btn2 = types.InlineKeyboardButton('Because the teacher is nice', callback_data='edu_audio_a1a2_wrong_5')
        btn3 = types.InlineKeyboardButton('Because she likes reading stories', callback_data='edu_audio_a1a2_correct_5')
        btn4 = types.InlineKeyboardButton('Because it is her only option', callback_data='edu_audio_a1a2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> Why does the speaker like English?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('You have to go there', callback_data='edu_audio_a1a2_wrong_4')
        btn2 = types.InlineKeyboardButton('You can skip classes ', callback_data='edu_audio_a1a2_wrong_4')
        btn3 = types.InlineKeyboardButton('You can learn many things and make friends', callback_data='edu_audio_a1a2_correct_4')
        btn4 = types.InlineKeyboardButton("You can have fun", callback_data='edu_audio_a1a2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> Why is school important to the speaker?",
                      reply_markup=markup, parse_mode='html')

# ==============================================
# Education and Studying - Audio Tasks (B1-B2)
# ==============================================
def send_audio_task_education_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Problems in modern schools', callback_data='education_audio_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Changes and benefits in modern education', callback_data='education_audio_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('History of education systems', callback_data='education_audio_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('How to choose a university', callback_data='education_audio_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/education_b1b2.mp3', 'rb'),
                     caption="<b>1/5.</b> Listen to the text. What is the audio about?",
                     reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Remembering facts', callback_data='education_audio_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('Writing quickly', callback_data='education_audio_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Critical thinking', callback_data='education_audio_b1b2_correct_2')
        btn4 = types.InlineKeyboardButton('Working alone', callback_data='education_audio_b1b2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What does modern education focus on?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Teamwork and leadership', callback_data='education_audio_b1b2_correct_3')
        btn2 = types.InlineKeyboardButton('Cooking and cleaning', callback_data='education_audio_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('Drawing and painting', callback_data='education_audio_b1b2_wrong_3')
        btn4 = types.InlineKeyboardButton('Singing and dancing', callback_data='education_audio_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What skills did the speaker learn outside class?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('It will be more expensive', callback_data='education_audio_b1b2_wrong_4')
        btn2 = types.InlineKeyboardButton('It will be shorter', callback_data='education_audio_b1b2_wrong_4')
        btn3 = types.InlineKeyboardButton('It will be only online', callback_data='education_audio_b1b2_wrong_4')
        btn4 = types.InlineKeyboardButton('It will be more personalized', callback_data='education_audio_b1b2_correct_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> How will education change in the future?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Because they give tests', callback_data='education_audio_b1b2_wrong_5')
        btn2 = types.InlineKeyboardButton('Because they inspire curiosity', callback_data='education_audio_b1b2_correct_5')
        btn3 = types.InlineKeyboardButton('Because they work online', callback_data='education_audio_b1b2_wrong_5')
        btn4 = types.InlineKeyboardButton('Because they know everything', callback_data='education_audio_b1b2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> Why are teachers still important?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Work and Jobs - Audio Tasks (A1-A2)
# ==============================================
def send_audio_task_work_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('A doctor describing his hospital', callback_data='work_audio_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('A teacher talking about her school', callback_data='work_audio_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('An office worker describing his daily routine', callback_data='work_audio_a1a2_correct_1')
        btn4 = types.InlineKeyboardButton('A chef explaining restaurant work', callback_data='work_audio_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/work_a1a2.mp3', 'rb'),
                       caption="<b>1/5.</b> Прослушайте запись и выполните задания. Кто говорит на записи?",
                       reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('At 7:00 am', callback_data='work_audio_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('At 8:00 am', callback_data='work_audio_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('At 9:00 am', callback_data='work_audio_a1a2_correct_2')
        btn4 = types.InlineKeyboardButton("At 10:00 am", callback_data='work_audio_a1a2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What time does the speaker start working?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Answering emails', callback_data='work_audio_a1a2_correct_3')
        btn2 = types.InlineKeyboardButton('Making coffee', callback_data='work_audio_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('Cleaning the office', callback_data='work_audio_a1a2_wrong_3')
        btn4 = types.InlineKeyboardButton('Teaching students', callback_data='work_audio_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What is the first thing the speaker does at work?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('At home', callback_data='work_audio_a1a2_wrong_4')
        btn2 = types.InlineKeyboardButton('In a restaurant', callback_data='work_audio_a1a2_correct_4')
        btn3 = types.InlineKeyboardButton('At his desk', callback_data='work_audio_a1a2_wrong_4')
        btn4 = types.InlineKeyboardButton("In a park", callback_data='work_audio_a1a2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> Where does the speaker have lunch?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Because it is easy', callback_data='work_audio_a1a2_wrong_5')
        btn2 = types.InlineKeyboardButton('Because he works short hours', callback_data='work_audio_a1a2_wrong_5')
        btn3 = types.InlineKeyboardButton('Because he makes friends there', callback_data='work_audio_a1a2_wrong_5')
        btn4 = types.InlineKeyboardButton('Because he earns money and helps people', callback_data='work_audio_a1a2_correct_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> Why is work important according to the speaker?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Work and Jobs - Audio Tasks (B1-B2)
# ==============================================
def send_audio_task_work_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Problems in modern offices', callback_data='work_audio_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Changes in the modern workplace', callback_data='work_audio_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('How to start a tech company', callback_data='work_audio_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('History of work traditions', callback_data='work_audio_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/work_b1b2.mp3', 'rb'),
                     caption="<b>1/5.</b> Listen and complete the tasks. What is the audio about?",
                     reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Strict schedules', callback_data='work_audio_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('Working only in offices', callback_data='work_audio_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Long working hours', callback_data='work_audio_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('Flexibility and work-life balance', callback_data='work_audio_b1b2_correct_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What is important in modern workplaces?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Communication and adaptability', callback_data='work_audio_b1b2_correct_3')
        btn2 = types.InlineKeyboardButton('Only technical skills', callback_data='work_audio_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('Physical strength', callback_data='work_audio_b1b2_wrong_3')
        btn4 = types.InlineKeyboardButton('Memory skills', callback_data='work_audio_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What kind of skills do employers value now?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Construction and farming', callback_data='work_audio_b1b2_wrong_4')
        btn2 = types.InlineKeyboardButton('Medicine and law', callback_data='work_audio_b1b2_wrong_4')
        btn3 = types.InlineKeyboardButton('Graphic design and teaching', callback_data='work_audio_b1b2_correct_4')
        btn4 = types.InlineKeyboardButton('Accounting and banking', callback_data='work_audio_b1b2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> What does the speaker's friend do for work?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('People will work longer hours', callback_data='work_audio_b1b2_wrong_5')
        btn2 = types.InlineKeyboardButton('Automation will handle simple tasks', callback_data='work_audio_b1b2_correct_5')
        btn3 = types.InlineKeyboardButton('Everyone will work from home', callback_data='work_audio_b1b2_wrong_5')
        btn4 = types.InlineKeyboardButton('Companies will become smaller', callback_data='work_audio_b1b2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> How will work change in the future?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Daily life and routine - Audio Tasks (A1-A2)
# ==============================================
def send_audio_task_daily_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("A student's weekend activities", callback_data='daily_audio_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton("A teacher's work schedule", callback_data='daily_audio_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton("A librarian's typical weekday routine", callback_data='daily_audio_a1a2_correct_1')
        btn4 = types.InlineKeyboardButton("A doctor's busy day", callback_data='daily_audio_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/daily_a1a2.mp3', 'rb'),
                       caption="<b>1/5.</b> Прослушайте аудиозапись и выполните задания. Чему посвящена аудиозапись?",
                       reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('At 6:00 am', callback_data='daily_audio_a1a2_correct_2')
        btn2 = types.InlineKeyboardButton('At 7:00 am', callback_data='daily_audio_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('At 8:00 am', callback_data='daily_audio_a1a2_wrong_2')
        btn4 = types.InlineKeyboardButton("At 9:00 am", callback_data='daily_audio_a1a2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What time does the speaker wake up?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('She goes jogging', callback_data='daily_audio_a1a2_correct_3')
        btn2 = types.InlineKeyboardButton('She reads the newspaper', callback_data='daily_audio_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('She checks her phone', callback_data='daily_audio_a1a2_wrong_3')
        btn4 = types.InlineKeyboardButton('She makes breakfast', callback_data='daily_audio_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What is the first thing she does in the morning?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('At 12:00 pm', callback_data='daily_audio_a1a2_wrong_4')
        btn2 = types.InlineKeyboardButton('At 1:00 pm', callback_data='daily_audio_a1a2_correct_4')
        btn3 = types.InlineKeyboardButton('At 2:00 pm', callback_data='daily_audio_a1a2_wrong_4')
        btn4 = types.InlineKeyboardButton("At 3:00 pm", callback_data='daily_audio_a1a2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> When does the speaker have lunch?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Watching TV', callback_data='daily_audio_a1a2_wrong_5')
        btn2 = types.InlineKeyboardButton('Reading books', callback_data='daily_audio_a1a2_correct_5')
        btn3 = types.InlineKeyboardButton('Playing video games', callback_data='daily_audio_a1a2_wrong_5')
        btn4 = types.InlineKeyboardButton('Cooking dinner', callback_data='daily_audio_a1a2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> What does the speaker like to do before bed?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Daily life and routine - Audio Tasks (B1-B2)
# ==============================================
def send_audio_task_daily_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('How to find a good job', callback_data='daily_audio_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Tips for balancing work and personal life', callback_data='daily_audio_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('Best meditation techniques', callback_data='daily_audio_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('History of work schedules', callback_data='daily_audio_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/daily_b1b2.mp3', 'rb'),
                     caption="<b>1/5.</b> Listen and complete the tasks. What is the audio about?",
                     reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Checking emails', callback_data='daily_audio_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('Team meetings', callback_data='daily_audio_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Exercise at the gym', callback_data='daily_audio_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('Meditation and planning', callback_data='daily_audio_b1b2_correct_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What does the speaker start his mornings with?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Between 10 AM and 12 PM', callback_data='daily_audio_b1b2_correct_3')
        btn2 = types.InlineKeyboardButton('Between 8 AM and 10 AM', callback_data='daily_audio_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('Between 2 PM and 4 PM', callback_data='daily_audio_b1b2_wrong_3')
        btn4 = types.InlineKeyboardButton('Between 6 PM and 8 PM', callback_data='daily_audio_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> When is the speaker most creative?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('They only help with organization', callback_data='daily_audio_b1b2_wrong_4')
        btn2 = types.InlineKeyboardButton('They are completely useless', callback_data='daily_audio_b1b2_wrong_4')
        btn3 = types.InlineKeyboardButton('They help but can be distracting', callback_data='daily_audio_b1b2_correct_4')
        btn4 = types.InlineKeyboardButton('They replace human contact', callback_data='daily_audio_b1b2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> What does the speaker say about technology?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Working only from home', callback_data='daily_audio_b1b2_wrong_5')
        btn2 = types.InlineKeyboardButton('Mixing office and home days', callback_data='daily_audio_b1b2_correct_5')
        btn3 = types.InlineKeyboardButton('Working only on weekends', callback_data='daily_audio_b1b2_wrong_5')
        btn4 = types.InlineKeyboardButton('Working only in cafes', callback_data='daily_audio_b1b2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> What work schedule works best for the speaker?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Travelling and Transport - Audio Tasks (A1-A2)
# ==============================================
def send_audio_task_travel_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('A business trip', callback_data='travel_audio_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('A family vacation', callback_data='travel_audio_a1a2_correct_1')
        btn3 = types.InlineKeyboardButton('A school excursion', callback_data='travel_audio_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('A work conference', callback_data='travel_audio_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/travelling_a1a2.mp3', 'rb'),
                       caption="<b>1/5.</b> Прослушайте аудиозапись. О каком виде путешествия идет речь?",
                       reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('By train', callback_data='travel_audio_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('By car', callback_data='travel_audio_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('By plane', callback_data='travel_audio_a1a2_correct_2')
        btn4 = types.InlineKeyboardButton("By bus", callback_data='travel_audio_a1a2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> How did the speaker travel to London?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Ferries', callback_data='travel_audio_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('Taxis', callback_data='travel_audio_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('Bicycles', callback_data='travel_audio_a1a2_wrong_3')
        btn4 = types.InlineKeyboardButton('Underground trains', callback_data='travel_audio_a1a2_correct_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What kind of transportation did the speaker use most in the city?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Because it is cheap', callback_data='travel_audio_a1a2_wrong_4')
        btn2 = types.InlineKeyboardButton('Because it is are more comfortable', callback_data='travel_audio_a1a2_correct_4')
        btn3 = types.InlineKeyboardButton('Because you can see the city', callback_data='travel_audio_a1a2_wrong_4')
        btn4 = types.InlineKeyboardButton("Because it is fast", callback_data='travel_audio_a1a2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> Why does the speaker's friend like travelling by car?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Paris', callback_data='travel_audio_a1a2_correct_5')
        btn2 = types.InlineKeyboardButton('Rome', callback_data='travel_audio_a1a2_wrong_5')
        btn3 = types.InlineKeyboardButton('Berlin', callback_data='travel_audio_a1a2_wrong_5')
        btn4 = types.InlineKeyboardButton('Madrid', callback_data='travel_audio_a1a2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> Where does the speaker want to go next year?",
                      reply_markup=markup, parse_mode='html')

# ==============================================
# Travelling and Transport - Audio Tasks (B1-B2)
# ==============================================
def send_audio_task_travel_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('How to travel on a budget', callback_data='travel_audio_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Modern transportation developments', callback_data='travel_audio_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('History of airplanes', callback_data='travel_audio_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('Best travel destinations', callback_data='travel_audio_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/travelling_b1b2.mp3', 'rb'),
                     caption="<b>1/5.</b> Listen and complete the tasks. What is the audio about?",
                     reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Japan and Amsterdam', callback_data='travel_audio_b1b2_correct_2')
        btn2 = types.InlineKeyboardButton('France and Germany', callback_data='travel_audio_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('USA and Canada', callback_data='travel_audio_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('Italy and Spain', callback_data='travel_audio_b1b2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> Which places are mentioned as great transportation examples?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Bigger planes', callback_data='travel_audio_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('More flight attendants', callback_data='travel_audio_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('Faster boarding', callback_data='travel_audio_b1b2_wrong_3')
        btn4 = types.InlineKeyboardButton('Biofuels and electric planes', callback_data='travel_audio_b1b2_correct_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What could make air travel more eco-friendly?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('They replace all public transport', callback_data='travel_audio_b1b2_wrong_4')
        btn2 = types.InlineKeyboardButton('They work well with public transport', callback_data='travel_audio_b1b2_correct_4')
        btn3 = types.InlineKeyboardButton('They are too expensive', callback_data='travel_audio_b1b2_wrong_4')
        btn4 = types.InlineKeyboardButton('They are not popular', callback_data='travel_audio_b1b2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> How do ride-sharing apps work in the speaker's hometown?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Teleportation', callback_data='travel_audio_b1b2_wrong_5')
        btn2 = types.InlineKeyboardButton('Flying bicycles', callback_data='travel_audio_b1b2_wrong_5')
        btn3 = types.InlineKeyboardButton('Hyperloop trains and self-driving cars', callback_data='travel_audio_b1b2_correct_5')
        btn4 = types.InlineKeyboardButton('Underground tunnels', callback_data='travel_audio_b1b2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> What future transportation ideas are mentioned?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Health and Medicine - Audio Tasks (A1-A2)
# ==============================================
def send_audio_task_health_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('A doctor giving advice', callback_data='health_audio_a1a2_correct_1')
        btn2 = types.InlineKeyboardButton('A patient describing symptoms', callback_data='health_audio_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('A nurse explaining procedures', callback_data='health_audio_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('A pharmacist recommending medicine', callback_data='health_audio_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/health_a1a2.mp3', 'rb'),
                       caption="<b>1/5.</b> Прослушайте аудиозапись и выполните задания. Кто говорит на записи?",
                       reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Once a month', callback_data='health_audio_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('Twice a year', callback_data='health_audio_a1a2_correct_2')
        btn3 = types.InlineKeyboardButton('Every week', callback_data='health_audio_a1a2_wrong_2')
        btn4 = types.InlineKeyboardButton("Never", callback_data='health_audio_a1a2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> How often should you visit your doctor?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Two times a day', callback_data='health_audio_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('Once a month', callback_data='health_audio_a1a2_wrong_3')
        btn3 = types.InlineKeyboardButton('Three times a week', callback_data='health_audio_a1a2_correct_3')
        btn4 = types.InlineKeyboardButton('Every day', callback_data='health_audio_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> How often should you exercise?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('For headaches or cold', callback_data='health_audio_a1a2_correct_4')
        btn2 = types.InlineKeyboardButton('For stomachaches', callback_data='health_audio_a1a2_wrong_4')
        btn3 = types.InlineKeyboardButton('For back pain', callback_data='health_audio_a1a2_wrong_4')
        btn4 = types.InlineKeyboardButton("For sore throat", callback_data='health_audio_a1a2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> When should you take take medicine?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Eat more fast food', callback_data='health_audio_a1a2_wrong_5')
        btn2 = types.InlineKeyboardButton('Drink more soda', callback_data='health_audio_a1a2_wrong_5')
        btn3 = types.InlineKeyboardButton('Never take pills without advice', callback_data='health_audio_a1a2_correct_5')
        btn4 = types.InlineKeyboardButton('Sleep less', callback_data='health_audio_a1a2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> What health advice does the speaker give?",
                      reply_markup=markup, parse_mode='html')

# ==============================================
# Health and Medicine - Audio Tasks (B1-B2)
# ==============================================
def send_audio_task_health_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('How to become a doctor', callback_data='health_audio_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Modern healthcare approaches', callback_data='health_audio_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('History of medicine', callback_data='health_audio_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('Best hospitals in the world', callback_data='health_audio_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/health_b1b2.mp3', 'rb'),
                     caption="<b>1/5.</b> Listen and complete the tasks. What is the audio about?",
                     reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Treating serious diseases', callback_data='health_audio_b1b2_wrong_2')
        btn2 = types.InlineKeyboardButton('Surgical operations', callback_data='health_audio_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Emergency care', callback_data='health_audio_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('Preventing illness', callback_data='health_audio_b1b2_correct_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What does modern healthcare focus on?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Online shopping', callback_data='health_audio_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('Virtual reality games', callback_data='health_audio_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('Online doctor consultations', callback_data='health_audio_b1b2_correct_3')
        btn4 = types.InlineKeyboardButton('Video calls with friends', callback_data='health_audio_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What helped people during lockdowns?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Genetic test', callback_data='health_audio_b1b2_correct_4')
        btn2 = types.InlineKeyboardButton('Blood type test', callback_data='health_audio_b1b2_wrong_4')
        btn3 = types.InlineKeyboardButton('Allergy test', callback_data='health_audio_b1b2_wrong_4')
        btn4 = types.InlineKeyboardButton('Eye exam', callback_data='health_audio_b1b2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> What test helped the speaker understand health risks?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Smartphones', callback_data='health_audio_b1b2_wrong_5')
        btn2 = types.InlineKeyboardButton('Wearable devices', callback_data='health_audio_b1b2_correct_5')
        btn3 = types.InlineKeyboardButton('Home computers', callback_data='health_audio_b1b2_wrong_5')
        btn4 = types.InlineKeyboardButton('TVs', callback_data='health_audio_b1b2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> What technology helps track health?",
                      reply_markup=markup, parse_mode='html')

# ==============================================
# Shopping - Audio Tasks (A1-A2)
# ==============================================
def send_audio_task_shopping_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Different shopping habits', callback_data='shopping_audio_a1a2_correct_1')
        btn2 = types.InlineKeyboardButton('How to save money', callback_data='shopping_audio_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('History of supermarkets', callback_data='shopping_audio_a1a2_wrong_1')
        btn4 = types.InlineKeyboardButton('Best shopping apps', callback_data='shopping_audio_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/shopping_a1a2.mp3', 'rb'),
                     caption="<b>1/5.</b> Прослушайте аудиозапись и выполните задания. О чем эта запись?",
                     reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('On Sunday', callback_data='shopping_audio_a1a2_wrong_2')
        btn2 = types.InlineKeyboardButton('On Saturday', callback_data='shopping_audio_a1a2_correct_2')
        btn3 = types.InlineKeyboardButton('On Friday', callback_data='shopping_audio_a1a2_wrong_2')
        btn4 = types.InlineKeyboardButton('Every day', callback_data='shopping_audio_a1a2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> When does the speaker usually go shopping?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('The supermarket', callback_data='shopping_audio_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('The bookstore', callback_data='shopping_audio_a1a2_correct_3')
        btn3 = types.InlineKeyboardButton('The clothes shop', callback_data='shopping_audio_a1a2_wrong_3')
        btn4 = types.InlineKeyboardButton('The electronics store', callback_data='shopping_audio_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> Which shop does the speaker like most?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Because it has more discounts', callback_data='shopping_audio_a1a2_wrong_4')
        btn2 = types.InlineKeyboardButton('Because she can see products directly', callback_data='shopping_audio_a1a2_wrong_4')
        btn3 = types.InlineKeyboardButton('Because they have better quality', callback_data='shopping_audio_a1a2_correct_4')
        btn4 = types.InlineKeyboardButton('Because they are cheaper', callback_data='shopping_audio_a1a2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> Why does the grandmother prefer small shops?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Make a shopping list', callback_data='shopping_audio_a1a2_wrong_5')
        btn2 = types.InlineKeyboardButton('Buy everything online', callback_data='shopping_audio_a1a2_wrong_5')
        btn3 = types.InlineKeyboardButton('Go shopping every day', callback_data='shopping_audio_a1a2_wrong_5')
        btn4 = types.InlineKeyboardButton('Compare prices before buying', callback_data='shopping_audio_a1a2_correct_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> What shopping advice does the mother give?",
                      reply_markup=markup, parse_mode='html')

# ==============================================
# Shopping - Audio Tasks (B1-B2)
# ==============================================
def send_audio_task_shopping_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('How to open an online store', callback_data='shopping_audio_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Changes in consumer behaviour', callback_data='shopping_audio_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('History of shopping malls', callback_data='shopping_audio_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('How to become a shop assistant', callback_data='shopping_audio_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/shopping_b1b2.mp3', 'rb'),
                     caption="<b>1/5.</b> Listen and complete the tasks. What is the audio about?",
                     reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('They suggest useful products', callback_data='shopping_audio_b1b2_correct_2')
        btn2 = types.InlineKeyboardButton('They are always more expensive', callback_data='shopping_audio_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('They have better choices', callback_data='shopping_audio_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('They are difficult to use', callback_data='shopping_audio_b1b2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What is good about online stores?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('It helps her buy more things', callback_data='shopping_audio_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('It will help her open her own store', callback_data='shopping_audio_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('It will help her become a shop designer', callback_data='shopping_audio_b1b2_wrong_3')
        btn4 = types.InlineKeyboardButton('It helps her shop more carefully', callback_data='shopping_audio_b1b2_correct_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> Why is the speaker interested in shopping psychology?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("Because it's more popular", callback_data='shopping_audio_b1b2_wrong_4')
        btn2 = types.InlineKeyboardButton('Because new things are boring', callback_data='shopping_audio_b1b2_wrong_4')
        btn3 = types.InlineKeyboardButton("Because it's cheaper and eco-friendly", callback_data='shopping_audio_b1b2_correct_4')
        btn4 = types.InlineKeyboardButton('Because friends recommend it', callback_data='shopping_audio_b1b2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> Why does the speaker like shopping at second-hands?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Virtual try-ons and fast delivery', callback_data='shopping_audio_b1b2_correct_5')
        btn2 = types.InlineKeyboardButton('Cheaper prices only', callback_data='shopping_audio_b1b2_wrong_5')
        btn3 = types.InlineKeyboardButton('More shop assistants', callback_data='shopping_audio_b1b2_wrong_5')
        btn4 = types.InlineKeyboardButton('Bigger shopping carts', callback_data='shopping_audio_b1b2_wrong_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> What new shopping features appeared during the pandemic?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Food - Audio Tasks (A1-A2)
# ==============================================
def send_audio_task_food_a1a2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('How to cook pizza', callback_data='food_audio_a1a2_wrong_1')
        btn2 = types.InlineKeyboardButton('Best restaurants in town', callback_data='food_audio_a1a2_wrong_1')
        btn3 = types.InlineKeyboardButton('Different food preferences', callback_data='food_audio_a1a2_correct_1')
        btn4 = types.InlineKeyboardButton('History of cooking', callback_data='food_audio_a1a2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/food_a1a2.mp3', 'rb'),
                     caption="<b>1/5.</b> Прослушайте аудиозапись и выполните задания. О чем эта запись?",
                     reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Eggs and toast', callback_data='food_audio_a1a2_correct_2')
        btn2 = types.InlineKeyboardButton('Pancakes', callback_data='food_audio_a1a2_wrong_2')
        btn3 = types.InlineKeyboardButton('Sandwich', callback_data='food_audio_a1a2_wrong_2')
        btn4 = types.InlineKeyboardButton('Cereal', callback_data='food_audio_a1a2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What does the speaker usually eat for breakfast?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Pizza with pepperoni', callback_data='food_audio_a1a2_wrong_3')
        btn2 = types.InlineKeyboardButton('Pizza with mushrooms and cheese', callback_data='food_audio_a1a2_correct_3')
        btn3 = types.InlineKeyboardButton('Pizza with vegetables', callback_data='food_audio_a1a2_wrong_3')
        btn4 = types.InlineKeyboardButton('Pizza with seafood', callback_data='food_audio_a1a2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What is the speaker's favorite pizza?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Mother - barbecue, Father - cakes', callback_data='food_audio_a1a2_wrong_4')
        btn2 = types.InlineKeyboardButton('Mother - cakes, Father - barbecue', callback_data='food_audio_a1a2_correct_4')
        btn3 = types.InlineKeyboardButton('Both make good cakes', callback_data='food_audio_a1a2_wrong_4')
        btn4 = types.InlineKeyboardButton('Both make great barbecue', callback_data='food_audio_a1a2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> What do the speaker's parents cook well?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Eat more fast food', callback_data='food_audio_a1a2_wrong_5')
        btn2 = types.InlineKeyboardButton('Eat less at home', callback_data='food_audio_a1a2_wrong_5')
        btn3 = types.InlineKeyboardButton('Eat only meat', callback_data='food_audio_a1a2_wrong_5')
        btn4 = types.InlineKeyboardButton('Eat more fruits and vegetables', callback_data='food_audio_a1a2_correct_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> What does the doctor recommend?",
                      reply_markup=markup, parse_mode='html')


# ==============================================
# Food - Audio Tasks (B1-B2)
# ==============================================
def send_audio_task_food_b1b2(user_id, task_num):
    if task_num == 1:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('How to cook Italian pasta', callback_data='food_audio_b1b2_wrong_1')
        btn2 = types.InlineKeyboardButton('Global food trends and personal experiences', callback_data='food_audio_b1b2_correct_1')
        btn3 = types.InlineKeyboardButton('History of Thai cuisine', callback_data='food_audio_b1b2_wrong_1')
        btn4 = types.InlineKeyboardButton('Best food delivery apps', callback_data='food_audio_b1b2_wrong_1')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_audio(user_id, audio=open('audio/food_b1b2.mp3', 'rb'),
                     caption="<b>1/5.</b> Listen and complete the tasks. What is the audio about?",
                     reply_markup=markup, parse_mode='html')

    elif task_num == 2:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Precise timing', callback_data='food_audio_b1b2_correct_2')
        btn2 = types.InlineKeyboardButton('Using expensive ingredients', callback_data='food_audio_b1b2_wrong_2')
        btn3 = types.InlineKeyboardButton('Special cooking tools', callback_data='food_audio_b1b2_wrong_2')
        btn4 = types.InlineKeyboardButton('Adding lots of spices', callback_data='food_audio_b1b2_wrong_2')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>2/5.</b> What is important when cooking pasta in Italy?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 3:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('Traditional baking', callback_data='food_audio_b1b2_wrong_3')
        btn2 = types.InlineKeyboardButton('Fast food preparation', callback_data='food_audio_b1b2_wrong_3')
        btn3 = types.InlineKeyboardButton('Molecular gastronomy', callback_data='food_audio_b1b2_correct_3')
        btn4 = types.InlineKeyboardButton('Barbecue techniques', callback_data='food_audio_b1b2_wrong_3')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>3/5.</b> What advanced cooking technique has the speaker tried?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 4:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('He purchases imported luxury foods', callback_data='food_audio_b1b2_wrong_4')
        btn2 = types.InlineKeyboardButton('He buys local seasonal produce and reduces waste', callback_data='food_audio_b1b2_correct_4')
        btn3 = types.InlineKeyboardButton('He eats only frozen vegetables', callback_data='food_audio_b1b2_wrong_4')
        btn4 = types.InlineKeyboardButton('He avoids all carbohydrates', callback_data='food_audio_b1b2_wrong_4')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>4/5.</b> How does the speaker practice sustainable eating?",
                      reply_markup=markup, parse_mode='html')

    elif task_num == 5:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton('They make cooking skills unnecessary', callback_data='food_audio_b1b2_wrong_5')
        btn2 = types.InlineKeyboardButton('They only work for young people', callback_data='food_audio_b1b2_wrong_5')
        btn3 = types.InlineKeyboardButton('They are too complicated to use', callback_data='food_audio_b1b2_wrong_5')
        btn4 = types.InlineKeyboardButton("They are helpful but can't replace shared meals", callback_data='food_audio_b1b2_correct_5')
        markup.row(btn1)
        markup.row(btn2)
        markup.row(btn3)
        markup.row(btn4)
        bot.send_message(user_id, "<b>5/5.</b> What is the speaker's view on food technology?",
                      reply_markup=markup, parse_mode='html')




@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # Разбираем callback data
    if '_img_' in call.data:  # Обработка callback от заданий с изображениями
        data = call.data.split('_')
        topic = data[0]
        level = data[2]
        result = data[3]
        task_num = int(data[4]) if len(data) > 4 else None
        total_tasks = 3  # Для изображений 3 задания
    elif '_audio_' in call.data:  # Обработка callback от аудио заданий
        data = call.data.split('_')
        topic = data[0]
        level = data[2]
        result = data[3]
        task_num = int(data[4]) if len(data) > 4 else None
        total_tasks = 5  # Для аудио 5 заданий
    else:  # Обработка callback от текстовых заданий
        data = call.data.split('_')
        topic = data[0]
        level = data[1]
        result = data[2]
        task_num = int(data[3]) if len(data) > 3 else None
        total_tasks = 5  # Для текстовых заданий 5 заданий

    user_id = call.message.chat.id
    user_info = user_data.get(user_id, {})

    # Инициализация счетчика попыток
    if 'attempts' not in user_info:
        user_info['attempts'] = {}
    if task_num not in user_info['attempts']:
        user_info['attempts'][task_num] = 0

    user_info['attempts'][task_num] += 1

    if result == 'correct':
        bot.send_message(user_id, "✅ Верно!")
        user_info["score"] = user_info.get("score", 0) + 1
        user_info["current_task"] = user_info.get("current_task", 1) + 1
    elif result == 'wrong':
        if user_info['attempts'][task_num] >= 2:  # После 2 неудач пропускаем задание
            bot.send_message(user_id, "❌ Неправильно. Переходим к следующему заданию.")
            user_info["current_task"] = user_info.get("current_task", 1) + 1
        else:
            bot.send_message(user_id, "❌ Неправильно. Попробуйте еще раз!")
            send_task(user_id)  # Повтор текущего задания
            return

    # Проверка завершения всех заданий
    if user_info.get("current_task", 1) > total_tasks:
        show_final_results(user_id)
    else:
        send_task(user_id)


def show_final_results(user_id):
    user_info = user_data.get(user_id, {})
    score = user_info.get("score", 0)
    task_type = user_info.get("task_type", "На основе текста")

    # Определяем общее количество заданий в зависимости от типа
    if task_type == "На основе изображения":
        total_tasks = 3
    else:
        total_tasks = 5

    # Формируем сообщение в зависимости от процента правильных ответов
    percentage = (score / total_tasks) * 100

    if percentage == 100:
        message = f"🎉 Поздравляем! Вы выполнили все {total_tasks} заданий правильно!"
    elif percentage >= 70:
        message = f"👍 Хороший результат! Вы правильно выполнили {score} из {total_tasks} заданий."
    elif percentage >= 40:
        message = f"😊 Неплохо! Вы правильно выполнили {score} из {total_tasks} заданий. Есть куда расти!"
    else:
        message = f"😊 Вы правильно выполнили {score} из {total_tasks} заданий. Нужно больше практики!"

    # Добавляем мотивирующее сообщение в зависимости от результата
    if percentage >= 80:
        message += "\n\nОтличная работа! Вы хорошо разбираетесь в этой теме!"
    elif percentage >= 50:
        message += "\n\nПродолжайте в том же духе! С практикой придет совершенство."
    else:
        message += "\n\nНе расстраивайтесь! Каждая ошибка - это возможность научиться чему-то новому."

    bot.send_message(user_id, message)

    # Предлагаем выбрать новую тему или тип заданий
    bot.send_message(user_id, "Хотите попробовать другую тему или тип заданий?", reply_markup=get_topics())



# Запуск бота
bot.polling(none_stop=True)