# Apollolytics Dialogue Backend

This is the backend server for the Apollolytics Dialogue application, which provides an interactive conversational experience with different dialogue modes.

## Setup

1. Install dependencies:
```bash
pip install fastapi uvicorn websockets requests numpy
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your-api-key-here
```

## Running the Server

### Standard WebSocket Server
```bash
uvicorn app:app --host 0.0.0.0 --port 8080
```

### Real-time Speech Server
```bash
uvicorn ws_speech_real-time:app --host 0.0.0.0 --port 8000
```

## Testing

### Generate Test Audio
Create a test WAV file for audio input testing:
```bash
python generate_test_audio.py
```

### Test Session Creation
Verify that your API key can create OpenAI Realtime API sessions:
```bash
python test_session_creation.py
```

### Basic API Test
Test the real-time API implementation with text and optional audio:
```bash
python test_realtime_api.py
python test_realtime_api.py --audio
```

### Full Conversation Test
Simulate a multi-turn conversation:
```bash
python test_full_conversation.py --turns 3
```

### Run All Tests
```bash
./run_tests.sh
```

## Configuration

- The server supports two dialogue modes: `critical` and `supportive`
- System prompts for each mode are defined in `prompts/system_prompts.py`
- WebSocket endpoints:
  - `/ws/conversation` - Main conversation endpoint

## Integration with Frontend

The frontend connects to the WebSocket server at:
- Production: `wss://your-domain.com/ws/conversation`
- Local development: `ws://localhost:8000/ws/conversation`

## Architecture

- `app.py` - Main FastAPI application
- `ws_speech.py` - Original WebSocket speech implementation
- `ws_speech_real-time.py` - New implementation using OpenAI's Realtime API
- `prompts/system_prompts.py` - System prompts for different dialogue modes