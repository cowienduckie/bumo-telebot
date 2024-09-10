import asyncio
import datetime
import logging
import os
import random
from typing import Tuple

import pytz
import redis
from telegram import Chat, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.constants import ParseMode
from telegram.ext import (
    filters,
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ApplicationBuilder,
)

from constants import (
    GET_FB_THOITIETHN_BUTTON,
    WEATHER_MENU,
    FB_WEATHER_CACHE_KEY,
    REDIS_URL_KEY,
    BOT_TOKEN_KEY,
    WEATHER_SUCCESS_MESSAGE,
    WEATHER_FAILURE_MESSAGE,
)
from facebook_crawler import FacebookCrawler
from redis_persistence import RedisPersistence

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Get the Redis URL from the environment variable
REDIS_URL = os.environ.get(REDIS_URL_KEY)
r = redis.from_url(REDIS_URL)

# Export the API token as an environment variable
BOT_TOKEN = os.environ.get(BOT_TOKEN_KEY)

# Build keyboards
WEATHER_MENU_MARKUP = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                GET_FB_THOITIETHN_BUTTON, callback_data=GET_FB_THOITIETHN_BUTTON
            )
        ]
    ]
)


async def start_private_chat(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Greets the user and records that they started a chat with the bot if it's a private chat.
    Since no `my_chat_member` update is issued when a user starts a private chat with the bot
    for the first time, we have to track it explicitly here.
    """
    user_name = update.effective_user.full_name
    chat = update.effective_chat

    if chat.type != Chat.PRIVATE or chat.id in context.bot_data.get("user_ids", set()):
        return

    context.bot_data.setdefault("user_ids", set()).add(chat.id)

    await update.effective_message.reply_text(
        f"Welcome {user_name}. Me is Bumo chatbot. Glad to meet you!"
    )


async def random_choice(update: Update, context: CallbackContext) -> None:
    """
    This handler sends responses a random choice from the list of arguments
    """
    if not context.args:
        text = "🙏 You need to provide a list of choices to pick from."
    else:
        text = f"🎲 The random choice is: {random.choice(context.args)}"

    await context.bot.send_message(update.message.from_user.id, text)


async def weather(update: Update, context: CallbackContext) -> None:
    """
    This handler sends a menu with the inline buttons we pre-assigned above
    """
    # Put the user's name in the menu's greeting
    menu_string = WEATHER_MENU.format(update.message.from_user.first_name)

    # Send the menu to the user
    await context.bot.send_message(
        update.message.from_user.id,
        menu_string,
        parse_mode=ParseMode.HTML,
        reply_markup=WEATHER_MENU_MARKUP,
    )


async def get_weather_data(is_daily_send=False) -> Tuple[str, InlineKeyboardMarkup]:
    # Check if the data is being sent for daily weather forecast, if so, delete the cache
    if is_daily_send:
        r.delete(FB_WEATHER_CACHE_KEY)

    # Get the latest post from the Facebook page
    if (post_url := r.get(FB_WEATHER_CACHE_KEY)) is None:
        # Get the data using the FacebookCrawler
        crawler = FacebookCrawler(logging)
        post_url = crawler.get_latest_post("thoitietHN")

        # Cache the URL
        if post_url is not None:
            r.set(FB_WEATHER_CACHE_KEY, post_url)
            # Set expiration time to 1 hour
            r.expire(FB_WEATHER_CACHE_KEY, 3600)
        else:
            logging.error("Failed to get the latest post from the Facebook page.")
    else:
        # Get the URL from the cache
        post_url = post_url.decode("utf-8")

    # Prepare the text and markup
    if post_url is None:
        text = WEATHER_FAILURE_MESSAGE
        markup = None
    else:
        text = WEATHER_SUCCESS_MESSAGE.format(post_url)
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Go to Post", url=post_url)]]
        )

    return text, markup


async def send_weather(update: Update, context: CallbackContext) -> None:
    """
    This handler processes the inline buttons on the menu
    """
    if update.callback_query.data != GET_FB_THOITIETHN_BUTTON:
        return

    text, markup = await get_weather_data()

    # Update message content with corresponding menu section
    await update.callback_query.edit_message_text(
        text, ParseMode.HTML, reply_markup=markup
    )


async def send_daily_weather(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends the daily weather forecast to the users who have started a chat with the bot
    """
    # Get the latest post from the Facebook page
    text, markup = await get_weather_data()

    # If text is WEATHER_FAILURE_MESSAGE, retry to get the latest post up to 10 times
    if text == WEATHER_FAILURE_MESSAGE:
        for _ in range(10):
            await asyncio.sleep(120)  # Wait for 2 minutes before retrying
            text, markup = await get_weather_data()

            if text != WEATHER_FAILURE_MESSAGE:
                break

    # Send the weather forecast to all users who have started a chat with the bot
    for user_id in context.bot_data.setdefault("user_ids", set()):
        await context.bot.send_message(
            chat_id=user_id, text=text, parse_mode=ParseMode.HTML, reply_markup=markup
        )


def main() -> None:
    application = (
        ApplicationBuilder().token(BOT_TOKEN).persistence(RedisPersistence(r)).build()
    )

    # Job queue
    job_queue = application.job_queue

    job_queue.run_daily(
        callback=send_daily_weather,
        time=datetime.time(hour=7, minute=30, tzinfo=pytz.timezone("Asia/Ho_Chi_Minh")),
        days=(0, 1, 2, 3, 4, 5, 6),
        name="daily_weather",
    )

    # Command handlers
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(CommandHandler("random_choice", random_choice))

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(send_weather))

    # Message handlers
    application.add_handler(MessageHandler(filters.ALL, start_private_chat))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
