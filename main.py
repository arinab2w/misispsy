import sqlite3
import os
import tempfile
import time
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from flask import Flask, request
from const import API_TOKEN  # Импортируем токен из const.py

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Подключение к базе данных SQLite (вместо работы с CSV)
conn = sqlite3.connect('users.db', check_same_thread=False)  # check_same_thread=False для работы с многопоточностью
cursor = conn.cursor()

# Создание таблицы пользователей (если она ещё не создана)
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (user_id INTEGER PRIMARY KEY, name TEXT, stage TEXT)''')
conn.commit()

# Кэш для хранения часто запрашиваемых данных
user_cache = {}

# Функция для добавления нового пользователя в базу данных
def add_user(user_id, name):
    cursor.execute('INSERT INTO users (user_id, name, stage) VALUES (?, ?, ?)', (user_id, name, ''))
    conn.commit()

# Функция для поиска пользователя в базе данных (с кэшированием)
def find_user(user_id):
    if user_id in user_cache:
        return user_cache[user_id]
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if user:
        user_cache[user_id] = user  # Кэшируем данные пользователя
    return user

# Функция очистки временной папки от старых файлов
def clean_temp_directory(directory='temp/', max_age=86400):  # Удаление файлов старше 1 дня
    now = time.time()
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.stat(file_path).st_mtime < now - max_age:
            os.remove(file_path)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    if not find_user(user_id):  # Если пользователь не найден, добавляем
        add_user(user_id, name)
        await message.reply(f"Привет, {name}! Ты добавлен в базу данных.")
    else:
        await message.reply(f"Привет снова, {name}!")

# Обработка голосового сообщения (пример использования временных файлов)
@dp.message_handler(content_types=['voice'])
async def handle_voice(message: types.Message):
    file_info = await bot.get_file(message.voice.file_id)
    file_path = file_info.file_path

    # Создание временного файла для сохранения голосового сообщения
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    downloaded_file = await bot.download_file(file_path)
    temp_file.write(downloaded_file.read())
    temp_file_path = temp_file.name
    temp_file.close()

    # Тут можно добавить обработку голосового файла

    # Удаление временного файла после использования
    os.remove(temp_file_path)

    await message.reply("Ваше голосовое сообщение обработано.")

# Обработчик фото (пример аналогичен голосовому)
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    photo_info = message.photo[-1]  # Берём фото наивысшего качества
    file_info = await bot.get_file(photo_info.file_id)
    file_path = file_info.file_path

    # Создание временного файла для сохранения фото
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    downloaded_file = await bot.download_file(file_path)
    temp_file.write(downloaded_file.read())
    temp_file_path = temp_file.name
    temp_file.close()

    # Тут можно добавить обработку изображения

    # Удаление временного файла после использования
    os.remove(temp_file_path)

    await message.reply("Ваше фото обработано.")

# Установка webhook (вместо long polling)
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
async def webhook():
    update = types.Update.de_json(request.stream.read().decode("utf-8"))
    await bot.process_new_updates([update])  # Убедитесь, что эта строка ожидается
    return "OK", 200

# Настройка webhook при запуске
async def on_startup(dp):
    await bot.set_webhook('https://yourdomain.com/webhook')  # Замените на ваш домен

# Очистка временной папки каждый раз при старте
clean_temp_directory()

if __name__ == '__main__':
    # Запуск Flask сервера и Telegram бота
    executor.start_polling(dp, skip_updates=True)  # Используйте polling вместо webhook, если тестируете локально
