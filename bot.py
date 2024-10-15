# -*- coding: utf-8 -*-
"""
Created on Tue Oct 15 11:20:50 2024

@author: PC1
"""

import telebot
import os
import csv
import random
from dotenv import load_dotenv

def main():
    load_dotenv()

    # Создание объекта бота с использованием токена из переменных окружения
    bot = telebot.TeleBot(os.getenv('TOKEN'))

    # Проверка наличия необходимых директорий и файлов для хранения данных
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.isfile('data/users.csv'):
        with open('data/users.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['user_id', 'companion'])  # Заголовки CSV файла

    # Функция добавления нового пользователя в базу данных
    def add_companion_to_database(tg_id):
        csv_file = 'data/users.csv'
        exists = False
        try:
            with open(csv_file, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:  # Проверка на пустую строку
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

    # Функция поиска свободного собеседника
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

    # Функция для связывания двух пользователей
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

    # Функция для получения собеседника для пользователя
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

    # Обработчик сообщений
    @bot.message_handler(content_types=['text'])
    def handle_text(message):
        if message.text == '/start':
            handle_start(message)
        elif message.text == '/change':
            handle_change(message)
        else:
            companion = get_companion(str(message.chat.id))
            if companion == '+' or companion is None:
                bot.send_message(message.chat.id, "На данный момент Вы не состоите в диалоге")
            else:
                bot.send_message(int(companion), message.text)

    # Обработчики для различных типов медиа (фото, видео, голосовые сообщения, стикеры)
    
    # Обработка фото
    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        if message.photo:
            companion = get_companion(str(message.chat.id))
            file_info = bot.get_file(message.photo[len(message.photo) - 1].file_id)
            user_id = message.from_user.username
            downloaded_file = bot.download_file(file_info.file_path)
            src = 'temp/photos/' + user_id + '.jpg'
            try:
                with open(src, 'wb') as new_file:
                    new_file.write(downloaded_file)
            except IOError:
                print("[!] Ошибка при открытии файла: "+src)
            bot.send_photo(int(companion), photo=open(src, "rb"))
            os.remove(src)

    # Обработка видео
    @bot.message_handler(content_types=['video'])
    def handle_video(message):
        if message.video:
            companion = get_companion(str(message.chat.id))
            file_info = bot.get_file(message.video.file_id)
            user_id = message.from_user.username
            downloaded_file = bot.download_file(file_info.file_path)
            src = 'temp/videos/' + user_id + '.mp4'
            try:
                with open(src, 'wb') as new_file:
                    new_file.write(downloaded_file)
            except IOError:
                print("[!] Ошибка при открытии файла: "+src)
            bot.send_video(int(companion), video=open(src, "rb"))
            os.remove(src)

    # Обработка голосовых сообщений
    @bot.message_handler(content_types=['voice'])
    def handle_voice(message):
        if message.voice:
            companion = get_companion(str(message.chat.id))
            file_info = bot.get_file(message.voice.file_id)
            user_id = message.from_user.username
            downloaded_file = bot.download_file(file_info.file_path)
            src = 'temp/audio/' + user_id + '.ogg'
            try:
                with open(src, 'wb') as new_file:
                    new_file.write(downloaded_file)
            except IOError:
                print("[!] Ошибка при открытии файла: "+src)
            bot.send_voice(int(companion), voice=open(src, "rb"))
            os.remove(src)

    # Обработка стикеров
    @bot.message_handler(content_types=['sticker'])
    def handle_sticker(message):
        if message.sticker:
            companion = get_companion(str(message.chat.id))
            file_info = bot.get_file(message.sticker.file_id)
            user_id = message.from_user.username
            downloaded_file = bot.download_file(file_info.file_path)
            src = 'temp/stickers/' + user_id + '.webp'
            try:
                with open(src, 'wb') as new_file:
                    new_file.write(downloaded_file)
            except IOError:
                print("[!] Ошибка при открытии файла: "+src)
            bot.send_sticker(int(companion), sticker=open(src, "rb"))
            os.remove(src)

    # Обработчик команды /start
    def handle_start(message):
        add_companion_to_database(message.from_user.id)
        name = message.from_user.first_name
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.row(
            telebot.types.InlineKeyboardButton("Найти собеседника", callback_data="find_companion")
        )
        bot.send_message(message.chat.id, "Привет, "+name+"!\n\nС помощью этого бота ты сможешь связаться с любым человеком абсолютно анонимно!\n\nНажмите кнопку \"Найти собеседника\" для того, чтобы начать общение!", reply_markup=keyboard)

    # Обработчик команды /change
    def handle_change(message):
        old = get_companion(str(message.chat.id))
        bot.send_message(int(old), "С Вами больше не общаются. Вы можете найти нового собеседника, введя команду /change")
        companion = find_companion_from_database(str(message.chat.id))
        set_companion(old, '+')
        if companion == "Empty":
            bot.send_message(message.chat.id, "К сожалению, свободных собеседников нет")
            set_companion(str(message.chat.id), '+')
        else:
            set_companion(str(message.chat.id), companion)
            set_companion(companion, str(message.chat.id))
            bot.send_message(message.chat.id, "Собеседник найден!\n\nНапишите сообщение, и оно отправится ему! Если Вы решите сменить собеседника, введите команду /change")
            bot.send_message(companion, "Собеседник найден!\n\nНапишите сообщение, и оно отправится ему! Если Вы решите сменить собеседника, введите команду /change")

    # Обработчик callback для кнопок inline
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback_query(call):
        if call.data == "find_companion":
            companion = find_companion_from_database(str(call.message.chat.id))
            if companion == "Empty":
                bot.send_message(call.message.chat.id, "К сожалению, свободных собеседников нет")
            else:
                set_companion(str(call.message.chat.id), companion)
                set_companion(companion, str(call.message.chat.id))
                bot.send_message(call.message.chat.id, "Собеседник найден!\n\nНапишите сообщение, и оно отправится ему! Если Вы решите сменить собеседника, введите команду /change")
                bot.send_message(companion, "Собеседник найден!\n\nНапишите сообщение, и оно отправится ему! Если Вы решите сменить собеседника, введите команду /change")

    # Запуск бота с обработкой ошибок
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main()
