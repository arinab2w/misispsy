import telebot
import os
import csv
import random
import threading
import time
from dotenv import load_dotenv

# Хранение времени последней активности пользователей
last_active_time = {}

def main():
    load_dotenv()
    bot = telebot.TeleBot(os.getenv('TOKEN'))
    
    # Функция для проверки неактивных пользователей каждые 10 минут
    def check_inactivity():
        while True:
            current_time = time.time()
            for tg_id, last_time in list(last_active_time.items()):
                if current_time - last_time > 600:  # 600 секунд = 10 минут
                    update_status(tg_id, "inactive")
                    last_active_time.pop(tg_id)
                    bot.send_message(tg_id, "Вы были исключены из чата за неактивность.")
            time.sleep(60)  # Проверяем раз в минуту

    # Запуск проверки неактивных пользователей в отдельном потоке
    threading.Thread(target=check_inactivity, daemon=True).start()

    def add_companion_to_database(tg_id):
        csv_file = 'data/users.csv'
        exists = False
        try:
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
                    writer.writerow([tg_id, '+', 'active'])  # Добавим статус 'active' по умолчанию
        except IOError:
            print("[!] Ошибка при открытии файла: " + csv_file)

    def find_companion_from_database(usr):
        csv_file = 'data/users.csv'
        values = []
        try:
            with open(csv_file, 'r', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    value1, value2, status = row  # Учтем третий столбец (статус)
                    if value2 == "+" and status == "active":  # Ищем только активных пользователей
                        values.append(value1)
        except IOError:
            print("[!] Ошибка при открытии файла: " + csv_file)
        if usr in values:
            values.remove(usr)
        if not values:
            return "Empty"
        return random.choice(values)

    def update_status(tg_id, status):
        csv_file = 'data/users.csv'
        try:
            with open(csv_file, 'r', newline='') as f:
                reader = csv.reader(f)
                rows = list(reader)
                for i, row in enumerate(rows):
                    if row[0] == str(tg_id):
                        rows[i][2] = status  # Обновляем статус пользователя
                        break

            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
        except IOError:
            print("[!] Ошибка при открытии файла: " + csv_file)

    @bot.message_handler(commands=['start'])
    def handle_start(message):
        add_companion_to_database(message.from_user.id)
        name = message.from_user.first_name
        last_active_time[message.from_user.id] = time.time()  # Сохраняем время активности
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.row(
            telebot.types.InlineKeyboardButton("Найти собеседника", callback_data="find_companion")
        )
        bot.send_message(message.chat.id, "Привет, " + name + "!\n\nНажмите кнопку \"Найти собеседника\", чтобы начать общение.", reply_markup=keyboard)

    @bot.message_handler(commands=['pause'])
    def handle_pause(message):
        update_status(message.from_user.id, "paused")
        bot.send_message(message.chat.id, "Вы приостановили поиск собеседников.")

    @bot.message_handler(commands=['resume'])
    def handle_resume(message):
        update_status(message.from_user.id, "active")
        last_active_time[message.from_user.id] = time.time()  # Обновляем время активности
        bot.send_message(message.chat.id, "Поиск собеседников возобновлен.")

    @bot.message_handler(commands=['change'])
    def handle_change(message):
        old = get_companion(str(message.chat.id))
        if old != '+':
            bot.send_message(int(old), "С Вами больше не общаются.")
            set_companion(old, '+')
        
        companion = find_companion_from_database(str(message.chat.id))
        if companion == "Empty":
            bot.send_message(message.chat.id, "Свободных собеседников нет.")
            set_companion(str(message.chat.id), '+')
        else:
            set_companion(str(message.chat.id), companion)
            set_companion(companion, str(message.chat.id))
            bot.send_message(message.chat.id, "Собеседник найден!")
            bot.send_message(companion, "Собеседник найден!")
        last_active_time[message.from_user.id] = time.time()  # Обновляем время активности

    @bot.callback_query_handler(func=lambda call: call.data == "find_companion")
    def handle_find_companion(call):
        companion = find_companion_from_database(str(call.message.chat.id))
        if companion == "Empty":
            bot.send_message(call.message.chat.id, "Свободных собеседников нет.")
        else:
            set_companion(str(call.message.chat.id), companion)
            set_companion(companion, str(call.message.chat.id))
            bot.send_message(call.message.chat.id, "Собеседник найден!")
            bot.send_message(companion, "Собеседник найден!")
        last_active_time[call.message.chat.id] = time.time()  # Обновляем время активности

    # Обрабатываем любые сообщения и обновляем время последней активности
    @bot.message_handler(func=lambda message: True)
    def handle_all_messages(message):
        last_active_time[message.from_user.id] = time.time()  # Обновляем время активности

    bot.infinity_polling()

if __name__ == "__main__":
    main()
