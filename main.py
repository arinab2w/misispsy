import logging
from telegram import Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, CallbackContext)
from telegram.error import BadRequest
from const import TOKEN
import random
from apscheduler.schedulers.background import BackgroundScheduler

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Списки для ожидания и активных чатов
waiting_users = []
active_chats = {}

# Устанавливаем лимит на ожидание собеседника и беседу без активности (10 минут = 600 секунд)
TIME_LIMIT = 600

# Функция для старта поиска собеседника
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    
    if user_id in active_chats:
        context.bot.send_message(chat_id=user_id, text="Вы уже общаетесь с собеседником.")
    else:
        context.bot.send_message(chat_id=user_id, text="Ищем собеседника...")
        start_search_for_partner(user_id, context)

# Функция поиска собеседника
def start_search_for_partner(user_id, context):
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

        # Сбрасываем таймеры через 10 минут
        context.job_queue.run_once(disconnect_due_to_timeout, TIME_LIMIT, context={'user_id': user_id, 'partner_id': partner_id})
    else:
        context.bot.send_message(chat_id=user_id, text="Ошибка соединения. Повторите попытку.")

# Отключение собеседников по таймеру
def disconnect_due_to_timeout(context: CallbackContext) -> None:
    user_id = context.job.context['user_id']
    partner_id = context.job.context['partner_id']

    if user_id in active_chats and active_chats[user_id] == partner_id:
        disconnect_users(user_id, partner_id, context)

# Отключение двух пользователей
def disconnect_users(user_id, partner_id, context):
    del active_chats[user_id]
    del active_chats[partner_id]

    context.bot.send_message(chat_id=user_id, text="Собеседник отключен.")
    context.bot.send_message(chat_id=partner_id, text="Собеседник отключен.")

    waiting_users.append(user_id)
    waiting_users.append(partner_id)

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

# Обработка входящих сообщений и пересылка их собеседнику
def forward_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        context.bot.forward_message(chat_id=partner_id, from_chat_id=user_id, message_id=update.message.message_id)

# Отправка фото после отключения
def send_photo_to_user(context, user_id, photo_path):
    message = context.bot.send_photo(chat_id=user_id, photo=open(photo_path, 'rb'))
    message_id = message.message_id
    context.job_queue.run_once(delete_photo, 10, context={'chat_id': user_id, 'message_id': message_id})

def delete_photo(context: CallbackContext) -> None:
    chat_id = context.job.context.get('chat_id')
    message_id = context.job.context.get('message_id')
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except BadRequest as e:
        logger.warning(f"Ошибка при удалении фото: {e}")

# Отключение собеседника с отправкой фото
def end_chat_and_send_photo(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        
        send_photo_to_user(context, partner_id, 'телега.jpg')

        disconnect_users(user_id, partner_id, context)

        context.bot.send_message(chat_id=user_id, text="Собеседник завершил беседу, ищем нового собеседника.")
        context.bot.send_message(chat_id=partner_id, text="Ваш собеседник завершил беседу.")

        waiting_users.append(user_id)
        waiting_users.append(partner_id)

# Основная функция для запуска бота
def main() -> None:
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Команды
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("stop", stop))
    dispatcher.add_handler(CommandHandler("next", next))

    # Обработка сообщений
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, forward_message))
    dispatcher.add_handler(MessageHandler(Filters.photo | Filters.video | Filters.sticker | Filters.voice, forward_message))

    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
