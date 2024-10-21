import telebot
import os
import csv
import random
import time
from threading import Thread
from dotenv import load_dotenv

def main():
    load_dotenv()
    token = os.getenv('TOKEN')
    bot = telebot.TeleBot(token)
    
    active_users = {}
    paused_users = set()

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

    @bot.message_handler(content_types=['text'])
    def handle_text(message):
        if message.text == '/start':
            handle_start(message)
        elif message.text == '/pause':
            handle_pause(message)
        elif message.text == '/resume':
            handle_resume(message)
        elif message.text == '/change':
            handle_change(message)
        else:
            if get_companion(str(message.chat.id)) != '+':
                msg = message.text
                companion = get_companion(str(message.chat.id))
                bot.send_message(int(companion), msg)
                print("[#] Успешная отправка сообщения")
                # Update the last active time for this user
                active_users[message.chat.id] = time.time()
            else:
                bot.send_message(message.chat.id, "На данный момент Вы не состоите в диалоге")
                print("[#] Пользователь пытался отправить сообщение, не состоя в диалоге")

    def handle_pause(message):
        paused_users.add(message.chat.id)
        bot.send_message(message.chat.id, "Вы приостановили бота. Вы можете продолжить в любой момент, используя команду /resume.")

    def handle_resume(message):
        paused_users.discard(message.chat.id)
        bot.send_message(message.chat.id, "Вы возобновили работу бота. Вы можете снова искать собеседника.")

    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        if message.photo:
            companion = get_companion(str(message.chat.id))
            if companion not in paused_users:
                file_info = bot.get_file(message.photo[len(message.photo) - 1].file_id)
                user_id = message.from_user.username
                downloaded_file = bot.download_file(file_info.file_path)
                src = 'temp/photos/' + user_id + '.jpg'
                try:
                    with open(src, 'wb') as new_file:
                        new_file.write(downloaded_file)
                except IOError:
                    print("[!] Ошибка при открытии файла: " + src)
                bot.send_photo(int(companion), photo=open(src, "rb"))
                os.remove(src)

    # Implement similar handlers for video, voice, sticker, etc. 

    def handle_start(message):
        add_companion_to_database(message.from_user.id)
        name = message.from_user.first_name
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.row(
            telebot.types.InlineKeyboardButton("Найти собеседника", callback_data="find_companion")
        )
        bot.send_message(message.chat.id, "Привет, " + name + "!\n\nС помощью этого бота ты сможешь связаться с любым человеком абсолютно анонимно!\n\nНажмите кнопку \"Найти собеседника\" для того, чтобы начать общение!", reply_markup=keyboard)

    def handle_change(message):
        old = get_companion(str(message.chat.id))
        bot.send_message(int(old), "С Вами больше не общаются. Вы можете найти нового собеседника, введя команду /change")
        companion = find_companion_from_database(str(message.chat.id))
        set_companion(old, '+')
        if companion == "Empty":
            bot.send_message(message.chat.id, "К сожалению, свободных собеседников нет")
            set_companion(str(message.chat.id), '+')
            print("Пользователь ID:" + str(message.chat.id) + " не нашел собеседника [свободных нет]")
        else:
            set_companion(str(message.chat.id), companion)
            set_companion(companion, str(message.chat.id))
            bot.send_message(message.chat.id, "Собеседник найден!\n\nНапишите сообщение, и оно отправится ему! Если Вы решите сменить собеседника, введите команду /change")
            bot.send_message(companion, "Собеседник найден!\n\nНапишите сообщение, и оно отправится ему! Если Вы решите сменить собеседника, введите команду /change")
            print("Пользователь ID:" + str(message.chat.id) + " нашел собеседника ID:" + str(companion))

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback_query(call):
        if call.data == "find_companion":
            if call.message.chat.id in paused_users:
                bot.send_message(call.message.chat.id, "Вы приостановили бота. Сначала возобновите работу, используя команду /resume.")
                return
            companion = find_companion_from_database(str(call.message.chat.id))
            if companion == "Empty":
                bot.send_message(call.message.chat.id, "К сожалению, свободных собеседников нет")
                print("Пользователь ID:" + str(call.message.chat.id) + " не нашел собеседника [свободных нет]")
            else:
                set_companion(str(call.message.chat.id), companion)
                set_companion(companion, str(call.message.chat.id))
                bot.send_message(call.message.chat.id, "Собеседник найден!\n\nНапишите сообщение, и оно отправится ему! Если Вы решите сменить собеседника, введите команду /change")
                bot.send_message(companion, "Собеседник найден!\n\nНапишите сообщение, и оно отправится ему! Если Вы решите сменить собеседника, введите команду /change")
                print("Пользователь ID:" + str(call.message.chat.id) + " нашел собеседника ID:" + str(companion))

    def remove_inactive_users():
        while True:
            time.sleep(60)  # Check every minute
            current_time = time.time()
            for user_id in list(active_users.keys()):
                if current_time - active_users[user_id] > 600:  # 10 minutes
                    # Remove user from active_users and set companion to '+'
                    set_companion(str(user_id), '+')
                    del active_users[user_id]
                    print(f"[#] Пользователь ID:{user_id} был отключен из-за неактивности.")

    # Start the background thread for removing inactive users
    thread = Thread(target=remove_inactive_users)
    thread.daemon = True
    thread.start()

    bot.infinity_polling()

if __name__ == "__main__":
    main()
