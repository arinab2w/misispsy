import logging
from telegram import Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, CallbackContext)
import random
from dotenv import load_dotenv
import os
import re

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Списки для ожидания и активных чатов
waiting_users = []
active_chats = {}
banned_users = set()  # Бан-лист
stopped_users = set()  # Пользователи, отключившиеся через /stop

PROHIBITED_WORDS = ["мат1", "мат2", "мат3", "бля", "блядь", "сука", "пиздец"]  # Список запрещенных слов

# Функция для старта с приветствием
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id

    # Если пользователь ранее отправил /stop, удаляем его из списка stopped_users
    if user_id in stopped_users:
        stopped_users.remove(user_id)
    
    # Приветственное сообщение
    welcome_message = ("Здравствуй, дорогой пользователь! Данный чат-бот предназначен для анонимной переписки между студентами "
                       "университета МИСиС. Здесь ты можешь чувствовать себя комфортно, не бояться быть открытым и делиться своими "
                       "переживаниями. Убедительная просьба быть вежливыми друг к другу!")
    context.bot.send_message(chat_id=user_id, text=welcome_message)
    
    if user_id in active_chats:
        context.bot.send_message(chat_id=user_id, text="Вы уже общаетесь с собеседником.")
    else:
        context.bot.send_message(chat_id=user_id, text="Ищем собеседника...")
        start_search_for_partner(user_id, context)

# Функция поиска собеседника
def start_search_for_partner(user_id, context):
    if user_id in banned_users:
        context.bot.send_message(chat_id=user_id, text="Вы забанены за использование нецензурных слов.")
        return
    if waiting_users and waiting_users[0] != user_id:
        partner_id = waiting_users.pop(0)
        connect_users(user_id, partner_id, context)
    else:
        waiting_users.append(user_id)

# Соединение двух пользователей
def connect_users(user_id, partner_id, context):
    if user_id not in active_chats and partner_id not in active_chats:
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        context.bot.send_message(chat_id=user_id, text="Найден собеседник!")
        context.bot.send_message(chat_id=partner_id, text="Найден собеседник!")

# Отключение двух пользователей
def disconnect_users(user_id, partner_id, context):
    # Убираем пользователей из активных чатов
    if user_id in active_chats:
        del active_chats[user_id]
    if partner_id in active_chats:
        del active_chats[partner_id]

# Команда /stop для остановки бота
def stop(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    stopped_users.add(user_id)
    
    # Если пользователь находится в чате, отключаем его
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        disconnect_users(user_id, partner_id, context)
        context.bot.send_message(chat_id=partner_id, text="Ваш собеседник покинул чат.")

    context.bot.send_message(chat_id=user_id, text="Вы успешно остановили бота. Чтобы возобновить общение, введите команду /start.")

# Команда /next для поиска нового собеседника
def next(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in stopped_users:
        context.bot.send_message(chat_id=user_id, text="Вы остановили бота. Введите команду /start, чтобы возобновить общение.")
        return
    
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        disconnect_users(user_id, partner_id, context)
        context.bot.send_message(chat_id=user_id, text="Ищем нового собеседника...")
        start_search_for_partner(user_id, context)
    else:
        start_search_for_partner(user_id, context)

# Проверка на запрещенные слова
def check_prohibited_words(text):
    return any(re.search(rf'\b{word}\b', text, re.IGNORECASE) for word in PROHIBITED_WORDS)

# Обработка текстовых сообщений, изображений и стикеров с проверкой на нецензурные слова
def forward_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    
    # Если пользователь отключен, не обрабатываем сообщения
    if user_id in stopped_users:
        return
    
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        
        # Проверка текста сообщения на нецензурные слова
        message_text = update.message.text
        if message_text and check_prohibited_words(message_text):
            banned_users.add(user_id)
            context.bot.send_message(chat_id=user_id, text="Вы забанены за использование нецензурных слов.")
            context.bot.send_message(chat_id=partner_id, text="Ваш собеседник был отключен за нарушение правил.")
            disconnect_users(user_id, partner_id, context)
        else:
            # Пересылка текста
            if message_text:
                context.bot.send_message(chat_id=partner_id, text=message_text)
            
            # Пересылка фото
            if update.message.photo:
                photo_file = update.message.photo[-1].file_id
                context.bot.send_photo(chat_id=partner_id, photo=photo_file)
            
            # Пересылка стикеров
            if update.message.sticker:
                sticker_file = update.message.sticker.file_id
                context.bot.send_sticker(chat_id=partner_id, sticker=sticker_file)

# Основная функция для запуска бота
def main() -> None:
    load_dotenv()

    updater = Updater(os.getenv('TOKEN'), use_context=True)
    dispatcher = updater.dispatcher

    # Команды
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("stop", stop))
    dispatcher.add_handler(CommandHandler("next", next))

    # Обработка текстовых сообщений, фото и стикеров
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, forward_message))
    dispatcher.add_handler(MessageHandler(Filters.photo, forward_message))
    dispatcher.add_handler(MessageHandler(Filters.sticker, forward_message))  # Новый фильтр для стикеров

    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
