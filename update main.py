import logging
import random
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
from datetime import datetime, timedelta, time

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot token
TOKEN = '7458025599:AAH9sCuoApy27rsMu7AGjDqLqXtE_yP4UVE'  # Replace with your actual token

# File for data persistence
DATA_FILE = 'data.json'

# Load data function
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    return {"user_access": {}, "predictions": []}

# Save data function
def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file)

# Load data on startup
data = load_data()
user_access = data["user_access"]
predictions = data["predictions"]

# Prediction tracking
total_predictions = 0
successful_predictions = 0

# Access code
ACCESS_CODE = "S1234"

# User preferences
user_preferences = {}

# Generate a prediction
def generate_prediction() -> dict:
    multiplier = round(random.uniform(1, 10), 2)
    assurance_start = round(multiplier / 2, 2)
    assurance_end = round(multiplier / 1.5, 2)
    chance = random.randint(80, 90)
    
    start_time = datetime.now() + timedelta(minutes=random.randint(1, 10))
    end_time = start_time + timedelta(minutes=1)
    expiration_time = end_time + timedelta(minutes=5)

    message = (
        f"🚀 *PREDICTION RESULT* 🚀\n"
        f"➤ Time: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n"
        f"➤ CÔTE: {multiplier}x\n"
        f"➤ Assurance: {assurance_start}x - {assurance_end}x\n"
        f"➤ Chance: {chance}%\n"
        f"Note: Predictions are based on actual data."
    )
    
    return {
        "multiplier": multiplier,
        "chance": chance,
        "message": message,
        "expiration_time": expiration_time.isoformat()
    }

# Update statistics
def update_statistics(is_successful: bool):
    global total_predictions, successful_predictions
    total_predictions += 1
    if is_successful:
        successful_predictions += 1
    success_rate = (successful_predictions / total_predictions) * 100 if total_predictions > 0 else 0
    return success_rate

# Command to start the bot and request access code
def start(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("Stop Predictions", callback_data='stop_predictions')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Welcome to the Prediction Bot! Please enter the access code using /code [your_code].', reply_markup=reply_markup)

# Handle button press
def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == 'stop_predictions':
        user_preferences[user_id] = False
        context.bot.send_message(chat_id=user_id, text="Predictions have been stopped.")
    query.answer()

# Command to check access code
def check_access_code(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if context.args and context.args[0] == ACCESS_CODE:
        user_access[user_id] = True
        save_data({"user_access": user_access, "predictions": predictions})
        update.message.reply_text('Access granted! You can now use /predict, /history, and other commands.')
        context.job_queue.run_repeating(notification_job, interval=60, first=0, context=user_id)
    else:
        logger.warning(f"User {user_id} failed access with code: {context.args[0] if context.args else 'No code'}")
        update.message.reply_text('Invalid access code. Please try again.')

# Notification job
def notification_job(context: CallbackContext):
    user_id = context.job.context
    if user_access.get(user_id, False) and user_preferences.get(user_id, True):
        prediction = generate_prediction()
        context.bot.send_message(chat_id=user_id, text=f"🔔 Good time to Bet!\n{prediction['message']}")

# Daily update job
def daily_update(context: CallbackContext) -> None:
    logger.info("Running daily update...")
    current_time = datetime.now()
    global predictions
    predictions = [p for p in predictions if datetime.fromisoformat(p["expiration_time"]) > current_time]
    new_prediction = generate_prediction()
    predictions.append(new_prediction)
    save_data({"user_access": user_access, "predictions": predictions})
    logger.info("Daily update completed. Predictions updated.")

# Command to get a prediction
def predict(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if not user_access.get(user_id, False):
        update.message.reply_text('You must enter the access code first. Use /start to begin.')
        return

    try:
        prediction = generate_prediction()
        is_successful = random.random() < 0.7
        success_rate = update_statistics(is_successful)

        predictions.append(prediction)
        save_data({"user_access": user_access, "predictions": predictions})
        
        response_message = f"{prediction['message']}\n\nSuccess Rate: {success_rate:.2f}%"
        update.message.reply_text(response_message)
    except Exception as e:
        logger.error(f"Error in predict: {e}")
        update.message.reply_text("An error occurred while generating the prediction.")

# Command to fetch dummy game history
def get_history(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if not user_access.get(user_id, False):
        update.message.reply_text('You must enter the access code first. Use /start to begin.')
        return

    history = [
        {"id": 1, "result": "Win"},
        {"id": 2, "result": "Lose"},
        {"id": 3, "result": "Win"},
    ]
    history_message = '\n'.join([f"Game ID: {game['id']}, Result: {game['result']}" for game in history])
    update.message.reply_text(f"Game History:\n{history_message}")

# Command to filter predictions
def filter_predictions(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if not user_access.get(user_id, False):
        update.message.reply_text('You must enter the access code first. Use /start to begin.')
        return

    filter_value = int(context.args[0]) if context.args and context.args[0].isdigit() else 80
    filtered_predictions = [p for p in predictions if p["chance"] >= filter_value]
    
    if filtered_predictions:
        response_message = "\n".join([p["message"] for p in filtered_predictions])
        update.message.reply_text(f"Filtered Predictions:\n{response_message}")
    else:
        update.message.reply_text('No predictions match the filter.')

# Command to show help information
def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "Welcome to the Prediction Bot! Here are the commands you can use:\n"
        "/start - Welcome message and request access code\n"
        "/code [your_code] - Enter the access code\n"
        "/predict - Get a prediction\n"
        "/history - Fetch game history\n"
        "/filter [value] - Filter predictions by chance (default 80)\n"
        "/help - Show this help message\n"
        "/set_notification [on/off] - Enable or disable notifications"
    )
    update.message.reply_text(help_text)

# Command to set notification preferences
def set_notification(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if context.args and context.args[0].lower() in ['on', 'off']:
        user_preferences[user_id] = context.args[0].lower() == 'on'
        state = "enabled" if user_preferences[user_id] else "disabled"
        update.message.reply_text(f"Notifications have been {state}.")
    else:
        update.message.reply_text("Usage: /set_notification [on/off]")

# Main function to run the bot
def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))  # Handle button presses
    dispatcher.add_handler(CommandHandler("code", check_access_code))  
    dispatcher.add_handler(CommandHandler("predict", predict))
    dispatcher.add_handler(CommandHandler("history", get_history))
    dispatcher.add_handler(CommandHandler("filter", filter_predictions))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("set_notification", set_notification))

    # Schedule daily update at a specific time (e.g., every day at midnight)
    job_queue = updater.job_queue
    job_queue.run_daily(daily_update, time(hour=0, minute=0))

    # Start polling for updates
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
