# Apollolytics Dialogue Bot

## Introduction

The Apollolytics Dialogue Bot is a Telegram bot designed to flag propaganda in articles and facilitate discussions through various dialogue types such as persuasion, inquiry, discovery, negotiation, and more. This bot helps users understand and engage with the content by analyzing it for propaganda and guiding the conversation accordingly.

## How to Run the Docker Container

1. **Create a `.env` file in the project directory with the following content:**
   ```plaintext
   telegram_apollolytics_dialogue_bot=YOUR_TELEGRAM_BOT_TOKEN
   OPENAI_API_KEY=YOUR_API_KEY
   DATABASE_PATH=user_interactions.db

2. **Build the Docker image**
    ``` bash
    docker build -t apollolytics_dialogue_bot .

3. **Run the Docker container**
    ``` bash
    docker run -d apollolytics_dialogue_bot


FOCUS on measuring persuasion ?!
-> check if measuring persuasiveness has a standard
-> willingness to share something ? -> measure how trustworthy something is. 
 -> https://arxiv.org/abs/2402.07395