from telegram import Update, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from const import TOKEN
import time

# Словарь для хранения текущих чатов
active_chats = {}
waiting_users = []

# Путь к фото для отправки при завершении чата
PHOTO_PATH = 'телега.jpg'

# Функция для начала поиска собеседника
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        update.message.reply_text("Вы уже находитесь в чате.")
        return

    if waiting_users and waiting_users[0] != user_id:
        # Если есть кто-то в ожидании и это не сам пользователь
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        
        context.bot.send_message(chat_id=partner_id, text="Найден собеседник!")
        update.message.reply_text("Найден собеседник!")
    else:
        # Если никого нет в очереди, добавляем пользователя в ожидание
        waiting_users.append(user_id)
        update.message.reply_text("Ищем собеседника, подождите...")
        
        # Ограничение поиска на 10 минут
        context.job_queue.run_once(time_up, 600, context=user_id)

# Функция для завершения поиска после 10 минут
def time_up(context: CallbackContext):
    user_id = context.job.context
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        context.bot.send_message(chat_id=user_id, text="Время поиска истекло, собеседник не найден.")

# Функция для отправки сообщений, фото, видео и т.д.
def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in active_chats:
        update.message.reply_text("Вы не в чате. Используйте /start, чтобы найти собеседника.")
        return

    partner_id = active_chats[user_id]
    
    # Пересылаем различные типы сообщений собеседнику
    if update.message.text:
        context.bot.send_message(chat_id=partner_id, text=update.message.text)
    elif update.message.photo:
        context.bot.send_photo(chat_id=partner_id, photo=update.message.photo[-1].file_id)
    elif update.message.video:
        context.bot.send_video(chat_id=partner_id, video=update.message.video.file_id)
    elif update.message.sticker:
        context.bot.send_sticker(chat_id=partner_id, sticker=update.message.sticker.file_id)
    elif update.message.voice:
        context.bot.send_voice(chat_id=partner_id, voice=update.message.voice.file_id)

# Функция для смены собеседника
def next(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in active_chats:
        update.message.reply_text("Вы не в чате. Используйте /start, чтобы начать.")
        return

    partner_id = active_chats.pop(user_id)
    active_chats.pop(partner_id, None)

    # Уведомляем собеседника и отправляем ему фото
    context.bot.send_message(chat_id=partner_id, text="Ваш собеседник завершил чат.")
    context.bot.send_photo(chat_id=partner_id, photo=open(PHOTO_PATH, 'rb'))
    
    # Уведомляем пользователя, завершившего чат
    update.message.reply_text("Чат завершен. Ищем нового собеседника...")

    # Удаляем фото через 10 секунд
    context.job_queue.run_once(delete_photo, 10, context={'chat_id': partner_id})

    # Начинаем поиск нового собеседника
    start(update, context)

# Функция для удаления фото
def delete_photo(context: CallbackContext):
    chat_id = context.job.context['chat_id']
    context.bot.delete_message(chat_id=chat_id, message_id=context.job.context.get('message_id'))

# Функция для завершения чата вручную
def stop(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in active_chats:
        update.message.reply_text("Вы не в чате.")
        return

    partner_id = active_chats.pop(user_id)
    active_chats.pop(partner_id, None)

    # Уведомляем собеседника и отправляем фото
    context.bot.send_message(chat_id=partner_id, text="Ваш собеседник завершил чат.")
    context.bot.send_photo(chat_id=partner_id, photo=open(PHOTO_PATH, 'rb'))

    update.message.reply_text("Чат завершен.")

# Основная функция для запуска бота
def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    # Обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("next", next))
    dp.add_handler(CommandHandler("stop", stop))

    # Обработчики сообщений (текст, медиа)
    dp.add_handler(MessageHandler(Filters.text | Filters.photo | Filters.video | Filters.sticker | Filters.voice, handle_message))

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
