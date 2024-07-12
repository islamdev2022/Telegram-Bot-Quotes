import logging
from dotenv import load_dotenv
import os
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.ext import JobQueue
import datetime
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

# Accessing variables
token = os.getenv('TOKEN')
API_KEY = os.getenv('APIKEY')

CATEGORY, QUOTE, FREQUENCY, SET_FREQUENCY = range(4)

# List of categories
categories = [
    'alone', 'amazing', 'anger', 'art', 'attitude', 'beauty',
    'best', 'birthday', 'business', 'car', 'change', 'communication', 'computers', 
    'cool', 'courage', 'dad', 'dating', 'death', 'design', 'dreams', 'education', 
    'environmental', 'equality', 'experience', 'failure', 'faith', 'family', 'famous',
    'fear', 'fitness', 'food', 'forgiveness', 'freedom', 'friendship', 'funny', 
    'future', 'god', 'good', 'government', 'graduation', 'great', 'happiness', 
    'health', 'history', 'home', 'hope', 'humor', 'imagination', 'inspirational', 
    'intelligence', 'jealousy', 'knowledge', 'leadership', 'learning', 'legal', 
    'life', 'love', 'marriage', 'medical', 'men', 'mom', 'money', 'morning', 
    'movies', 'success'
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    username = user.username if user.username else user.first_name

    reply_keyboard = [categories[i:i + 3] for i in range(0, len(categories), 3)]

    await update.message.reply_text(
        f'Hi {username} ! I am your Daily Motivation Bot. Please choose a category for your quotes:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return CATEGORY

async def set_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    category = update.message.text
    username = user.username if user.username else user.first_name
    logger.info("Category chosen by %s: %s", user.first_name, category)

    context.user_data['category'] = category
    
    await update.message.reply_text(
        f'Thank you {username}! You have chosen {category} category. '
        'Now please choose how often you want to receive motivational quotes:',
        reply_markup=ReplyKeyboardMarkup([['1 hour', '2 hours', '4 hours', '8 hours','12 hours']], one_time_keyboard=True)
    )

    return FREQUENCY


async def set_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    frequency_text = update.message.text
    username = user.username if user.username else user.first_name

    frequency_mapping = {
        '1 hour': 1,
        '2 hours': 2,
        '4 hours': 4,
        '8 hours': 8,
        '12 hours': 12
    }

    frequency_hours = frequency_mapping.get(frequency_text)

    if not frequency_hours:
        await update.message.reply_text(
            'Invalid frequency selection. Please choose from the provided options.',
            reply_markup=ReplyKeyboardMarkup([['1 hour', '2 hours', '4 hours', '8 hours','12 hours']], one_time_keyboard=True)
        )
        return FREQUENCY

    context.user_data['frequency'] = frequency_hours

    await update.message.reply_text(
        f'Great choice, {username}! You will now receive motivational quotes every {frequency_hours} hours.'
        ' You can type /NewQuote anytime to receive a quote immediately.'
    )

    # Schedule the first job immediately
    context.job_queue.run_repeating(send_daily_quote, interval=frequency_hours * 3600, first=0, context=update.message.chat_id)

    return ConversationHandler.END


async def fetch_quote(category: str) -> str:
    api_url = f'https://api.api-ninjas.com/v1/quotes?category={category}'
    response = requests.get(api_url, headers={'X-Api-Key': API_KEY})
    if response.status_code == requests.codes.ok:
        data = response.json()
        if data:
            return data[0]['quote']
    return "Could not fetch quote at this time. Please try again later."

async def send_daily_quote(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    user_data = context.job.context
    category = user_data.get('category', 'happiness')
    quote = await fetch_quote(category)
    await context.bot.send_message(job.context, text=quote)
    
    
async def daily_quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    category = context.user_data.get('category', 'happiness')
    quote = await fetch_quote(category)
    await update.message.reply_text(quote)


def main() -> None:
    # Replace 'YOUR_TOKEN_HERE' with your bot's token
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CATEGORY: [MessageHandler(filters.Regex(f'^({"|".join(categories)})$'), set_category)],
            FREQUENCY: [MessageHandler(filters.Regex(f'^({"|".join(['1 hour', '2 hours', '4 hours', '8 hours','12 hours'])})$'), set_frequency)]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("NewQuote", daily_quote))

    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()