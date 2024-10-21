from telegram import Update, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from const import TOKEN
import time

# Здесь храним информацию о текущих чатах
active_chats = {}
waiting_users = []

# Путь к фото, которую нужно отправить при завершении чата
PHOTO_PATH = 'телега.jpg'

# Функция для начала поиска собеседника
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in active_chats:
        update.message.reply_text("Вы уже находитесь в чате.")
        return
    
    if waiting_users:
        # Если есть кто-то в ожидании, соединяем пользователей
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        
        context.bot.send_message(chat_id=partner_id, text="Найден собеседник!")
        update.message.reply_text("Найден собеседник!")
    else:
        # Если нет никого в ожидании, добавляем пользователя в список ожидания
        waiting_users.append(user_id)
        update.message.reply_text("Ищем собеседника, подождите...")
        
        # Ограничение поиска собеседника на 10 минут
        context.job_queue.run_once(time_up, 600, context=user_id)

# Функция для завершения поиска после 10 минут ожидания
def time_up(context: CallbackContext):
    user_id = context.job.context
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        context.bot.send_message(chat_id=user_id, text="Время поиска истекло, собеседник не найден.")

# Функция для отправки сообщений
def message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in active_chats:
        update.message.reply_text("Вы не в чате, используйте /start, чтобы начать.")
        return

    partner_id = active_chats[user_id]
    context.bot.send_message(chat_id=partner_id, text=update.message.text)

# Функция для отключения и поиска нового собеседника
def next(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in active_chats:
        update.message.reply_text("Вы не в чате. Используйте /start, чтобы начать.")
        return

    partner_id = active_chats.pop(user_id)
    active_chats.pop(partner_id, None)

    # Уведомляем пользователей об окончании чата
    context.bot.send_message(chat_id=partner_id, text="Ваш собеседник завершил чат. Используйте /start, чтобы найти нового собеседника.")

    # Отправляем картинку пользователю, завершившему чат
    context.bot.send_photo(chat_id=user_id, photo=open(PHOTO_PATH, 'rb'))
    update.message.reply_text("Чат завершен. Ищем нового собеседника...")

    # Удаляем картинку через 10 секунд
    context.job_queue.run_once(delete_photo, 10, context={'chat_id': user_id})

    # Начинаем новый поиск для пользователя
    start(update, context)

# Функция для удаления фото через 10 секунд
def delete_photo(context: CallbackContext):
    chat_id = context.job.context['chat_id']
    context.bot.delete_message(chat_id=chat_id, message_id=context.job.context['message_id'])

# Функция для завершения чата вручную
def stop(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in active_chats:
        update.message.reply_text("Вы не в чате.")
        return

    partner_id = active_chats.pop(user_id)
    active_chats.pop(partner_id, None)

    context.bot.send_message(chat_id=partner_id, text="Ваш собеседник завершил чат.")
    update.message.reply_text("Чат завершен.")

    # Отправляем фото, если диалог был завершен
    context.bot.send_photo(chat_id=user_id, photo=open(PHOTO_PATH, 'rb'))
    context.job_queue.run_once(delete_photo, 10, context={'chat_id': user_id})

# Основная функция для запуска бота
def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    # Обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("next", next))
    dp.add_handler(CommandHandler("stop", stop))

    # Обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message))

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
