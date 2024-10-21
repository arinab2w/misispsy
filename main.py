import telebot
import os
import csv
import random
import time
from threading import Timer
from dotenv import load_dotenv

# Хранилище таймеров для отслеживания неактивных пользователей
user_timers = {}

def main():
    load_dotenv()
    bot = telebot.TeleBot(os.getenv('TOKEN'))
    bot.set_webhook()

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
                    writer.writerow([tg_id, '+'])
        except IOError:
            print("[!] Ошибка при открытии файла: " + csv_file)

    def find_companion_from_database(usr):
        csv_file = 'data/users.csv'
        values = []
        try:
            with open(csv_file, 'r', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    value1, value2 = row
                    if value2 == "+":
                        values.append(value1)
        except IOError:
            print("[!] Ошибка при открытии файла: " + csv_file)
        if usr in values:
            values.remove(usr)
        if not values:
            return "Empty"
        return random.choice(values)

    def set_companion(usr1, usr2):
        connections_file = 'data/users.csv'
        try:
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
        except IOError:
            print("[!] Ошибка при открытии файла: " + connections_file)

    def get_companion(usr):
        connections_file = 'data/users.csv'
        try:
            with open(connections_file, 'r', newline='') as f:
                reader = csv.reader(f)
                rows = list(reader)
                for i, row in enumerate(rows):
                    if row[0] == usr:
                        return rows[i][1]
        except IOError:
            print("[!] Ошибка при открытии файла: " + connections_file)

    def pause_user(user_id):
        """Отметить пользователя как приостановленного."""
        set_companion(user_id, 'paused')
        bot.send_message(user_id, "Вы приостановили бота. Для продолжения нажмите /resume")

    def resume_user(user_id):
        """Возобновить поиск собеседника."""
        set_companion(user_id, '+')
        bot.send_message(user_id, "Вы снова доступны для поиска собеседника. Нажмите кнопку 'Найти собеседника'")

    def disconnect_user(user_id):
        """Отключить пользователя за неактивность."""
        old_companion = get_companion(user_id)
        if old_companion and old_companion != "+" and old_companion != 'paused':
            bot.send_message(old_companion, "Ваш собеседник был отключен за неактивность.")
            set_companion(old_companion, '+')
        set_companion(user_id, '+')
        bot.send_message(user_id, "Вы были отключены за неактивность.")

    def reset_timer(user_id):
        """Перезапустить таймер активности пользователя."""
        if user_id in user_timers:
            user_timers[user_id].cancel()
        timer = Timer(600, disconnect_user, [user_id])  # 10 минут
        timer.start()
        user_timers[user_id] = timer

    @bot.message_handler(commands=['start', 'pause', 'resume'])
    def handle_commands(message):
        if message.text == '/start':
            add_companion_to_database(message.from_user.id)
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.row(
                telebot.types.InlineKeyboardButton("Найти собеседника", callback_data="find_companion")
            )
            bot.send_message(message.chat.id, "Привет! Нажмите кнопку \"Найти собеседника\" для начала общения.", reply_markup=keyboard)
            reset_timer(message.from_user.id)

        elif message.text == '/pause':
            pause_user(message.chat.id)

        elif message.text == '/resume':
            resume_user(message.chat.id)
            reset_timer(message.chat.id)

    @bot.message_handler(content_types=['text'])
    def handle_text(message):
        companion = get_companion(str(message.chat.id))
        if companion != '+' and companion != 'paused':
            bot.send_message(int(companion), message.text)
            reset_timer(message.chat.id)
        else:
            bot.send_message(message.chat.id, "На данный момент Вы не состоите в диалоге.")

    # Обработка нажатий на кнопки
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback_query(call):
        if call.data == "find_companion":
            companion = find_companion_from_database(str(call.message.chat.id))
            if companion == "Empty":
                bot.send_message(call.message.chat.id, "К сожалению, свободных собеседников нет.")
            else:
                set_companion(str(call.message.chat.id), companion)
                set_companion(companion, str(call.message.chat.id))
                bot.send_message(call.message.chat.id, "Собеседник найден!")
                bot.send_message(companion, "Собеседник найден!")
                reset_timer(call.message.chat.id)

    bot.infinity_polling()

if __name__ == "__main__":
    main()
