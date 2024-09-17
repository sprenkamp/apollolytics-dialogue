import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv
load_dotenv()

from apollo_dialogue import ApollolyticsDialogue

DATABASE_PATH = os.getenv("interactions_db_path")

def log_interaction(user_id, username, date, user_input, response):
    """
    Log interaction details into the database.
    """
    c.execute('''INSERT INTO interactions (user_id, username, date, dialogue_type, system_prompt, user_input, response)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, username, date, "Socratic", context.user_data["system_prompt"], user_input, response))
    conn.commit()

# Handler for the /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send a welcome message and instructions when the user starts the bot.
    """
    user = update.effective_user
    start_message = """
    👋 Hi! Welcome to the Apollolytics Socratic Dialogue Bot. Here, we engage in thoughtful discussions about articles and explore the potential use of propaganda and disinformation.

    Here's how to use this tool:

    1️⃣ Use the /scan command to send me an article for analysis.
    2️⃣ After sending the article, you can ask me questions about it. We'll explore the content together Socratically, focusing on critical thinking and self-reflection.

    Type /help at any time for assistance.
    """
    await update.message.reply_text(start_message)

# Handler for the /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Provide help instructions to the user.
    """
    help_message = """
    Send me an article to analyze for propaganda, and then ask me questions about it. Use /scan to get started.
    """
    await update.message.reply_text(help_message)

# Handler for the /scan command
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Prompt the user to send an article for analysis.
    """
    await update.message.reply_text('Please send me the article you want to analyze.')
    context.user_data['expecting_article'] = True  # Set flag to expect article text

# Handler for processing regular text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle user messages: analyze the article or process user queries after analysis.
    """
    user = update.effective_user
    if context.user_data.get('expecting_article'):
        article = update.message.text
        context.user_data['expecting_article'] = False  # Reset flag
        await update.message.reply_text('Article received. \nAnalyzing ⏳\n Depending on the article length, this may take a few minutes ☕️')
        
        apollolytics_dialogue = ApollolyticsDialogue("socratic")  # Always use Socratic dialogue
        context.user_data['apollolytics_dialogue'] = apollolytics_dialogue

        detected_propaganda = apollolytics_dialogue.detect_propaganda(article)
        await update.message.reply_text('Article analyzed. You can now ask questions about it.')

        context.user_data["system_prompt"], context.user_data["conversation_chain"] = apollolytics_dialogue.create_conversation_chain(article, detected_propaganda)
        log_interaction(user.id, user.username, str(datetime.now()), '', 'Article analyzed. You can now ask questions about it.')
    else:
        apollolytics_dialogue = context.user_data.get('apollolytics_dialogue')
        if not apollolytics_dialogue:
            await update.message.reply_text('Please use /scan to send an article for analysis.')
            return

        user_input = update.message.text
        response = apollolytics_dialogue.process_user_input(context.user_data["conversation_chain"], user_input)
        await update.message.reply_text(response)
        log_interaction(user.id, user.username, str(datetime.now()), user_input, response)

if __name__ == '__main__':
    print("Starting bot...")
    # Initialize the Application with the bot token

    # Retrieve environment variables for the bot token and bot name
    TOKEN = os.getenv('telegram_apollolytics_dialogue_bot')

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
    
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('scan', scan_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Polling...")
    app.run_polling(poll_interval=0.5)
