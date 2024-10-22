import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from const import TOKEN  # Импорт токена из const.py

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Списки для пользователей
users_waiting = []
active_chats = {}
user_ids = {}

# Максимальное время ожидания
SEARCH_TIMEOUT = 300  # 5 минут
IDLE_TIMEOUT = 300    # 5 минут бездействия

# Генерация уникальных номеров пользователей
user_counter = 0

async def connect_users():
    while True:
        if len(users_waiting) >= 2:
            user1 = users_waiting.pop(0)
            user2 = users_waiting.pop(0)
            
            active_chats[user1] = user2
            active_chats[user2] = user1
            
            await bot.send_message(user1, "Вы подключены к собеседнику!")
            await bot.send_message(user2, "Вы подключены к собеседнику!")
        await asyncio.sleep(1)

# Команда /start для начала работы
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    global user_counter
    user_id = message.from_user.id

    # Присваивание уникального номера пользователю
    if user_id not in user_ids:
        user_counter += 1
        user_ids[user_id] = f'user{user_counter}'

    if user_id in active_chats:
        await message.reply("Вы уже в чате с собеседником. Напишите /next для поиска нового.")
    elif user_id not in users_waiting:
        users_waiting.append(user_id)
        await message.reply("Ищем вам собеседника...")
        await search_for_partner(user_id)

# Команда /next для смены собеседника
@dp.message_handler(commands=['next'])
async def next_command(message: types.Message):
    user_id = message.from_user.id

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await bot.send_message(partner_id, "Собеседник отключился.")
        await disconnect(user_id)

    await start_command(message)

# Команда /stop для отключения
@dp.message_handler(commands=['stop'])
async def stop_command(message: types.Message):
    user_id = message.from_user.id

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await bot.send_message(partner_id, "Собеседник отключился.")
        await disconnect(user_id)
    else:
        if user_id in users_waiting:
            users_waiting.remove(user_id)
        await message.reply("Вы отключились от поиска.")

# Поиск собеседника
async def search_for_partner(user_id):
    for _ in range(SEARCH_TIMEOUT):
        if user_id in active_chats:
            return
        if user_id not in users_waiting:
            return
        await asyncio.sleep(1)
    
    if user_id in users_waiting:
        users_waiting.remove(user_id)
        await bot.send_message(user_id, "Собеседник пока не найден, попробуйте позже.")

# Функция отключения
async def disconnect(user_id):
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        if partner_id in active_chats:
            active_chats.pop(partner_id)

    if user_id in users_waiting:
        users_waiting.remove(user_id)

    await bot.send_message(user_id, "Вы отключены.")

# Таймауты при бездействии
async def idle_timeout_check():
    while True:
        for user_id, partner_id in list(active_chats.items()):
            try:
                await bot.send_chat_action(user_id, "typing")
            except:
                await disconnect(user_id)
                await bot.send_message(partner_id, "Собеседник отключился.")
        await asyncio.sleep(IDLE_TIMEOUT)

# Обработка текстовых сообщений
@dp.message_handler(content_types=types.ContentType.ANY)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        try:
            # Пересылаем все виды контента от одного пользователя к другому
            if message.content_type == 'text':
                await bot.send_message(partner_id, message.text)
            else:
                await message.copy_to(partner_id)
        except:
            await disconnect(user_id)
            await bot.send_message(user_id, "Ошибка отправки сообщения. Собеседник отключен.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(connect_users())
    loop.create_task(idle_timeout_check())
    executor.start_polling(dp, skip_updates=True)
