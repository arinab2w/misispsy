import telebot
import os
import csv
import random
import const
import threading
import time

bot = telebot.TeleBot(const.TOKEN)
bot.set_webhook()

# Хранение времени последней активности пользователя
user_activity = {}

# Максимальное время неактивности в секундах (10 минут = 600 секунд)
INACTIVITY_TIMEOUT = 600

# Флаг для остановки бота
stop_bot = False

# Добавляем пользователя в базу
def add_companion_to_database(tg_id):
    csv_file = 'data/users.csv'
    exists = False
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                break
            if row[0] == str(tg_id):
                exists = True
                break
    if not exists:
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([tg_id, '+'])

# Поиск свободного собеседника
def find_companion_from_database(usr):
    csv_file = 'data/users.csv'
    values = []
    with open(csv_file, 'r', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            value1, value2 = row
            if value2 == "+":
                values.append(value1)
    if usr in values:
        values.remove(usr)
    if not values:
        return "Empty"
    return random.choice(values)

# Установка собеседника
def set_companion(usr1, usr2):
    connections_file = 'data/users.csv'
    with open(connections_file, 'r', newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)
        for i, row in enumerate(rows):
            if row[0] == usr1:
                rows[i][1] = usr2
                break
    with open(connections_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

# Получение текущего собеседника
def get_companion(usr):
    connections_file = 'data/users.csv'
    with open(connections_file, 'r', newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)
        for i, row in enumerate(rows):
            if row[0] == usr:
                return rows[i][1]

# Функция для завершения общения по истечении времени
def check_inactivity():
    while not stop_bot:
        current_time = time.time()
        for user_id, last_active in list(user_activity.items()):
            if current_time - last_active > INACTIVITY_TIMEOUT:
                bot.send_message(user_id, "Вы были отключены за неактивность.")
                set_companion(user_id, '+')
                del user_activity[user_id]
        time.sleep(10)

# Обработка текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    global stop_bot
    if message.text == '/start':
        handle_start(message)
    elif message.text == '/change':
        handle_change(message)
    elif message.text == '/stop':
        bot.send_message(message.chat.id, "Бот отключается. Спасибо за использование!")
        stop_bot = True
        bot.stop_polling()  # Остановка поллинга
    else:
        update_user_activity(message.chat.id)
        if get_companion(str(message.chat.id)) != '+':
            msg = message.text
            companion = get_companion(str(message.chat.id))
            bot.send_message(int(companion), msg)
        else:
            bot.send_message(message.chat.id, "На данный момент Вы не состоите в диалоге")

# Функция обновления активности пользователя
def update_user_activity(user_id):
    user_activity[user_id] = time.time()

# Обработка команды /start
def handle_start(message):
    add_companion_to_database(message.from_user.id)
    name = message.from_user.first_name
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton("Найти собеседника", callback_data="find_companion")
    )
    bot.send_message(message.chat.id, f"Привет, {name}!\n\nНажмите кнопку \"Найти собеседника\" для того, чтобы начать общение!", reply_markup=keyboard)
    update_user_activity(message.from_user.id)

# Обработка команды /change
def handle_change(message):
    old = get_companion(str(message.chat.id))
    if old != '+':
        bot.send_message(int(old), "С Вами больше не общаются. Вы можете найти нового собеседника, введя команду /change")
    companion = find_companion_from_database(str(message.chat.id))
    set_companion(old, '+')
    if companion == "Empty":
        bot.send_message(message.chat.id, "К сожалению, свободных собеседников нет")
        set_companion(str(message.chat.id), '+')
    else:
        set_companion(str(message.chat.id), companion)
        set_companion(companion, str(message.chat.id))
        bot.send_message(message.chat.id, "Собеседник найден!\n\nНапишите сообщение.")
        bot.send_message(companion, "Собеседник найден!\n\nНапишите сообщение.")
    update_user_activity(message.chat.id)

# Запуск функции проверки неактивности пользователей в отдельном потоке
inactivity_thread = threading.Thread(target=check_inactivity)
inactivity_thread.start()

# Запуск бота
bot.infinity_polling()
