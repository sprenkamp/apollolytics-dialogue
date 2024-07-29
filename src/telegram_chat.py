import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv
load_dotenv()

from chat import ApollolyticsDialogue

DATABASE_PATH = os.getenv("interactions_db_path")

def log_interaction(user_id, username, date, dialogue_type, system_prompt, user_input, response):
    c.execute('''INSERT INTO interactions (user_id, username, date, dialogue_type, system_prompt, user_input, response)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, username, date, dialogue_type, system_prompt, user_input, response))
    conn.commit()

# Handler for the /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    start_message = (
        "👋 Hi! Welcome to the Apollolytics Dialogue Bot! Here's how you can use this tool:\n\n"
        "1️⃣ Use the /scan command to send me an article for analysis.\n"
        "2️⃣ Choose the type of dialogue you want to have about the article. Here are your options:\n"
        "  - persuasion 🗣️\n"
        "  - inquiry ❓\n"
        "  - discovery 🔍\n"
        "  - negotiation 🤝\n"
        "  - information_seeking 📚\n"
        "  - deliberation 🧠\n"
        "  - eristic ⚡\n"
        "3️⃣ After choosing the dialogue type, send me the article text.\n"
        "4️⃣ Once the article is analyzed, you can ask me questions about it based on the chosen dialogue type.\n\n"
        "Type /help at any time for assistance."
    )
    await update.message.reply_text(start_message)

# Handler for setting the dialogue type based on user input
async def set_dialogue_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    selected_type = update.message.text
    if selected_type in dialogue_values_to_keys:
        context.user_data['dialogue_type'] = dialogue_values_to_keys[selected_type]
        await update.message.reply_text(f'Dialogue type set to: {selected_type}')
        await update.message.reply_text('Now please send me the article you want to analyze.')
        context.user_data['expecting_article'] = True  # Set flag to expect article text
        return ConversationHandler.END  # End the conversation after setting the dialogue type
    else:
        await update.message.reply_text('Invalid dialogue type. Please choose from the provided options.')
        return CHOOSING_DIALOGUE_TYPE  # Remain in the current state waiting for a valid input

# Handler for the /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        "You can send me an article to analyze for propaganda and then ask me questions about it. Use /scan to get started."
    )

# Handler for the /scan command
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [[KeyboardButton(value)] for value in dialogue_types.values()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text('Please choose the dialogue type:', reply_markup=reply_markup)
    return CHOOSING_DIALOGUE_TYPE  # Move to the state where the bot waits for a dialogue type to be chosen

# Handler for processing regular text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if context.user_data.get('expecting_article'):
        article = update.message.text
        context.user_data['expecting_article'] = False  # Reset flag
        await update.message.reply_text('Article received. \nAnalyzing ⏳\n Depending on the article length, this may take a few minutes ☕️')
        
        dialogue_type = context.user_data.get('dialogue_type')
        apollolytics_dialogue = ApollolyticsDialogue(dialogue_type)
        context.user_data['apollolytics_dialogue'] = apollolytics_dialogue

        detected_propaganda = apollolytics_dialogue.detect_propaganda(article)
        await update.message.reply_text('Article analyzed. You can now ask questions about it.')

        context.user_data["system_prompt"], context.user_data["conversation_chain"] = apollolytics_dialogue.create_conversation_chain(article, detected_propaganda)
        log_interaction(user.id, user.username, str(datetime.now()), context.user_data['dialogue_type'], context.user_data["system_prompt"], '', 'Article analyzed. You can now ask questions about it.')
    else:
        apollolytics_dialogue = context.user_data.get('apollolytics_dialogue')
        if not apollolytics_dialogue:
            await update.message.reply_text('Please use /scan to send an article for analysis.')
            return

        user_input = update.message.text
        response = apollolytics_dialogue.process_user_input(context.user_data["conversation_chain"], user_input)
        await update.message.reply_text(response)
        log_interaction(user.id, user.username, str(datetime.now()), context.user_data['dialogue_type'], context.user_data["system_prompt"], user_input, response)

if __name__ == '__main__':
    print("Starting bot...")
    # Initialize the Application with the bot token

    # Retrieve environment variables for the bot token and bot name
    TOKEN = os.getenv('telegram_apollolytics_dialogue_bot')

    # Define the types of dialogues available
    dialogue_types = {
        "persuasion": "persuasion 🗣️",
        "inquiry": "inquiry ❓",
        "discovery": "discovery 🔍",
        "negotiation": "negotiation 🤝",
        "information_seeking": "information_seeking 📚",
        "deliberation": "deliberation 🧠",
        "eristic": "eristic ⚡"
    }

    # Create a reverse mapping dictionary
    dialogue_values_to_keys = {v: k for k, v in dialogue_types.items()}

    # Define states for the conversation
    CHOOSING_DIALOGUE_TYPE = 1

    # Set up the SQLite database
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                date TEXT,
                dialogue_type TEXT,
                system_prompt TEXT,
                user_input TEXT,
                response TEXT
                )''')
    conn.commit()

    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('scan', scan_command)],  # Entry point is the /scan command
        states={
            CHOOSING_DIALOGUE_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_dialogue_type)
            ],
        },
        fallbacks=[],  # Define any fallback handlers if necessary
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Polling...")
    app.run_polling(poll_interval=0.5)
