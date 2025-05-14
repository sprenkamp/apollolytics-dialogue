# backend/app.py
import asyncio
import base64
import io
import json
import logging
import os
import sys
import time
import uuid
import wave
from typing import Dict, Any, List, AsyncGenerator

import websockets
from fastapi import FastAPI, Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from openai import OpenAI

# Import the prompts system
from backend.prompts.system_prompts import get_prompt

# Import DynamoDB utilities
from backend.db_utils.dialogue_db import (
    initialize_db,
    save_session_init,
    save_propaganda_analysis,
    save_message,
    save_session_end
)

# Optionally install and import pydub (requires ffmpeg installed)
from pydub import AudioSegment

# Ensure the logs directory exists inside the working directory (/app/logs)
os.makedirs("logs", exist_ok=True)

# Configure logging to save logs to both file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log", mode="a"),
        logging.StreamHandler()  # This will print to console
    ]
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
        return True
    except Exception as e:
        logger.info("Invalid WAV format detected")
        return False

def ensure_valid_wav(audio_base64: str) -> str:
    """
    Checks if the provided base64 audio is a valid WAV file.
    If not, it tries to convert the audio (detecting if it is a WebM file)
    using pydub and returns a valid WAV file as base64.
    """
    logger.info("Processing audio input...")
    audio_bytes = base64.b64decode(audio_base64)
    # First try to validate as WAV
    try:
        with io.BytesIO(audio_bytes) as audio_file:
            with wave.open(audio_file, 'rb') as wav_file:
                wav_file.getparams()
        logger.info("Audio is valid WAV format")
        return audio_base64
    except wave.Error:
        logger.info("Audio is not in valid WAV format, attempting conversion")

    # If that fails, attempt to convert. Check if the file is actually a WebM file.
    try:
        if audio_bytes.startswith(b'\x1A\x45\xDF\xA3'):
            logger.info("Converting WebM format to WAV")
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
        else:
            logger.info("Converting unknown format to WAV")
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        valid_bytes = buf.getvalue()
        logger.info("Audio conversion successful")
        return base64.b64encode(valid_bytes).decode('utf-8')
    except Exception as e:
        logger.error("Audio conversion failed: %s", str(e).split('\n')[0])
        raise ValueError("Audio conversion failed") from e

async def detect_propaganda(input_article: str) -> Dict[str, Any]:
    logger.info("Starting propaganda detection...")
    data = {
        "model_name": "gpt-4o",
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
        logger.error("Propaganda service connection closed")
    
    logger.info("Propaganda detection completed")
    return results[-1] if results else {}

async def chat_completion_streaming(messages: list) -> AsyncGenerator[Dict[str, Any], None]:
    start_time = time.time()
    def blocking_stream():
        logger.info("Generating assistant response...")
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
        logger.info("ASSISTANT: %s", transcript)
        return {
            "text_chunks": text_chunks, 
            "audio": audio_data, 
            "audio_id": audio_id,
            "full_transcript": transcript
        }
    
    stream_data = await asyncio.to_thread(blocking_stream)
    
    # Store accumulated text for the transcript
    accumulated_text = ""
    
    # Stream text in chunks for smooth UI experience
    for chunk in stream_data["text_chunks"]:
        accumulated_text += chunk
        yield {"text": chunk}
        await asyncio.sleep(0.1)
    
    # Log audio generation without the actual encoded data
    logger.info("Generated audio response (length: approx. %d KB)", 
                len(stream_data["audio"]) // 1024 if stream_data["audio"] else 0)
    
    # Send the audio last
    yield {"audio": stream_data["audio"], "audio_id": stream_data["audio_id"]}
    
    # Send the full transcript as a special final event
    yield {"full_transcript": stream_data["full_transcript"]}
    
    # Calculate and return the generation time
    generation_time = time.time() - start_time
    logger.info("Model response generation time: %.2f seconds", generation_time)
    yield {"timing": {"model_generation_time": generation_time}}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use ["http://localhost:3000"] in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DynamoDB on startup
@app.on_event("startup")
async def startup_event():
    initialize_db()
    logger.info("DynamoDB initialized")

@app.websocket("/ws/conversation")
async def realtime_conversation(websocket: WebSocket):
    session_id = str(uuid.uuid4())
    logger.info(f"New conversation session started: {session_id}")
    await websocket.accept()
    
    conversation_sessions[session_id] = {
        "conversation": [],
        "last_response_time": None,  # Track when the last assistant response was sent
        "last_model_generation_time": None  # Track the last model generation time
    }
    messages = conversation_sessions[session_id]["conversation"]
    
    try:
        init_msg = await websocket.receive_json()
        if init_msg.get("type") != "start":
            await websocket.send_json(format_error("Expected 'start' message with article"))
            return
        article = init_msg.get("article", "")
        if not article:
            await websocket.send_json(format_error("Article not provided."))
            return
            
        # Get the dialogue mode from the message, default to "critical" if not provided
        dialogue_mode = init_msg.get("mode", "critical")
        logger.info(f"Using dialogue mode: {dialogue_mode}")
            
        # Get the origin URL that made the request
        origin_url = init_msg.get("origin_url", None)
        logger.info(f"Request from origin: {origin_url}")
            
        logger.info("Received article for analysis (length: %d chars)", len(article))
        
        # Save the initial session information to DynamoDB
        save_session_init(session_id, article, dialogue_mode, origin_url)
        
        # Get propaganda info for all modes
        propaganda_result = await detect_propaganda(article)
        propaganda_info = {
            cat: [
                {k: entry[k] for k in ['explanation', 'location', 'contextualize'] if k in entry}
                for entry in entries
            ]
            for cat, entries in propaganda_result.get('data', {}).items()
        }
        
        # Save propaganda analysis results to DynamoDB
        save_propaganda_analysis(session_id, propaganda_result)
        
        # Get the appropriate system prompt based on mode
        logger.info(f"Constructing system prompt for mode: {dialogue_mode}")
        system_prompt = get_prompt(dialogue_mode, article, propaganda_info)
        logger.info(f"System prompt constructed. {system_prompt}")
        messages.append({"role": "system", "content": system_prompt})
        
        # Add initial user message to conversation flow (but don't save to DB)
        initial_user_message = "Please start the conversation."
        initial_user_content = [{"type": "text", "text": initial_user_message}]
        messages.append({"role": "user", "content": initial_user_content})
        
        logger.info("Generating initial assistant response...")
        full_transcript = ""
        response_id = f"assistant_{uuid.uuid4()}"
        
        async for delta in chat_completion_streaming(messages):
            # Check if this is the timing yield
            if "timing" in delta:
                conversation_sessions[session_id]["last_model_generation_time"] = delta["timing"]["model_generation_time"]
                continue
                
            # Check if this is the full transcript yield
            if "full_transcript" in delta:
                full_transcript = delta["full_transcript"]
                continue
                
            await websocket.send_json({"type": "assistant_delta", "payload": delta})
            if "text" in delta:
                full_transcript += delta["text"]
        
        # Save assistant message to DynamoDB with timing info
        timing_info = {
            "model_generation_time": conversation_sessions[session_id]["last_model_generation_time"]
        }
        save_message(session_id, "assistant", full_transcript, response_id, timing_info)
        
        # Send the final message with the complete transcript
        logger.info("Initial assistant response completed")
        await websocket.send_json({
            "type": "assistant_final", 
            "payload": {
                "text": full_transcript,
                "id": response_id,
                "timing": timing_info
            }
        })
        
        # Update the last response time
        conversation_sessions[session_id]["last_response_time"] = time.time()
        
        while True:
            user_msg = await websocket.receive_json()
            
            # Get user response time from frontend if provided
            user_response_time = None
            if "timing" in user_msg:
                user_response_time = user_msg["timing"].get("user_response_time")
            
            # Calculate user response time if not provided by frontend
            if not user_response_time and conversation_sessions[session_id]["last_response_time"]:
                user_response_time = time.time() - conversation_sessions[session_id]["last_response_time"]
                logger.info("User response time: %.2f seconds", user_response_time)
            
            if user_msg.get("type") != "user":
                await websocket.send_json(format_error("Invalid message type. Expected 'user'."))
                continue
                
            user_content = user_msg.get("content")
            if not user_content:
                await websocket.send_json(format_error("No content provided in user message."))
                continue
            
            # Generate a unique ID for this user message
            user_message_id = f"user_{uuid.uuid4()}"
            
            # Process any audio content
            transcript_text = None
            if isinstance(user_content, list):
                for content_item in user_content:
                    if content_item.get("type") == "input_audio":
                        audio_info = content_item.get("input_audio")
                        if audio_info and audio_info.get("format") == "wav":
                            try:
                                data = audio_info.get("data")
                                logger.info("Processing user audio...")
                                audio_info["data"] = ensure_valid_wav(data)
                                
                                # We need to perform speech-to-text here to get the transcript
                                try:
                                    audio_bytes = base64.b64decode(audio_info["data"])
                                    with open("temp_audio.wav", "wb") as f:
                                        f.write(audio_bytes)
                                    
                                    # Use OpenAI's Whisper API for transcription
                                    with open("temp_audio.wav", "rb") as audio_file:
                                        logger.info("Transcribing user audio...")
                                        transcript = client.audio.transcriptions.create(
                                            model="whisper-1",
                                            file=audio_file,
                                            language="en"
                                        )
                                    
                                    # Send the transcript to the client for display
                                    if transcript.text:
                                        transcript_text = transcript.text
                                        logger.info(f"USER: {transcript_text}")
                                        await websocket.send_json({
                                            "type": "user_transcript",
                                            "payload": {
                                                "text": transcript_text,
                                                "transcript": transcript_text,
                                                "item_id": user_message_id
                                            }
                                        })
                                except Exception as e:
                                    logger.error(f"Failed to transcribe audio: {e}")
                                    # Continue even if transcription fails
                            except ValueError as e:
                                logger.error("Audio conversion failed: %s", e)
                                await websocket.send_json(format_error(str(e)))
                                continue
            
            # Save the user message to DynamoDB with timing info
            timing_info = {
                "user_response_time": user_response_time
            }
            save_message(session_id, "user", user_content, user_message_id, timing_info)
            
            messages.append({"role": "user", "content": user_content})
            logger.info("Appended user message to conversation. Total messages: %d", len(messages))
            
            # Get the assistant response with transcript
            logger.info("Processing user input...")
            full_transcript = ""
            response_id = f"assistant_{uuid.uuid4()}"
            
            async for delta in chat_completion_streaming(messages):
                # Check if this is the timing yield
                if "timing" in delta:
                    conversation_sessions[session_id]["last_model_generation_time"] = delta["timing"]["model_generation_time"]
                    continue
                    
                # Check if this is the full transcript yield
                if "full_transcript" in delta:
                    full_transcript = delta["full_transcript"]
                    continue
                
                await websocket.send_json({"type": "assistant_delta", "payload": delta})
                if "text" in delta:
                    full_transcript += delta["text"]
            
            # Save assistant message to DynamoDB with timing info
            timing_info = {
                "model_generation_time": conversation_sessions[session_id]["last_model_generation_time"]
            }
            save_message(session_id, "assistant", full_transcript, response_id, timing_info)
            
            # Send the final message with the complete transcript
            logger.info("Sent complete assistant response")
            await websocket.send_json({
                "type": "assistant_final", 
                "payload": {
                    "text": full_transcript,
                    "id": response_id,
                    "timing": timing_info
                }
            })
            
            # Update the last response time for the next user response
            conversation_sessions[session_id]["last_response_time"] = time.time()
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        # Save session end with normal disconnection reason
        save_session_end(session_id, "normal_disconnect")
    except Exception as e:
        logger.exception(f"Error during realtime conversation for session {session_id}")
        # Save session end with error reason
        save_session_end(session_id, f"error: {str(e)}")
        # Try to notify client about the error
        try:
            await websocket.send_json(format_error(str(e)))
        except:
            pass

if __name__ == "__main__":
    logger.info("Starting server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
