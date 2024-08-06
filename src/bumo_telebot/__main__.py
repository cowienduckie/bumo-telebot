import logging
import os

import redis
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import filters, CallbackContext, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ApplicationBuilder
from telegram.constants import ParseMode
from constants import GET_FB_THOITIETHN_BUTTON, WEATHER_MENU
from facebook_crawler import FacebookCrawler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get the Redis URL from the environment variable
r = redis.from_url(os.environ.get("REDIS_URL"))

# Export the API token as an environment variable
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Build keyboards
WEATHER_MENU_MARKUP = InlineKeyboardMarkup([[
    InlineKeyboardButton(GET_FB_THOITIETHN_BUTTON, callback_data=GET_FB_THOITIETHN_BUTTON)
]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    This function would be added to the dispatcher as a handler for the /start command
    """
    # Send a welcome message
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Me is Bumo chatbot. Glad to meet you!"
    )


async def echo(update: Update, context: CallbackContext) -> None:
    """
    This function would be added to the dispatcher as a handler for messages coming from the Bot API
    """
    # Print to console
    print(f'{update.message.from_user.first_name} wrote {update.message.text}')

    # Reply to the user
    await update.message.copy(update.message.chat_id)


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
        reply_markup=WEATHER_MENU_MARKUP
    )


async def button_tap(update: Update, context: CallbackContext) -> None:
    """
    This handler processes the inline buttons on the menu
    """
    data = update.callback_query.data
    text = ''
    markup = None

    if data == GET_FB_THOITIETHN_BUTTON:
        if (post_url := r.get("thoitietHN")) is None:
            crawler = FacebookCrawler()
            post_url = crawler.get_latest_post("thoitietHN")

            r.set("thoitietHN", post_url)
            r.expire("thoitietHN", 3600)  # Set expiration time to 1 hour
        else:
            post_url = post_url.decode('utf-8')

        if post_url is None:
            text = "<b>🙇 Sorry, I couldn't find the latest post from Thời Tiết Hà Nội</b>"
            markup = None
        else:
            text = f"<a href=\"{post_url}\"><b>🔗 Latest post from Thời Tiết Hà Nội</b></a>"
            markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("Go to Post", url=post_url)
            ]])

    # Close the query to end the client-side loading animation
    await update.callback_query.answer()

    # Update message content with corresponding menu section
    await update.callback_query.edit_message_text(
        text,
        ParseMode.HTML,
        reply_markup=markup
    )


def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler("weather", weather))

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(button_tap))

    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

    application.run_polling()


if __name__ == '__main__':
    main()
