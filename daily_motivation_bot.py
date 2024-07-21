import logging
from dotenv import load_dotenv
import os
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

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
categories = [ 'amazing',
    'best', 'birthday', 'business', 'car', 'change', 'communication', 
    'cool', 'courage', 'dad', 'dating', 'dreams', 
    'equality', 'experience', 'failure', 'faith', 'family', 
    'fear', 'fitness', 'food', 'forgiveness', 'freedom', 'friendship', 'funny', 
    'future', 'god', 'good', 'graduation', 'great', 'happiness', 
    'health', 'history', 'home', 'hope', 'humor', 'imagination', 'inspirational', 
    'intelligence',  'knowledge', 'leadership', 'learning', 
    'life', 'love', 'marriage', 'men', 'mom', 'money', 'success'
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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

    context.user_data['category'] = category
    
    await update.message.reply_text(
        f'Thank you {username}! You have chosen {category} category. '
        'Now please choose how often you want to receive motivational quotes:',
        reply_markup=ReplyKeyboardMarkup([['1 Hour', '2 Hours', '4 Hours', '8 Hours', '12 Hours']], one_time_keyboard=True)
    )

    return FREQUENCY

async def set_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    frequency_text = update.message.text
    username = user.username if user.username else user.first_name

    frequency_mapping = {
        '1 Hour': 1,
        '2 Hours': 2,
        '4 Hours': 4,
        '8 Hours': 8,
        '12 Hours': 12
    }

    frequency_Hours = frequency_mapping.get(frequency_text)

    if not frequency_Hours:
        await update.message.reply_text(
            'Invalid frequency selection. Please choose from the provided options.',
            reply_markup=ReplyKeyboardMarkup([['1 Hour', '2 Hours', '4 Hours', '8 Hours','12 Hours']], one_time_keyboard=True)
        )
        return FREQUENCY

    context.user_data['frequency'] = frequency_Hours
    category = context.user_data['category']

    await update.message.reply_text(
        f'Great choice, {username}! You will now receive motivational quotes every {frequency_Hours} Hours.'
        ' You can type /NewQuote anytime to receive a quote immediately.'
    )

    # Schedule the first job immediately
    context.job_queue.run_repeating(send_daily_quote, interval=frequency_Hours * 3600, first=0, data={'chat_id': update.message.chat_id, 'category': category})

    return ConversationHandler.END

async def fetch_quote(category: str) -> str:
    api_url = f'https://api.api-ninjas.com/v1/quotes?category={category}'
    response = requests.get(api_url, headers={'X-Api-Key': API_KEY})

    if response.status_code != requests.codes.ok:
        logger.error(f"Error fetching quote: {response.status_code} - {response.text}")
        return "Could not fetch quote at this time. Please try again later."

    data = response.json()
    if not data:
        logger.error(f"No data received from API: {response.text}")
        return "Could not fetch quote at this time. Please try again later."

    return data[0]['quote']

async def send_daily_quote(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    category = job_data.get('category', 'happiness')
    chat_id = job_data.get('chat_id')
    quote = await fetch_quote(category)
    await context.bot.send_message(chat_id=chat_id, text=quote)

async def daily_quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    category = context.user_data.get('category', 'happiness')
    quote = await fetch_quote(category)
    await update.message.reply_text(quote)

def main() -> None:
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CATEGORY: [MessageHandler(filters.Regex(f'^({"|".join(categories)})$'), set_category)],
            FREQUENCY: [MessageHandler(filters.Regex(f'^({"|".join(["1 Hours", "10 Hours", "15 Hours", "30 Hours", "60 Hours"])})$'), set_frequency)]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("NewQuote", daily_quote))

    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
