import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update
from const import TOKEN  # Импортируем токен из файла const.py

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)

logger = logging.getLogger(__name__)

# Списки для отслеживания состояния пользователей
active_chats = {}  # {user_id: partner_id}
waiting_users = []  # Очередь ожидания
stopped_users = set()  # Пользователи, которые остановили бота
banned_users = set()  # Забаненные пользователи

# Команда /start
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    logger.info(f"User {user_id} sent /start")

    if user_id in banned_users:
        context.bot.send_message(chat_id=user_id, text="Вы заблокированы и не можете использовать этого бота.")
        logger.warning(f"Blocked user {user_id} tried to use the bot")
        return

    if user_id in stopped_users:
        stopped_users.remove(user_id)
        logger.info(f"User {user_id} removed from stopped_users list")

    if user_id in active_chats:
        context.bot.send_message(chat_id=user_id, text="Вы уже находитесь в чате. Введите /stop, чтобы выйти.")
        logger.info(f"User {user_id} tried to start while already in a chat")
        return

    context.bot.send_message(chat_id=user_id, text="
Здравствуй, дорогой пользователь! Данный чат-бот предназначен для анонимной переписки между студентами университета МИСиС. Здесь ты можешь чувствовать себя комфортно, не бояться быть открытым и делиться своими переживаниями. Убедительная просьба быть вежливыми друг к другу!")
    start_search_for_partner(user_id, context)

# Команда /stop
def stop(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    logger.info(f"User {user_id} sent /stop")

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        logger.info(f"Disconnecting user {user_id} and partner {partner_id}")

        # Уведомляем партнера
        if partner_id in active_chats:
            context.bot.send_message(chat_id=partner_id, text="Ваш собеседник покинул чат.")

        disconnect_users(user_id, partner_id, context)

    stopped_users.add(user_id)
    logger.info(f"User {user_id} added to stopped_users list")
    context.bot.send_message(chat_id=user_id, text="Вы вышли из чата. Введите /start, чтобы начать новый диалог.")

# Команда /next
def next(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    logger.info(f"User {user_id} sent /next")

    if user_id in stopped_users:
        context.bot.send_message(chat_id=user_id, text="Вы остановили бота. Введите /start, чтобы начать заново.")
        logger.warning(f"User {user_id} tried /next after stopping the bot")
        return

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        logger.info(f"Disconnecting user {user_id} and partner {partner_id} for /next")

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
        logger.warning(f"Blocked user {user_id} attempted to search for a partner")
        return

    if waiting_users and waiting_users[0] != user_id:
        partner_id = waiting_users.pop(0)
        logger.info(f"Connecting user {user_id} with partner {partner_id}")
        connect_users(user_id, partner_id, context)
    else:
        waiting_users.append(user_id)
        logger.info(f"User {user_id} added to waiting list")

# Соединение двух пользователей
def connect_users(user1, user2, context):
    active_chats[user1] = user2
    active_chats[user2] = user1

    logger.info(f"Users {user1} and {user2} connected")
    context.bot.send_message(chat_id=user1, text="Вы подключены к новому собеседнику!")
    context.bot.send_message(chat_id=user2, text="Вы подключены к новому собеседнику!")

# Отключение двух пользователей
def disconnect_users(user_id, partner_id, context):
    if user_id in active_chats:
        del active_chats[user_id]
    if partner_id in active_chats:
        del active_chats[partner_id]
    logger.info(f"Users {user_id} and {partner_id} disconnected")

# Обработка текстовых сообщений
def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    message_text = update.message.text

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        logger.info(f"Message from user {user_id} to partner {partner_id}: {message_text}")
        context.bot.send_message(chat_id=partner_id, text=message_text)
    else:
        logger.info(f"User {user_id} sent a message without a partner: {message_text}")
        context.bot.send_message(chat_id=user_id, text="Вы не подключены к собеседнику. Введите /start, чтобы начать поиск.")

# Обработка стикеров
def handle_sticker(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    sticker_id = update.message.sticker.file_id

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        logger.info(f"Sticker from user {user_id} to partner {partner_id}")
        context.bot.send_sticker(chat_id=partner_id, sticker=sticker_id)
    else:
        logger.info(f"User {user_id} sent a sticker without a partner")
        context.bot.send_message(chat_id=user_id, text="Вы не подключены к собеседнику. Введите /start.")

# Обработка фотографий
def handle_photo(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    photo_id = update.message.photo[-1].file_id
    caption = update.message.caption if update.message.caption else ""

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        logger.info(f"Photo from user {user_id} to partner {partner_id} with caption: {caption}")
        context.bot.send_photo(chat_id=partner_id, photo=photo_id, caption=caption)
    else:
        logger.info(f"User {user_id} sent a photo without a partner")
        context.bot.send_message(chat_id=user_id, text="Вы не подключены к собеседнику. Введите /start.")

# Обработка неизвестных команд
def unknown_command(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    logger.warning(f"User {user_id} sent an unknown command")
    context.bot.send_message(chat_id=user_id, text="Неизвестная команда. Попробуйте /start, /stop или /next.")

# Основная функция запуска бота
def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("next", next))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.sticker, handle_sticker))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(MessageHandler(Filters.command, unknown_command))

    logger.info("Bot started")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
