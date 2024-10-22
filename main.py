import logging
from telegram import Update
from telegram.ext import (Application, CommandHandler, MessageHandler, filters)
from const import TOKEN
import random
from apscheduler.schedulers.background import BackgroundScheduler

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

waiting_users = []
active_chats = {}

TIME_LIMIT = 600

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id

    if user_id in active_chats:
        await context.bot.send_message(chat_id=user_id, text="Вы уже общаетесь с собеседником.")
    else:
        await context.bot.send_message(chat_id=user_id, text="Ищем собеседника...")
        await start_search_for_partner(user_id, context)

async def start_search_for_partner(user_id, context):
    if waiting_users and waiting_users[0] != user_id:
        partner_id = waiting_users.pop(0)
        await connect_users(user_id, partner_id, context)
    else:
        waiting_users.append(user_id)

async def connect_users(user_id, partner_id, context):
    if user_id not in active_chats and partner_id not in active_chats:
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        await context.bot.send_message(chat_id=user_id, text="Найден собеседник!")
        await context.bot.send_message(chat_id=partner_id, text="Найден собеседник!")

        context.job_queue.run_once(disconnect_due_to_timeout, TIME_LIMIT, data={'user_id': user_id, 'partner_id': partner_id})
    else:
        await context.bot.send_message(chat_id=user_id, text="Ошибка соединения. Повторите попытку.")

async def disconnect_due_to_timeout(context: CallbackContext) -> None:
    user_id = context.job.data['user_id']
    partner_id = context.job.data['partner_id']

    if user_id in active_chats and active_chats[user_id] == partner_id:
        await disconnect_users(user_id, partner_id, context)

async def disconnect_users(user_id, partner_id, context):
    del active_chats[user_id]
    del active_chats[partner_id]

    await context.bot.send_message(chat_id=user_id, text="Собеседник отключен. Ищем нового собеседника...")
    await context.bot.send_message(chat_id=partner_id, text="Собеседник отключен. Ищем нового собеседника...")

    await start_search_for_partner(user_id, context)
    await start_search_for_partner(partner_id, context)

async def stop(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await disconnect_users(user_id, partner_id, context)
    else:
        await context.bot.send_message(chat_id=user_id, text="Вы не находитесь в чате.")

async def next(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await disconnect_users(user_id, partner_id, context)
    await context.bot.send_message(chat_id=user_id, text="Ищем нового собеседника...")
    await start_search_for_partner(user_id, context)

async def forward_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)

async def forward_media(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        if update.message.photo:
            await context.bot.send_photo(chat_id=partner_id, photo=update.message.photo[-1].file_id)
        elif update.message.video:
            await context.bot.send_video(chat_id=partner_id, video=update.message.video.file_id)
        elif update.message.sticker:
            await context.bot.send_sticker(chat_id=partner_id, sticker=update.message.sticker.file_id)
        elif update.message.voice:
            await context.bot.send_voice(chat_id=partner_id, voice=update.message.voice.file_id)

async def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("next", next))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.STICKER | filters.VOICE, forward_media))

    await application.start_polling()
    await application.idle()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
