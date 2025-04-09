import asyncio
import json
import os
import websockets
import base64
import uuid
import logging
import httpx

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Hardcoded API key
OPENAI_API_KEY = "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"

async def test_realtime_api():
    # Connect directly to WebSocket without creating a session
    ws_url = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01'
    logging.debug(f"Connecting to WebSocket URL: {ws_url}")
    
    try:
        headers = {
            'Authorization': f'Bearer {OPENAI_API_KEY}',
            'openai-beta': 'realtime=v1'
        }
        async with websockets.connect(ws_url, extra_headers=headers) as websocket:
            logger.info("Connected to WebSocket")
            
            # Update session with instructions
            update_message = {
                "event_id": str(uuid.uuid4()),
                "type": "session.update",
                "session": {
                    "instructions": "You are a helpful assistant. Keep your responses brief and to the point."
                }
            }
            await websocket.send(json.dumps(update_message))
            logger.info("Sent session update")
            
            # Create a text message
            text_message = {
                "event_id": str(uuid.uuid4()),
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Hello! Can you hear me?"
                        }
                    ]
                }
            }
            await websocket.send(json.dumps(text_message))
            logger.info("Sent text message")
            
            # Request a response
            response_message = {
                "event_id": str(uuid.uuid4()),
                "type": "response.create",
                "response": {}
            }
            await websocket.send(json.dumps(response_message))
            logger.info("Requested response")
            
            # Listen for responses
            try:
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    logger.info(f"Received event: {data}")
                    
                    if data["type"] == "response.done":
                        logger.info("Response completed")
                        break
                        
            except websockets.exceptions.ConnectionClosed as e:
                logger.error(f"Connection closed unexpectedly: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_realtime_api()) 