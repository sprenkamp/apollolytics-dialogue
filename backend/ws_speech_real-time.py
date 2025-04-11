# backend/ws_speech_real-time.py
import asyncio
import base64
import json
import logging
import os
import uuid
import websockets
import pyaudio
import queue
import threading
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
import uvicorn
import requests
import time
from datetime import datetime
from pathlib import Path

# Import the prompts system
from prompts.system_prompts import get_prompt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backend.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
Path('logs').mkdir(exist_ok=True)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

WS_URL = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01'
PROPAGANDA_WS_URL = "ws://13.48.71.178:8000/ws/analyze_propaganda"

# Session storage
active_sessions = {}
conversation_sessions = {}  # For backward compatibility with existing frontend

# Audio configuration
CHUNK_SIZE = 1024
RATE = 24000
FORMAT = pyaudio.paInt16

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

# Store conversation states
conversation_states: Dict[str, Dict] = {}

class AudioManager:
    def __init__(self):
        self.audio_buffer = bytearray()
        self.mic_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.mic_on_at = 0
        self.mic_active = None
        self.REENGAGE_DELAY_MS = 500
        self.MIN_AUDIO_DURATION_MS = 100  # Minimum audio duration required by OpenAI
        self.SAMPLE_RATE = 24000  # Required sample rate by OpenAI
        self.CHANNELS = 1  # Mono audio required by OpenAI
        self.SAMPLE_WIDTH = 2  # 16-bit PCM
        self.CHUNK_SIZE = 1024
        logger.info("AudioManager initialized")

    def clear_audio_buffer(self):
        self.audio_buffer = bytearray()
        logger.info('Audio buffer cleared')

    def mic_callback(self, in_data, frame_count, time_info, status):
        if self.mic_active != True:
            logger.info('Mic active')
            self.mic_active = True
        self.mic_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def speaker_callback(self, in_data, frame_count, time_info, status):
        bytes_needed = frame_count * 2
        current_buffer_size = len(self.audio_buffer)

        if current_buffer_size >= bytes_needed:
            audio_chunk = bytes(self.audio_buffer[:bytes_needed])
            self.audio_buffer = self.audio_buffer[bytes_needed:]
            self.mic_on_at = time.time() + self.REENGAGE_DELAY_MS / 1000
        else:
            audio_chunk = bytes(self.audio_buffer) + b'\x00' * (bytes_needed - current_buffer_size)
            self.audio_buffer.clear()

        return (audio_chunk, pyaudio.paContinue)

    def get_audio_duration_ms(self):
        """Calculate the duration of the current audio buffer in milliseconds"""
        bytes_per_sample = self.SAMPLE_WIDTH * self.CHANNELS
        samples = len(self.audio_buffer) // bytes_per_sample
        return (samples / self.SAMPLE_RATE) * 1000

async def detect_propaganda(input_article: str) -> Dict[str, Any]:
    """
    Connect to propaganda detection WebSocket and get analysis results
    """
    logger.info(f"Starting propaganda detection for article: {input_article[:100]}...")
    data = {
        "model_name": "gpt-4o-mini",
        "contextualize": True,
        "text": input_article
    }
    results: List[Dict[str, Any]] = []
    try:
        logger.info(f"Attempting to connect to propaganda service at {PROPAGANDA_WS_URL}")
        async with websockets.connect(PROPAGANDA_WS_URL) as websocket:
            logger.info("Connected to propaganda detection service")
            await websocket.send(json.dumps(data))
            logger.info("Sent data to propaganda service")
            async for message in websocket:
                try:
                    result = json.loads(message)
                    results.append(result)
                    logger.info("Received propaganda detection result")
                except json.JSONDecodeError:
                    logger.error("Received invalid JSON from propaganda service")
    except Exception as e:
        logger.error(f"Error connecting to propaganda service: {e}")
        return {}
    
    logger.info("Propaganda detection completed")
    return results[-1] if results else {}

class RealtimeClient:
    def __init__(self, session_id: str, client_ws: WebSocket):
        self.session_id = session_id
        self.client_ws = client_ws
        self.openai_ws = None
        self.audio_manager = AudioManager()
        self.stop_event = threading.Event()
        self.running = True
        self.conversation_id = str(uuid.uuid4())
        self.mic_on_at = 0
        self.REENGAGE_DELAY_MS = 500
        self._lock = asyncio.Lock()
        self._forwarding_tasks = []
        logger.info(f"RealtimeClient initialized for session {session_id}")

    async def stop(self):
        """Stop all operations and close connections"""
        async with self._lock:
            if not self.running:
                return
            self.running = False
            logger.info(f"Stopping RealtimeClient for session {self.session_id}")
            
            # Cancel all forwarding tasks
            for task in self._forwarding_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            if self.openai_ws:
                try:
                    await self.openai_ws.close()
                except Exception as e:
                    logger.error(f"Error closing OpenAI WS in session {self.session_id}: {e}")
            
            try:
                if self.client_ws.client_state != WebSocketState.DISCONNECTED:
                    await self.client_ws.close()
            except Exception as e:
                logger.error(f"Error closing client WS in session {self.session_id}: {e}")

    async def connect(self):
        """Connect to OpenAI's Realtime WebSocket API"""
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
            "openai-beta": "realtime=v1"
        }
        logger.info(f"Connecting to OpenAI Realtime WS API for session {self.session_id}")
        try:
            self.openai_ws = await websockets.connect(WS_URL, extra_headers=headers)
            logger.info(f"Connected to OpenAI Realtime WS API for session {self.session_id}")
            
            # Store the session
            active_sessions[self.session_id] = self
            conversation_sessions[self.session_id] = {"conversation": []}
            logger.info(f"Session {self.session_id} stored in active sessions")
            
            # Start message forwarding loops
            self._forwarding_tasks = [
                asyncio.create_task(self.forward_client_to_openai()),
                asyncio.create_task(self.forward_openai_to_client())
            ]
            logger.info(f"Message forwarding loops started for session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to connect to OpenAI WS API for session {self.session_id}: {e}")
            await self.stop()
            raise

    async def forward_client_to_openai(self):
        try:
            while self.running:
                try:
                    if not self.running or self.client_ws.client_state == WebSocketState.DISCONNECTED:
                        break
                        
                    client_message = await self.client_ws.receive_json()
                    if not self.running:
                        break
                        
                    if client_message.get("type") == "start":
                        article = client_message.get("article", "")
                        mode = client_message.get("mode", "critical")
                        logger.info(f"Starting new conversation in session {self.session_id} with mode: {mode}")

                        # Get propaganda info
                        propaganda_result = await detect_propaganda(article)
                        logger.info(f"Propaganda analysis completed for session {self.session_id}")
                        
                        # Get the appropriate system prompt based on mode
                        system_prompt = get_prompt(mode, article, propaganda_result)
                        logger.info(f"System prompt generated for session {self.session_id}")

                        # Send session configuration
                        session_config = {
                            "type": "session.update",
                            "session": {
                                "instructions": system_prompt,
                                "turn_detection": {
                                    "type": "server_vad",
                                    "threshold": 0.5,
                                    "prefix_padding_ms": 300,
                                    "silence_duration_ms": 500
                                },
                                "voice": "alloy",
                                "temperature": 1,
                                "modalities": ["text", "audio"],
                                "input_audio_format": "pcm16",
                                "output_audio_format": "pcm16",
                                "input_audio_transcription": {
                                    "model": "whisper-1"
                                }
                            }
                        }
                        await self.openai_ws.send(json.dumps(session_config))
                        logger.info(f"Session configuration sent for session {self.session_id}")

                        # Create an initial response
                        response_message = {
                            "event_id": str(uuid.uuid4()),
                            "type": "response.create",
                            "response": {}
                        }
                        await self.openai_ws.send(json.dumps(response_message))
                        logger.info(f"Initial response created for session {self.session_id}")

                    elif client_message.get("type") == "user":
                        # Handle audio input
                        if isinstance(client_message.get("content"), list):
                            for content_item in client_message.get("content", []):
                                if content_item.get("type") == "input_audio":
                                    audio_info = content_item.get("input_audio")
                                    if audio_info and audio_info.get("data"):
                                        # User started speaking - clear AI audio buffer
                                        self.audio_manager.clear_audio_buffer()
                                        self.mic_on_at = time.time() + self.REENGAGE_DELAY_MS / 1000
                                        
                                        # Append audio to buffer
                                        append_message = {
                                            "event_id": str(uuid.uuid4()),
                                            "type": "input_audio_buffer.append",
                                            "audio": audio_info.get("data")
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
                                        
                                        logger.info(f"Audio message processed in session {self.session_id}")
                        
                        elif isinstance(client_message.get("content"), str):
                            text_input = client_message.get("content")
                            logger.info(f"Received text input in session {self.session_id}: {text_input[:100]}...")
                            text_message = {
                                "event_id": str(uuid.uuid4()),
                                "type": "conversation.item.create",
                                "item": {
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
                            logger.info(f"Text message sent for session {self.session_id}")
                            
                            # Create a response
                            response_message = {
                                "event_id": str(uuid.uuid4()),
                                "type": "response.create",
                                "response": {}
                            }
                            await self.openai_ws.send(json.dumps(response_message))
                            logger.info(f"Response created for text input in session {self.session_id}")
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"Client WS connection closed for session {self.session_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in forward_client_to_openai for session {self.session_id}: {e}")
                    if not self.running:
                        break
                    continue

        except Exception as e:
            logger.error(f"Error in forward_client_to_openai for session {self.session_id}: {e}")
        finally:
            await self.stop()

    async def forward_openai_to_client(self):
        try:
            while self.running:
                try:
                    if not self.running or self.client_ws.client_state == WebSocketState.DISCONNECTED:
                        break
                        
                    openai_message = await self.openai_ws.recv()
                    if not openai_message:
                        logger.info(f"Received empty message from OpenAI in session {self.session_id}")
                        break

                    if not self.running:
                        break
                        
                    message = json.loads(openai_message)
                    event_type = message.get("type")
                    logger.info(f"Received WebSocket event in session {self.session_id}: {event_type}")

                    if event_type == "response.audio.delta":
                        # Check if user is speaking
                        if time.time() < self.mic_on_at:
                            logger.info("Skipping AI audio while user is speaking")
                            continue
                            
                        audio_content = base64.b64decode(message["delta"])
                        self.audio_manager.audio_buffer.extend(audio_content)
                        await self.client_ws.send_json({
                            "type": "assistant_delta",
                            "payload": {
                                "audio": message["delta"]
                            }
                        })
                        logger.info(f"Audio delta sent to client in session {self.session_id}")

                    elif event_type == "response.audio_transcript.delta":
                        delta = message.get("delta", "")
                        await self.client_ws.send_json({
                            "type": "assistant_delta",
                            "payload": {
                                "text": delta
                            }
                        })
                        logger.info(f"Transcript delta sent to client in session {self.session_id}: {delta[:100]}...")

                    elif event_type == "response.done":
                        await self.client_ws.send_json({
                            "type": "assistant_final",
                            "payload": {
                                "id": str(uuid.uuid4())
                            }
                        })
                        logger.info(f"Response completed in session {self.session_id}")

                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        transcript = message.get("transcript", "")
                        await self.client_ws.send_json({
                            "type": "user_transcript",
                            "payload": {
                                "transcript": transcript,
                                "item_id": message.get("item_id", f"user_{uuid.uuid4()}")
                            }
                        })
                        logger.info(f"User transcript sent in session {self.session_id}: {transcript[:100]}...")

                    elif event_type == "error":
                        error_details = message.get("error", {})
                        logger.error(f"OpenAI API error in session {self.session_id}: {error_details}")
                        await self.client_ws.send_json({
                            "type": "error",
                            "payload": {
                                "message": error_details.get("message", "Unknown error"),
                                "code": error_details.get("code", "unknown_error")
                            }
                        })

                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"OpenAI WS connection closed for session {self.session_id}")
                    break
                except Exception as e:
                    logger.exception(f"Error in forward_openai_to_client for session {self.session_id}: {e}")
                    if not self.running:
                        break
                    continue

        except Exception as e:
            logger.exception(f"Error in forward_openai_to_client for session {self.session_id}: {e}")
        finally:
            await self.stop()

    async def close(self):
        """Close the connection"""
        await self.stop()
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
    session_id = None
    client = None
    try:
        await websocket.accept()
        session_id = str(uuid.uuid4())
        logger.info(f"New conversation session started: {session_id}")
        
        # Create and connect client
        client = RealtimeClient(session_id, websocket)
        await client.connect()
        
        # Keep the connection open until the client disconnects
        while True:
            try:
                # Check if the client is still connected
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    logger.info(f"Client disconnected from session {session_id}")
                    break
                    
                # Check if the client is still running
                if not client.running:
                    logger.info(f"Client stopped running in session {session_id}")
                    break
                    
                await asyncio.sleep(1)
            except WebSocketDisconnect:
                logger.info(f"Client disconnected from session {session_id}")
                break
            except Exception as e:
                logger.exception(f"Error during conversation in session {session_id}: {e}")
                if websocket.client_state != WebSocketState.DISCONNECTED:
                    await websocket.send_json({"error": str(e)})
                break
            
    except Exception as e:
        logger.exception(f"Error during WebSocket connection: {e}")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011)
    finally:
        # Clean up
        if session_id:
            if client and hasattr(client, 'close'):
                try:
                    await client.close()
                except Exception as e:
                    logger.error(f"Error closing client in session {session_id}: {e}")
            
            if session_id in active_sessions:
                try:
                    del active_sessions[session_id]
                except Exception as e:
                    logger.error(f"Error removing session {session_id} from active_sessions: {e}")
                    
            if session_id in conversation_sessions:
                try:
                    del conversation_sessions[session_id]
                except Exception as e:
                    logger.error(f"Error removing session {session_id} from conversation_sessions: {e}")
                    
            logger.info(f"Session {session_id} cleaned up")

@app.post("/log")
async def log_frontend(log_data: Dict[str, Any]):
    """Endpoint to receive and store frontend logs"""
    try:
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": log_data.get("level", "INFO"),
            "message": log_data.get("message", ""),
            "data": log_data.get("data", None)
        }
        
        # Write to frontend log file
        log_file = "logs/frontend.log"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error logging frontend message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("Starting real-time speech server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)