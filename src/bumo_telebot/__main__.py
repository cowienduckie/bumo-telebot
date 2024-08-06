import logging
import os

import redis
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

from constants import GET_FB_THOITIETHN_BUTTON, WEATHER_MENU
from facebook_crawler import FacebookCrawler

# Get the Redis URL from the environment variable
r = redis.from_url(os.environ.get("REDIS_URL"))

# Export the API token as an environment variable
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Enable logging
logger = logging.getLogger(__name__)

# Build keyboards
WEATHER_MENU_MARKUP = InlineKeyboardMarkup([[
    InlineKeyboardButton(GET_FB_THOITIETHN_BUTTON, callback_data=GET_FB_THOITIETHN_BUTTON)
]])


def echo(update: Update, context: CallbackContext) -> None:
    """
    This function would be added to the dispatcher as a handler for messages coming from the Bot API
    """

    # Print to console
    print(f'{update.message.from_user.first_name} wrote {update.message.text}')

    # Reply to the user
    update.message.copy(update.message.chat_id)


def weather_menu(update: Update, context: CallbackContext) -> None:
    """
    This handler sends a menu with the inline buttons we pre-assigned above
    """

    menu_string = WEATHER_MENU.format(update.message.from_user.first_name)

    context.bot.send_message(
        update.message.from_user.id,
        menu_string,
        parse_mode=ParseMode.HTML,
        reply_markup=WEATHER_MENU_MARKUP
    )


def button_tap(update: Update, context: CallbackContext) -> None:
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
    update.callback_query.answer()

    # Update message content with corresponding menu section
    update.callback_query.message.edit_text(
        text,
        ParseMode.HTML,
        reply_markup=markup
    )


def main() -> None:
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    # Then, we register each handler and the conditions the update must meet to trigger it
    dispatcher = updater.dispatcher

    # Register commands
    dispatcher.add_handler(CommandHandler("weather", weather_menu))

    # Register handler for inline buttons
    dispatcher.add_handler(CallbackQueryHandler(button_tap))

    # Echo any message that is not a command
    dispatcher.add_handler(MessageHandler(~Filters.command, echo))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
