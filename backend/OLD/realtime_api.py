# backend/realtime_api.py
import asyncio
import json
import logging
import os
import uuid
import websockets
import requests
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger("realtime_api")

class RealtimeSession:
    """
    Class to handle interactions with OpenAI's Realtime API
    """
    def __init__(self, client_ws, system_instructions: str):
        """
        Initialize a new Realtime Session
        
        Args:
            client_ws: The WebSocket connection with the client
            system_instructions: The system instructions to use for the session
        """
        self.client_ws = client_ws
        self.system_instructions = system_instructions
        self.session_data = None
        self.openai_ws = None
        self.session_id = str(uuid.uuid4())
        self.running = False
        
    async def create_session(self) -> Dict[str, Any]:
        """Create a new session with OpenAI's Realtime API"""
        logger.info(f"Creating new Realtime session with instructions: {self.system_instructions[:100]}...")
        
        api_key = "sk-eg29kkProhQ3KE6DGT-DOvGEJcHOBF3nUejOFFdKakT3BlbkFJUTCBsV6rl0DohALwImlDXYDqFe0PqEwZgyViCvDJcA"
        
        # If API key not found, try loading from .env file
        if not api_key:
            try:
                import dotenv
                env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
                dotenv.load_dotenv(env_path)
                api_key = "sk-eg29kkProhQ3KE6DGT-DOvGEJcHOBF3nUejOFFdKakT3BlbkFJUTCBsV6rl0DohALwImlDXYDqFe0PqEwZgyViCvDJcA"
                logger.info("Loaded API key from .env file")
            except Exception as e:
                logger.error(f"Failed to load .env file: {e}")
                
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4o-mini",  # Or another model that supports Realtime API
            "modalities": ["audio", "text"],
            "instructions": self.system_instructions,
            "voice": "alloy",
            "input_audio_transcription": {
                "model": "whisper-1",
                "language": "en"
            }
        }
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            self.session_data = response.json()
            logger.info(f"Successfully created Realtime session: {self.session_data.get('id')}")
            return self.session_data
        except Exception as e:
            logger.error(f"Failed to create Realtime session: {e}")
            raise
    
    async def connect_to_openai(self) -> None:
        """Connect to OpenAI's Realtime API WebSocket"""
        if not self.session_data:
            raise ValueError("Session data not available. Create a session first.")
        
        client_secret = self.session_data.get("client_secret", {}).get("value")
        if not client_secret:
            raise ValueError("Client secret not found in session data")
        
        # Connect to the websocket
        ws_uri = f"wss://api.openai.com/v1/realtime/{self.session_data['id']}"
        try:
            # Check if we're using a project key (which doesn't work with Realtime API)
            api_key = "sk-eg29kkProhQ3KE6DGT-DOvGEJcHOBF3nUejOFFdKakT3BlbkFJUTCBsV6rl0DohALwImlDXYDqFe0PqEwZgyViCvDJcA"
            if api_key.startswith("sk-proj-"):
                raise ValueError("Project-level API keys (starting with 'sk-proj-') cannot be used with the Realtime API. Please use a standard API key.")
            
            self.openai_ws = await websockets.connect(
                ws_uri,
                extra_headers={"Authorization": f"Bearer {client_secret}"}
            )
            logger.info(f"Connected to OpenAI Realtime websocket for session {self.session_data['id']}")
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 403:
                logger.error(f"403 Forbidden error connecting to Realtime API. Your API key may not have access to the Realtime API.")
                raise ValueError("403 Forbidden: Your API key doesn't have access to the Realtime API. Make sure you're using a standard API key, not a project key.")
            raise
    
    async def start_conversation(self, article: str) -> None:
        """Start the conversation with the given article"""
        # Create a session
        await self.create_session()
        
        # Connect to OpenAI websocket
        await self.connect_to_openai()
        
        # Start the message forwarding loops
        self.running = True
        await asyncio.gather(
            self.forward_client_to_openai(article),
            self.forward_openai_to_client()
        )
    
    async def forward_client_to_openai(self, article: str) -> None:
        """Forward messages from client to OpenAI"""
        try:
            # Send an initial message to initiate the conversation
            initial_message = {
                "type": "message.create",
                "data": {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Let's discuss this article: {article}"
                        }
                    ]
                }
            }
            await self.openai_ws.send(json.dumps(initial_message))
            logger.info(f"Sent initial message to OpenAI: {initial_message['data']['content'][0]['text'][:50]}...")
            
            # Forward messages from client to OpenAI
            while self.running:
                try:
                    message = await self.client_ws.receive_json()
                    logger.debug(f"Received from client: {message}")
                    
                    if message.get("type") == "user":
                        # Handle audio content - needs special formatting for Realtime API
                        content = message.get("content", [])
                        
                        # Transform content for Realtime API
                        realtime_content = []
                        for item in content:
                            if item.get("type") == "input_audio":
                                audio_info = item.get("input_audio", {})
                                # Format for Realtime API
                                realtime_content.append({
                                    "type": "audio",
                                    "data": audio_info.get("data"),
                                    "format": audio_info.get("format", "wav")
                                })
                            elif item.get("type") == "text":
                                realtime_content.append({
                                    "type": "text",
                                    "text": item.get("text", "")
                                })
                        
                        # Create the Realtime API message
                        openai_message = {
                            "type": "message.create",
                            "data": {
                                "role": "user",
                                "content": realtime_content or [{"type": "text", "text": "Continue"}]
                            }
                        }
                        
                        await self.openai_ws.send(json.dumps(openai_message))
                        logger.info(f"Forwarded message to OpenAI: {openai_message}")
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"Client WebSocket connection closed")
                    self.running = False
                    break
                    
        except Exception as e:
            logger.exception(f"Error in client-to-OpenAI forwarding: {e}")
            self.running = False
    
    async def forward_openai_to_client(self) -> None:
        """Forward messages from OpenAI to client"""
        try:
            while self.running:
                try:
                    message = await self.openai_ws.recv()
                    data = json.loads(message)
                    logger.debug(f"Received from OpenAI: {data}")
                    
                    # Process based on message type
                    if data.get("type") == "message.chunk":
                        # Handle message delta chunks (text streaming)
                        delta_content = data.get("delta", {}).get("content", [])
                        for content in delta_content:
                            if content.get("type") == "text":
                                text = content.get("text", "")
                                if text.strip():  # Only send non-empty text chunks
                                    # Log the chunk for debugging
                                    logger.debug(f"Sending assistant delta text: '{text}'")
                                    await self.client_ws.send_json({
                                        "type": "assistant_delta",
                                        "payload": {"text": text}
                                    })
                    
                    elif data.get("type") == "message.complete":
                        # Handle message completion
                        content = data.get("message", {}).get("content", [])
                        text_content = ""
                        for item in content:
                            if item.get("type") == "text":
                                text_content += item.get("text", "")
                        
                        # Log the complete text for debugging
                        logger.info(f"Complete assistant message: '{text_content[:100]}...'")
                        
                        # Send the complete message to signal the end of streaming
                        await self.client_ws.send_json({
                            "type": "assistant_final",
                            "payload": {"text": text_content, "id": data.get("message", {}).get("id")}
                        })
                    
                    elif data.get("type") == "audio.complete":
                        # Handle audio completion
                        audio_data = data.get("audio", {}).get("data")
                        if audio_data:
                            await self.client_ws.send_json({
                                "type": "assistant_delta",
                                "payload": {"audio": audio_data}
                            })
                    
                    elif data.get("type") == "conversation.item.input_audio_transcription.completed":
                        # Handle transcription completion - this is what we want for the transcript feature!
                        transcript = data.get("transcript", "")
                        item_id = data.get("item_id", "")
                        
                        # Looking at the frontend DialogueChat.js, we should either use:
                        # 1. "user_transcript" with payload.transcript (current implementation)
                        # OR
                        # 2. The exact same event type with payload.transcript 
                        
                        # Send this to client for display
                        await self.client_ws.send_json({
                            "type": "user_transcript",
                            "payload": {
                                "transcript": transcript,
                                "text": transcript,  # Adding text for compatibility with frontend handler
                                "item_id": item_id,
                                "event_id": data.get("event_id", str(uuid.uuid4()))
                            }
                        })
                        
                        # Also send in the format the frontend might be expecting
                        await self.client_ws.send_json({
                            "type": "conversation.item.input_audio_transcription.completed",
                            "payload": {
                                "transcript": transcript,
                                "item_id": item_id
                            }
                        })
                        
                        logger.info(f"Sent transcript to client: {transcript[:50]}...")
                
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"OpenAI WebSocket connection closed")
                    self.running = False
                    break
                
        except Exception as e:
            logger.exception(f"Error in OpenAI-to-client forwarding: {e}")
            self.running = False
    
    async def close(self) -> None:
        """Close the session and all connections"""
        self.running = False
        if self.openai_ws:
            await self.openai_ws.close()
        logger.info(f"Closed Realtime session: {self.session_id}")