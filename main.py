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
silent_timers = {}  # Таймеры для отслеживания молчания

# Устанавливаем лимит на молчание (10 минут = 600 секунд)
SILENCE_LIMIT = 600
PROHIBITED_WORDS = ["мат1", "мат2", "мат3"]  # Замена на реальные запрещенные слова

# Функция для старта с приветствием
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    
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

# Соединение двух пользователей и установка таймеров молчания
def connect_users(user_id, partner_id, context):
    if user_id not in active_chats and partner_id not in active_chats:
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        context.bot.send_message(chat_id=user_id, text="Найден собеседник!")
        context.bot.send_message(chat_id=partner_id, text="Найден собеседник!")

        # Запускаем таймер молчания для обоих пользователей
        silent_timers[user_id] = context.job_queue.run_once(disconnect_due_to_silence, SILENCE_LIMIT, context={'user_id': user_id, 'partner_id': partner_id})
        silent_timers[partner_id] = context.job_queue.run_once(disconnect_due_to_silence, SILENCE_LIMIT, context={'user_id': partner_id, 'partner_id': user_id})

# Отключение собеседников по таймеру молчания
def disconnect_due_to_silence(context: CallbackContext) -> None:
    user_id = context.job.context['user_id']
    partner_id = context.job.context['partner_id']

    if user_id in active_chats and active_chats[user_id] == partner_id:
        context.bot.send_message(chat_id=user_id, text="Вы отключены за молчание.")
        context.bot.send_message(chat_id=partner_id, text="Ваш собеседник был отключен за молчание.")
        disconnect_users(user_id, partner_id, context)

# Отключение двух пользователей
def disconnect_users(user_id, partner_id, context):
    if user_id in silent_timers:
        silent_timers[user_id].schedule_removal()
        del silent_timers[user_id]
    if partner_id in silent_timers:
        silent_timers[partner_id].schedule_removal()
        del silent_timers[partner_id]
    
    del active_chats[user_id]
    del active_chats[partner_id]

    context.bot.send_message(chat_id=user_id, text="Собеседник отключен. Ищем нового собеседника...")
    context.bot.send_message(chat_id=partner_id, text="Собеседник отключен. Ищем нового собеседника...")

    # Ищем нового собеседника сразу после отключения
    start_search_for_partner(user_id, context)
    start_search_for_partner(partner_id, context)

# Команда /stop для прекращения чата
def stop(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        disconnect_users(user_id, partner_id, context)
    else:
        context.bot.send_message(chat_id=user_id, text="Вы не находитесь в чате.")

# Команда /next для поиска нового собеседника
def next(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        disconnect_users(user_id, partner_id, context)
    context.bot.send_message(chat_id=user_id, text="Ищем нового собеседника...")
    start_search_for_partner(user_id, context)

# Проверка на запрещенные слова
def check_prohibited_words(text):
    return any(re.search(rf'\b{word}\b', text, re.IGNORECASE) for word in PROHIBITED_WORDS)

# Обработка текстовых сообщений с проверкой на нецензурные слова и сброс таймера молчания
def forward_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        message_text = update.message.text
        
        # Проверка на нецензурную лексику
        if check_prohibited_words(message_text):
            banned_users.add(user_id)
            context.bot.send_message(chat_id=user_id, text="Вы забанены за использование нецензурных слов.")
            context.bot.send_message(chat_id=partner_id, text="Ваш собеседник был отключен за нарушение правил.")
            disconnect_users(user_id, partner_id, context)
        else:
            # Пересылаем сообщение и сбрасываем таймер молчания
            context.bot.send_message(chat_id=partner_id, text=message_text)
            reset_silence_timer(user_id, partner_id, context)

# Сброс таймера молчания при активности пользователя
def reset_silence_timer(user_id, partner_id, context):
    if user_id in silent_timers:
        silent_timers[user_id].schedule_removal()
    if partner_id in silent_timers:
        silent_timers[partner_id].schedule_removal()

    silent_timers[user_id] = context.job_queue.run_once(disconnect_due_to_silence, SILENCE_LIMIT, context={'user_id': user_id, 'partner_id': partner_id})
    silent_timers[partner_id] = context.job_queue.run_once(disconnect_due_to_silence, SILENCE_LIMIT, context={'user_id': partner_id, 'partner_id': user_id})

# Основная функция для запуска бота
def main() -> None:
    load_dotenv()

    updater = Updater(os.getenv('TOKEN'), use_context=True)
    dispatcher = updater.dispatcher

    # Команды
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("stop", stop))
    dispatcher.add_handler(CommandHandler("next", next))

    # Обработка текстовых сообщений
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, forward_message))

    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
