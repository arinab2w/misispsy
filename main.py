from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update
from const import TOKEN  # Импортируем токен из файла const.py

# Списки для отслеживания состояния пользователей
active_chats = {}  # {user_id: partner_id}
waiting_users = []  # Очередь ожидания
stopped_users = set()  # Пользователи, которые остановили бота
banned_users = set()  # Забаненные пользователи

# Команда /start
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id

    if user_id in banned_users:
        context.bot.send_message(chat_id=user_id, text="Вы заблокированы и не можете использовать этого бота.")
        return

    if user_id in stopped_users:
        stopped_users.remove(user_id)

    if user_id in active_chats:
        context.bot.send_message(chat_id=user_id, text="Вы уже находитесь в чате. Введите /stop, чтобы выйти.")
        return

    context.bot.send_message(chat_id=user_id, text="Добро пожаловать в анонимный чат! Ищем собеседника...")
    start_search_for_partner(user_id, context)

# Команда /stop
def stop(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id

    if user_id in active_chats:
        partner_id = active_chats[user_id]

        # Уведомляем партнера
        if partner_id in active_chats:
            context.bot.send_message(chat_id=partner_id, text="Ваш собеседник покинул чат.")

        disconnect_users(user_id, partner_id, context)

    stopped_users.add(user_id)
    context.bot.send_message(chat_id=user_id, text="Вы вышли из чата. Введите /start, чтобы начать новый диалог.")

# Команда /next
def next(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id

    if user_id in stopped_users:
        context.bot.send_message(chat_id=user_id, text="Вы остановили бота. Введите /start, чтобы начать заново.")
        return

    if user_id in active_chats:
        partner_id = active_chats[user_id]

        # Уведомляем партнера
        if partner_id in active_chats:
            context.bot.send_message(chat_id=partner_id, text="Ваш собеседник покинул чат.")

        disconnect_users(user_id, partner_id, context)

    context.bot.send_message(chat_id=user_id, text="Ищем нового собеседника...")
    start_search_for_partner(user_id, context)

# Поиск нового собеседника
def start_search_for_partner(user_id, context):
    if user_id in banned_users:
        context.bot.send_message(chat_id=user_id, text="Вы заблокированы за нарушение правил.")
        return

    if waiting_users and waiting_users[0] != user_id:
        partner_id = waiting_users.pop(0)
        connect_users(user_id, partner_id, context)
    else:
        waiting_users.append(user_id)

# Соединение двух пользователей
def connect_users(user1, user2, context):
    active_chats[user1] = user2
    active_chats[user2] = user1

    context.bot.send_message(chat_id=user1, text="Вы подключены к новому собеседнику!")
    context.bot.send_message(chat_id=user2, text="Вы подключены к новому собеседнику!")

# Отключение двух пользователей
def disconnect_users(user_id, partner_id, context):
    if user_id in active_chats:
        del active_chats[user_id]
    if partner_id in active_chats:
        del active_chats[partner_id]

# Обработка текстовых сообщений
def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        context.bot.send_message(chat_id=user_id, text="Вы не подключены к собеседнику. Введите /start, чтобы начать поиск.")

# Обработка стикеров
def handle_sticker(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        context.bot.send_sticker(chat_id=partner_id, sticker=update.message.sticker.file_id)
    else:
        context.bot.send_message(chat_id=user_id, text="Вы не подключены к собеседнику. Введите /start.")

# Обработка фотографий
def handle_photo(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        photo = update.message.photo[-1].file_id  # Берем фото с максимальным разрешением
        caption = update.message.caption if update.message.caption else ""
        context.bot.send_photo(chat_id=partner_id, photo=photo, caption=caption)
    else:
        context.bot.send_message(chat_id=user_id, text="Вы не подключены к собеседнику. Введите /start.")

# Обработка неизвестных команд
def unknown_command(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(chat_id=update.message.chat_id, text="Неизвестная команда. Попробуйте /start, /stop или /next.")

# Основная функция запуска бота
def main():
    updater = Updater(TOKEN, use_context=True)  # Используем токен из const.py

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("next", next))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.sticker, handle_sticker))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(MessageHandler(Filters.command, unknown_command))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
