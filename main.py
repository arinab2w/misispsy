import logging
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from const import TOKEN
import random
import time
from threading import Timer

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранение состояния пользователей
waiting_users = []
connected_users = {}

# Таймеры для отключения пользователей по тайм-ауту
timers = {}

# Время ожидания в секундах
MAX_WAIT_TIME = 600  # 10 минут
MAX_INACTIVITY_TIME = 600  # 10 минут молчания

def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id in connected_users:
        update.message.reply_text("Вы уже подключены к собеседнику. Введите /stop для отключения.")
    else:
        update.message.reply_text("Поиск собеседника...")
        waiting_users.append(user_id)
        match_users(context)

def stop(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id in connected_users:
        disconnect_user(user_id, context, notify_partner=True)
        update.message.reply_text("Вы отключены. Начинается поиск нового собеседника...")
        start(update, context)
    else:
        update.message.reply_text("Вы не подключены к собеседнику.")

def match_users(context: CallbackContext):
    while len(waiting_users) >= 2:
        user1 = waiting_users.pop(0)
        user2 = waiting_users.pop(0)
        connected_users[user1] = user2
        connected_users[user2] = user1
        
        context.bot.send_message(user1, "Вы подключены к собеседнику.")
        context.bot.send_message(user2, "Вы подключены к собеседнику.")
        
        # Устанавливаем таймер на отключение при молчании
        set_inactivity_timer(user1, context)
        set_inactivity_timer(user2, context)

def set_inactivity_timer(user_id, context):
    if user_id in timers:
        timers[user_id].cancel()
    
    timers[user_id] = Timer(MAX_INACTIVITY_TIME, disconnect_user, [user_id, context])
    timers[user_id].start()

def disconnect_user(user_id, context, notify_partner=False):
    if user_id in connected_users:
        partner_id = connected_users.pop(user_id)
        connected_users.pop(partner_id, None)
        
        if notify_partner:
            context.bot.send_message(partner_id, "Ваш собеседник отключился. Поиск нового...")
            # Отправка изображения при прерывании
            with open('телега.jpg', 'rb') as img:
                context.bot.send_photo(chat_id=partner_id, photo=InputFile(img), caption="Ищем нового собеседника...")
            waiting_users.append(partner_id)
            match_users(context)

def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id in connected_users:
        partner_id = connected_users[user_id]
        if partner_id:
            # Пересылаем сообщение собеседнику
            if update.message.text:
                context.bot.send_message(partner_id, update.message.text)
            elif update.message.photo:
                context.bot.send_photo(partner_id, update.message.photo[-1].file_id)
            elif update.message.document:
                context.bot.send_document(partner_id, update.message.document.file_id)
            
            # Обновляем таймер молчания
            set_inactivity_timer(user_id, context)
            set_inactivity_timer(partner_id, context)
    else:
        update.message.reply_text("Собеседник пока не найден. Подождите.")

def timeout_handler(context: CallbackContext):
    user_id = context.job.context
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        context.bot.send_message(user_id, "Время ожидания истекло. Попробуйте снова позже.")

def error(update: Update, context: CallbackContext):
    """Логирование ошибок"""
    logger.warning(f'Update {update} caused error {context.error}')

def main():
    # Создаем бота
    updater = Updater(TOKEN, use_context=True)
    
    # Регистрация обработчиков
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(MessageHandler(Filters.text | Filters.photo | Filters.document, handle_message))
    
    dp.add_error_handler(error)
    
    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
