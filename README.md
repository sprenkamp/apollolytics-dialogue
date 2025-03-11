# Apollolytics Dialogue Bot

## Introduction

The Apollolytics Dialogue Bot is a Telegram bot designed to flag propaganda in articles and facilitate discussions through various dialogue types such as persuasion, inquiry, discovery, negotiation, and more. This bot helps users understand and engage with the content by analyzing it for propaganda and guiding the conversation accordingly.

## How to Run the Docker Container

1. **Create a `.env` file in the project directory with the following content:**
   ```plaintext
   telegram_apollolytics_dialogue_bot=YOUR_TELEGRAM_BOT_TOKEN
   OPENAI_API_KEY=YOUR_API_KEY
   DATABASE_PATH=user_interactions.db
   ```

2. **Build the Docker image**
   ```bash
   docker build -t apollolytics_dialogue_bot .
   ```

3. **Run the Docker container**
   ```bash
   docker run -d apollolytics_dialogue_bot
   ```

## DynamoDB Integration

The application now supports saving conversation data to AWS DynamoDB. This includes:

- Article content
- Dialogue mode (e.g., critical, positive)
- Origin URL of the request
- Propaganda analysis results
- Full conversation transcript (both text and audio)

### Configuration

To enable DynamoDB storage, set the following environment variables:

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
DYNAMODB_TABLE=apollolytics_dialogues
```

### Data Structure

The DynamoDB table uses a composite primary key:
- Partition key: `session_id` (string) - Unique identifier for each conversation
- Sort key: `timestamp` (number) - Unix timestamp for each event

Each item also includes:
- `event_type` - Type of event ("session_init", "message", "propaganda_analysis", "session_end")
- `created_at` - ISO timestamp
- Event-specific data (depending on the event type)

### Event Types

1. **session_init**: Stores initial session data
   - `article` - Full article text
   - `dialogue_mode` - Mode of conversation
   - `origin_url` - URL that originated the request

2. **propaganda_analysis**: Stores propaganda detection results
   - `propaganda_result` - Full analysis results

3. **message**: Stores conversation messages
   - `role` - "user" or "assistant"
   - `message_id` - Unique ID for the message
   - `message_content` - Full message content
   - `transcript` - Text transcript (if available)

4. **session_end**: Marks session completion
   - `reason` - Why the session ended (normal, error, etc.)

### DynamoDB Integration

The application automatically saves all conversation data to AWS DynamoDB, including:
- Article content
- Dialogue mode (critical, positive, etc.)
- Origin URL (where the request came from)
- All messages between user and assistant
- Propaganda detection results

#### Running Locally

Create a `.env` file with your AWS credentials:
```
OPENAI_API_KEY=your_openai_key
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=eu-north-1  # Stockholm region
DYNAMODB_TABLE=apollolytics_dialogues
```

Then run:
```bash
docker build -t apollolytics_dialogue_bot .
docker run -p 8080:8080 --env-file .env apollolytics_dialogue_bot
```

#### Server Deployment

The same setup works on your server - just provide the AWS credentials as environment variables when running the container.

The first time the application runs, it will automatically create the DynamoDB table if it doesn't exist, using this schema:
- Primary key: `session_id` (string)
- Sort key: `timestamp` (number)

No additional setup required!

### Research Notes

FOCUS on measuring persuasion ?!
-> check if measuring persuasiveness has a standard
-> willingness to share something ? -> measure how trustworthy something is. 
 -> https://arxiv.org/abs/2402.07395