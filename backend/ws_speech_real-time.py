# backend/app.py
import asyncio
import base64
import io
import json
import logging
import os
import uuid
import wave
from typing import Dict, Any, List, AsyncGenerator

import websockets
from fastapi import FastAPI, Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from openai import OpenAI

# Optionally install and import pydub (requires ffmpeg installed)
from pydub import AudioSegment

# Ensure the logs directory exists inside the working directory (/app/logs)
os.makedirs("logs", exist_ok=True)

# Configure logging to save logs to logs/app.log file
logging.basicConfig(
    level=logging.DEBUG,
    filename="logs/app.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

client = OpenAI()

conversation_sessions: Dict[str, dict] = {}
PROPAGANDA_WS_URL = "ws://13.48.71.178:8000/ws/analyze_propaganda"

def format_error(message: str) -> Dict[str, str]:
    return {"error": message}

def is_valid_wav(audio_base64: str) -> bool:
    try:
        audio_bytes = base64.b64decode(audio_base64)
        with io.BytesIO(audio_bytes) as audio_file:
            with wave.open(audio_file, 'rb') as wav_file:
                wav_file.getparams()
        logger.debug("Audio is valid WAV.")
        return True
    except Exception as e:
        logger.debug("Audio is not a valid WAV: %s", e)
        return False

def ensure_valid_wav(audio_base64: str) -> str:
    """
    Checks if the provided base64 audio is a valid WAV file.
    If not, it tries to convert the audio (detecting if it is a WebM file)
    using pydub and returns a valid WAV file as base64.
    """
    logger.info("Ensuring audio is a valid WAV.")
    audio_bytes = base64.b64decode(audio_base64)
    # First try to validate as WAV
    try:
        with io.BytesIO(audio_bytes) as audio_file:
            with wave.open(audio_file, 'rb') as wav_file:
                wav_file.getparams()
        logger.info("Audio validated as WAV without conversion.")
        return audio_base64
    except wave.Error as we:
        logger.debug("Initial WAV validation failed: %s", we)

    # If that fails, attempt to convert. Check if the file is actually a WebM file.
    try:
        if audio_bytes.startswith(b'\x1A\x45\xDF\xA3'):
            logger.info("Audio appears to be WebM format. Converting to WAV.")
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
        else:
            logger.info("Audio format not identified; trying auto-detect conversion.")
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        valid_bytes = buf.getvalue()
        logger.info("Audio conversion to WAV successful.")
        return base64.b64encode(valid_bytes).decode('utf-8')
    except Exception as e:
        logger.exception("Failed to convert audio to valid WAV")
        raise ValueError("Conversion to valid WAV failed") from e

async def detect_propaganda(input_article: str) -> Dict[str, Any]:
    logger.info("Starting propaganda detection for the article.")
    data = {
        "model_name": "gpt-4o-mini",
        "contextualize": True,
        "text": input_article
    }
    results: List[Dict[str, Any]] = []
    try:
        async with websockets.connect(PROPAGANDA_WS_URL) as websocket:
            logger.info("Connected to propaganda detection WebSocket.")
            await websocket.send(json.dumps(data))
            async for message in websocket:
                try:
                    result = json.loads(message)
                    results.append(result)
                    logger.debug("Received propaganda result: %s", result)
                except json.JSONDecodeError:
                    logger.error("Received invalid JSON message: %s", message)
    except websockets.exceptions.ConnectionClosed as e:
        logger.error("Propaganda WebSocket connection closed: %s", e)
    logger.info("Propaganda detection completed with %d results.", len(results))
    return results[-1] if results else {}

async def chat_completion_streaming(messages: list) -> AsyncGenerator[Dict[str, Any], None]:
    def blocking_stream():
        logger.info("Calling chat completion API with %d messages.", len(messages))
        completion = client.chat.completions.create(
            model="gpt-4o-audio-preview",
            modalities=["text", "audio"],
            audio={"voice": "alloy", "format": "wav"},
            messages=messages
        )
        transcript = completion.choices[0].message.audio.transcript
        audio_data = completion.choices[0].message.audio.data
        audio_id = completion.choices[0].message.audio.id
        chunk_size = 20
        text_chunks = [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size)]
        logger.info("Chat completion returned transcript of length %d.", len(transcript))
        return {"text_chunks": text_chunks, "audio": audio_data, "audio_id": audio_id}
    
    stream_data = await asyncio.to_thread(blocking_stream)
    for chunk in stream_data["text_chunks"]:
        yield {"text": chunk}
        await asyncio.sleep(0.1)
    yield {"audio": stream_data["audio"], "audio_id": stream_data["audio_id"]}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/conversation")
async def realtime_conversation(websocket: WebSocket):
    logger.info("WebSocket connection initiated.")
    await websocket.accept()
    
    session_id = websocket.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info("No session_id found; generated new session_id: %s", session_id)
    conversation_sessions[session_id] = {"conversation": []}
    messages = conversation_sessions[session_id]["conversation"]
    
    try:
        init_msg = await websocket.receive_json()
        logger.debug("Received initial message: %s", init_msg)
        if init_msg.get("type") != "start":
            await websocket.send_json(format_error("Expected 'start' message with article"))
            return
        article = init_msg.get("article", "")
        if not article:
            await websocket.send_json(format_error("Article not provided."))
            return
        
        propaganda_info = await detect_propaganda(article)
        propaganda_info = {
            cat: [
                {k: entry[k] for k in ['explanation', 'location', 'contextualize'] if k in entry}
                for entry in entries
            ]
            for cat, entries in propaganda_info.get('data', {}).items()
        }
        logger.info("Constructing system prompt.")
        system_prompt = f'''**PERSONA**: Socratic Dialogue with Informative Support

**Description**: Engage the user in thoughtful conversations that promote critical thinking. 
Begin the dialogue with an open-ended question about the topic. In subsequent responses, if possible, 
debunk the user's input using facts, and end with a follow-up question. Debate any viewpoint of the article that user gives to you, 
focusing on the ARTICLE at hand. Use the detected propaganda to guide the conversation and challenge the user's assumptions. 
Also use your own knowledge on historical events and answer in a detailed manner.

**ARTICLE**: PLEASE ARGUE AGAINST THE ARTICLE BELOW
{article}

**DETECTED PROPAGANDA**: USE THIS INFORMATION TO GUIDE YOUR ARGUMENTATION
{propaganda_info} needed to be formatted properly

Engage in a thoughtful dialogue'''
        
        messages.append({"role": "system", "content": system_prompt})
        initial_user_message = "Please start the conversation."
        messages.append({"role": "user", "content": [{"type": "text", "text": initial_user_message}]})
        
        logger.info("Streaming initial assistant response.")
        async for delta in chat_completion_streaming(messages):
            await websocket.send_json({"type": "assistant_delta", "payload": delta})
        await websocket.send_json({"type": "assistant_final", "payload": "Initial response complete."})
        
        while True:
            user_msg = await websocket.receive_json()
            logger.debug("Received user message: %s", user_msg)
            if user_msg.get("type") != "user":
                await websocket.send_json(format_error("Invalid message type. Expected 'user'."))
                continue
            user_content = user_msg.get("content")
            if not user_content:
                await websocket.send_json(format_error("No content provided in user message."))
                continue
            
            # Process any audio content: convert to a valid WAV if necessary.
            if isinstance(user_content, list):
                for content_item in user_content:
                    if content_item.get("type") == "input_audio":
                        audio_info = content_item.get("input_audio")
                        if audio_info and audio_info.get("format") == "wav":
                            try:
                                data = audio_info.get("data")
                                logger.info("Converting audio data to valid WAV if needed.")
                                audio_info["data"] = ensure_valid_wav(data)
                            except ValueError as e:
                                logger.error("Audio conversion failed: %s", e)
                                await websocket.send_json(format_error(str(e)))
                                continue
            
            messages.append({"role": "user", "content": user_content})
            logger.info("Appended user message to conversation. Total messages: %d", len(messages))
            
            async for delta in chat_completion_streaming(messages):
                await websocket.send_json({"type": "assistant_delta", "payload": delta})
            await websocket.send_json({"type": "assistant_final", "payload": "Response complete."})
    
    except Exception as e:
        logger.exception("Error during realtime conversation")
        await websocket.send_json(format_error(str(e)))

if __name__ == "__main__":
    logger.info("Starting server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
