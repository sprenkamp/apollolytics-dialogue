# backend/ws_speech_real-time.py
import asyncio
import base64
import json
import logging
import os
import uuid
import websockets
from typing import Dict, Any, List, Optional, AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
import uvicorn
import requests
import time

# Import the prompts system
from prompts.system_prompts import get_prompt

# Ensure the logs directory exists inside the working directory
os.makedirs("logs", exist_ok=True)

# Configure logging to save logs to logs/app.log file
logging.basicConfig(
    level=logging.INFO,
    filename="logs/app.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = "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"
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

REALTIME_MODEL = "gpt-4o-realtime-preview"
REALTIME_API_URL = "https://api.openai.com/v1/realtime/sessions"
PROPAGANDA_WS_URL = "ws://13.48.71.178:8000/ws/analyze_propaganda"

# Session storage
active_sessions = {}
conversation_sessions = {}  # For backward compatibility with existing frontend

def format_error(message: str) -> Dict[str, str]:
    return {"error": message}

def create_realtime_session() -> dict:
    """
    Create a new OpenAI Realtime API session
    """
    url = REALTIME_API_URL
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": REALTIME_MODEL,
        "modalities": ["audio", "text"],
        "voice": "alloy",  # Default voice
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "input_audio_transcription": {
            "model": "whisper-1"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error(f"Failed to create Realtime session: {response.text}")
        raise Exception(f"Failed to create Realtime session: {response.status_code}")
    
    return response.json()

async def detect_propaganda(input_article: str) -> Dict[str, Any]:
    """
    Connect to propaganda detection WebSocket and get analysis results
    """
    logger.info("Starting propaganda detection...")
    data = {
        "model_name": "gpt-4o-mini",
        "contextualize": True,
        "text": input_article
    }
    results: List[Dict[str, Any]] = []
    try:
        async with websockets.connect(PROPAGANDA_WS_URL) as websocket:
            logger.info("Connected to propaganda detection service")
            await websocket.send(json.dumps(data))
            async for message in websocket:
                try:
                    result = json.loads(message)
                    results.append(result)
                    logger.info("Received propaganda detection result")
                except json.JSONDecodeError:
                    logger.error("Received invalid JSON from propaganda service")
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"Propaganda service connection closed: {e}")
    
    logger.info("Propaganda detection completed")
    return results[-1] if results else {}

class RealtimeClient:
    """
    Client for interacting with OpenAI's Realtime API
    """
    def __init__(self, session_data: dict, client_ws: WebSocket):
        self.session_id = session_data["id"]
        self.client_secret = session_data["client_secret"]["value"]
        self.session_data = session_data
        self.client_ws = client_ws
        self.openai_ws = None
        self.running = True
        self.conversation_id = str(uuid.uuid4())
        
    async def connect(self):
        """Connect to OpenAI's Realtime WebSocket API"""
        url = f"wss://api.openai.com/v1/realtime/ws?session_id={self.session_id}&client_secret={self.client_secret}"
        logger.info(f"Connecting to OpenAI Realtime WS API")
        self.openai_ws = await websockets.connect(url)
        logger.info(f"Connected to OpenAI Realtime WS API")
        
        # Start message forwarding loops
        asyncio.create_task(self.forward_client_to_openai())
        asyncio.create_task(self.forward_openai_to_client())
        
    async def forward_client_to_openai(self):
        """Forward WebSocket messages from client to OpenAI"""
        try:
            while self.running:
                client_message = await self.client_ws.receive_json()
                
                # Map from our API format to OpenAI's API format
                if client_message.get("type") == "start":
                    # Initialize session with the article and specific instructions
                    article = client_message.get("article", "")
                    mode = client_message.get("mode", "critical")

                    # Get propaganda info
                    propaganda_result = await detect_propaganda(article)
                    propaganda_info = {
                        cat: [
                            {k: entry[k] for k in ['explanation', 'location', 'contextualize'] if k in entry}
                            for entry in entries
                        ]
                        for cat, entries in propaganda_result.get('data', {}).items()
                    }
                    
                    # Get the appropriate system prompt based on mode
                    system_prompt = get_prompt(mode, article, propaganda_info)
                    
                    # Update session instructions
                    update_message = {
                        "event_id": str(uuid.uuid4()),
                        "type": "session.update",
                        "session": {
                            "instructions": system_prompt
                        }
                    }
                    await self.openai_ws.send(json.dumps(update_message))
                    
                    # Create an initial response
                    response_message = {
                        "event_id": str(uuid.uuid4()),
                        "type": "response.create",
                        "response": {}
                    }
                    await self.openai_ws.send(json.dumps(response_message))
                    
                elif client_message.get("type") == "user":
                    # Handle audio input
                    if isinstance(client_message.get("content"), list):
                        for content_item in client_message.get("content", []):
                            if content_item.get("type") == "input_audio":
                                audio_info = content_item.get("input_audio")
                                if audio_info and audio_info.get("format") == "wav":
                                    audio_data = audio_info.get("data", "")
                                    
                                    # Append audio to buffer
                                    append_message = {
                                        "event_id": str(uuid.uuid4()),
                                        "type": "input_audio_buffer.append",
                                        "audio": audio_data
                                    }
                                    await self.openai_ws.send(json.dumps(append_message))
                                    
                                    # Commit the audio buffer
                                    commit_message = {
                                        "event_id": str(uuid.uuid4()),
                                        "type": "input_audio_buffer.commit"
                                    }
                                    await self.openai_ws.send(json.dumps(commit_message))
                                    
                                    # Create a response
                                    response_message = {
                                        "event_id": str(uuid.uuid4()),
                                        "type": "response.create",
                                        "response": {}
                                    }
                                    await self.openai_ws.send(json.dumps(response_message))
                    
                    # Handle text input (not used in current UI but implemented for completeness)
                    elif isinstance(client_message.get("content"), str):
                        text_input = client_message.get("content")
                        # Create a text message item
                        text_message = {
                            "event_id": str(uuid.uuid4()),
                            "type": "conversation.item.create",
                            "previous_item_id": None,  # Append to end of conversation
                            "item": {
                                "id": f"user_{uuid.uuid4()}",
                                "type": "message",
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": text_input
                                    }
                                ]
                            }
                        }
                        await self.openai_ws.send(json.dumps(text_message))
                        
                        # Create a response
                        response_message = {
                            "event_id": str(uuid.uuid4()),
                            "type": "response.create",
                            "response": {}
                        }
                        await self.openai_ws.send(json.dumps(response_message))
                
                else:
                    # Pass through any other message types
                    await self.openai_ws.send(json.dumps(client_message))
                    
        except WebSocketDisconnect:
            logger.info("Client disconnected")
            self.running = False
        except Exception as e:
            logger.exception(f"Error in forward_client_to_openai: {e}")
            self.running = False
    
    async def forward_openai_to_client(self):
        """Forward WebSocket messages from OpenAI to client with format translation"""
        pending_transcript = ""  # Accumulate transcript
        pending_audio_base64 = ""  # Accumulate audio
        current_response_id = None
        current_item_id = None
        
        try:
            while self.running:
                try:
                    openai_message_raw = await asyncio.wait_for(self.openai_ws.recv(), timeout=1.0)
                    openai_message = json.loads(openai_message_raw)
                    msg_type = openai_message.get("type")
                    
                    # Translate OpenAI's event format to our format
                    if msg_type == "response.created":
                        current_response_id = openai_message.get("response", {}).get("id")
                        # No direct mapping needed, just store the response ID
                    
                    elif msg_type == "response.output_item.added":
                        current_item_id = openai_message.get("item", {}).get("id")
                        # Clear any pending data for new item
                        pending_transcript = ""
                        pending_audio_base64 = ""
                        
                    elif msg_type == "response.audio_transcript.delta":
                        # Accumulate transcript delta
                        delta = openai_message.get("delta", "")
                        pending_transcript += delta
                        
                        # Send transcript update to client
                        await self.client_ws.send_json({
                            "type": "assistant_delta",
                            "payload": {
                                "text": delta
                            }
                        })
                        
                    elif msg_type == "response.audio.delta":
                        # Accumulate audio delta
                        audio_delta = openai_message.get("delta", "")
                        pending_audio_base64 += audio_delta
                        
                        # Only send the first chunk to start playing audio early
                        # This avoids sending too many audio chunks which can cause playback issues
                        if len(pending_audio_base64) > 0 and not pending_audio_base64.endswith("=="):
                            # Only send complete base64 chunks
                            await self.client_ws.send_json({
                                "type": "assistant_delta",
                                "payload": {
                                    "audio": pending_audio_base64
                                }
                            })
                            pending_audio_base64 = ""  # Clear after sending
                    
                    elif msg_type == "response.done":
                        # Audio done - send any remaining audio data
                        if pending_audio_base64:
                            await self.client_ws.send_json({
                                "type": "assistant_delta", 
                                "payload": {
                                    "audio": pending_audio_base64
                                }
                            })
                            
                        # Send final message with complete transcript
                        if pending_transcript:
                            await self.client_ws.send_json({
                                "type": "assistant_final",
                                "payload": {
                                    "text": pending_transcript,
                                    "id": current_item_id or f"assistant_{uuid.uuid4()}"
                                }
                            })
                            
                        # Reset state for next response
                        pending_transcript = ""
                        pending_audio_base64 = ""
                        current_response_id = None
                        current_item_id = None
                            
                    elif msg_type == "conversation.item.input_audio_transcription.completed":
                        # Send user transcript to client
                        transcript = openai_message.get("transcript", "")
                        await self.client_ws.send_json({
                            "type": "user_transcript",
                            "payload": {
                                "transcript": transcript,
                                "item_id": openai_message.get("item_id", f"user_{uuid.uuid4()}")
                            }
                        })
                    
                    elif msg_type == "error":
                        # Forward errors to client
                        error_details = openai_message.get("error", {})
                        logger.error(f"OpenAI API error: {error_details}")
                        await self.client_ws.send_json({
                            "type": "error",
                            "payload": {
                                "message": error_details.get("message", "Unknown error"),
                                "code": error_details.get("code", "unknown_error")
                            }
                        })
                        
                except asyncio.TimeoutError:
                    # Check if we should still be running
                    if not self.running:
                        break
                    continue
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI WS connection closed")
            self.running = False
        except Exception as e:
            logger.exception(f"Error in forward_openai_to_client: {e}")
            self.running = False
    
    async def close(self):
        """Close the connection"""
        self.running = False
        if self.openai_ws:
            await self.openai_ws.close()
        logger.info(f"Closed OpenAI Realtime connection for session {self.session_id}")

# FastAPI app setup
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/conversation")
async def realtime_conversation(websocket: WebSocket):
    """
    WebSocket endpoint for real-time conversation using OpenAI's Realtime API
    """
    try:
        await websocket.accept()
        session_id = str(uuid.uuid4())
        logger.info(f"New conversation session started: {session_id}")
        
        # Create a Realtime API session
        session_data = create_realtime_session()
        logger.info(f"Created Realtime session: {session_data['id']}")
        
        # Store the session
        active_sessions[session_id] = session_data
        conversation_sessions[session_id] = {"conversation": []}
        
        # Create and connect client
        client = RealtimeClient(session_data, websocket)
        await client.connect()
        
        # Keep the connection open until the client disconnects
        try:
            while True:
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            logger.info(f"Client disconnected from session {session_id}")
        except Exception as e:
            logger.exception(f"Error during conversation: {e}")
            await websocket.send_json(format_error(str(e)))
            
    except Exception as e:
        logger.exception(f"Error during WebSocket connection: {e}")
        if not websocket.client_state == WebSocketState.DISCONNECTED:
            await websocket.close(code=1011)
    finally:
        # Clean up
        if session_id in active_sessions:
            client = active_sessions.pop(session_id, None)
            if client and hasattr(client, 'close'):
                await client.close()
                
        if session_id in conversation_sessions:
            del conversation_sessions[session_id]

if __name__ == "__main__":
    logger.info("Starting real-time speech server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)