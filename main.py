import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update
from const import TOKEN  # Импортируем токен из файла const.py

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
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
    logger.info(f"Пользователь {user_id} вызвал команду /start")

    if user_id in banned_users:
        logger.warning(f"Заблокированный пользователь {user_id} попытался начать чат.")
        context.bot.send_message(chat_id=user_id, text="Вы заблокированы и не можете использовать этого бота.")
        return

    if user_id in stopped_users:
        stopped_users.remove(user_id)
        logger.info(f"Пользователь {user_id} удален из списка остановивших бота.")

    if user_id in active_chats:
        logger.info(f"Пользователь {user_id} уже в активном чате.")
        context.bot.send_message(chat_id=user_id, text="Вы уже находитесь в чате. Введите /stop, чтобы выйти.")
        return

    context.bot.send_message(chat_id=user_id, text="Здравствуй, дорогой пользователь! Данный чат-бот предназначен для анонимной переписки между студентами университета МИСиС. Здесь ты можешь чувствовать себя комфортно, не бояться быть открытым и делиться своими переживаниями. Убедительная просьба быть вежливыми друг к другу!")
    start_search_for_partner(user_id, context)

# Команда /stop
def stop(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    logger.info(f"Пользователь {user_id} вызвал команду /stop")

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        logger.info(f"Пользователь {user_id} отключается от собеседника {partner_id}")

        # Уведомляем партнера
        if partner_id in active_chats:
            context.bot.send_message(chat_id=partner_id, text="Ваш собеседник покинул чат.")

        disconnect_users(user_id, partner_id, context)

    stopped_users.add(user_id)
    context.bot.send_message(chat_id=user_id, text="Вы вышли из чата. Введите /start, чтобы начать новый диалог.")

# Команда /next
def next(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    logger.info(f"Пользователь {user_id} вызвал команду /next")

    if user_id in stopped_users:
        logger.warning(f"Пользователь {user_id} в состоянии остановки попытался использовать /next.")
        context.bot.send_message(chat_id=user_id, text="Вы остановили бота. Введите /start, чтобы начать заново.")
        return

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        logger.info(f"Пользователь {user_id} отключается от собеседника {partner_id} для поиска нового.")
        
        # Уведомляем партнера
        if partner_id in active_chats:
            context.bot.send_message(chat_id=partner_id, text="Ваш собеседник покинул чат.")

        disconnect_users(user_id, partner_id, context)

    context.bot.send_message(chat_id=user_id, text="Ищем нового собеседника...")
    start_search_for_partner(user_id, context)

# Поиск нового собеседника
def start_search_for_partner(user_id, context):
    logger.info(f"Пользователь {user_id} начал поиск собеседника.")
    
    if user_id in banned_users:
        logger.warning(f"Заблокированный пользователь {user_id} попытался найти собеседника.")
        context.bot.send_message(chat_id=user_id, text="Вы заблокированы за нарушение правил.")
        return

    if waiting_users and waiting_users[0] != user_id:
        partner_id = waiting_users.pop(0)
        logger.info(f"Пользователи {user_id} и {partner_id} подключены.")
        connect_users(user_id, partner_id, context)
    else:
        waiting_users.append(user_id)
        logger.info(f"Пользователь {user_id} добавлен в очередь ожидания.")

# Соединение двух пользователей
def connect_users(user1, user2, context):
    active_chats[user1] = user2
    active_chats[user2] = user1

    logger.info(f"Пользователи {user1} и {user2} соединены.")
    context.bot.send_message(chat_id=user1, text="Вы подключены к новому собеседнику!")
    context.bot.send_message(chat_id=user2, text="Вы подключены к новому собеседнику!")

# Отключение двух пользователей
def disconnect_users(user_id, partner_id, context):
    if user_id in active_chats:
        logger.info(f"Отключение пользователя {user_id}")
        del active_chats[user_id]
    if partner_id in active_chats:
        logger.info(f"Отключение пользователя {partner_id}")
        del active_chats[partner_id]

# Обработка текстовых сообщений
def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    text = update.message.text
    logger.info(f"Получено сообщение от пользователя {user_id}: {text}")

    if user_id in active_chats:
        partner_id = active_chats[user_id]
        context.bot.send_message(chat_id=partner_id, text=text)
    else:
        context.bot.send_message(chat_id=user_id, text="Вы не подключены к собеседнику. Введите /start, чтобы начать поиск.")

# Обработка неизвестных команд
def unknown_command(update: Update, context: CallbackContext) -> None:
    command = update.message.text
    user_id = update.message.chat_id
    logger.warning(f"Неизвестная команда от пользователя {user_id}: {command}")
    context.bot.send_message(chat_id=user_id, text="Неизвестная команда. Попробуйте /start, /stop или /next.")

# Основная функция запуска бота
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("next", next))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.command, unknown_command))

    logger.info("Бот запущен.")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
