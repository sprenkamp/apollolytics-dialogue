# Apollolytics Dialogue Bot

## Introduction

The Apollolytics Dialogue Bot is a Telegram bot designed to flag propaganda in articles and facilitate discussions through various dialogue types such as persuasion, inquiry, discovery, negotiation, and more. This bot helps users understand and engage with the content by analyzing it for propaganda and guiding the conversation accordingly.

## How to Run the Docker Container

1. **Create a `.env` file in the project directory with the following content:**
   ```plaintext
   telegram_apollolytics_dialogue_bot=YOUR_TELEGRAM_BOT_TOKEN
   DATABASE_PATH=/db/user_interactions.db

2. **Build the Docker image**
    ```
    docker build -t apollolytics_dialogue_bot .

3. **Run the Docker container**
    ```
    docker run -d --name apollolytics_dialogue_bot .

