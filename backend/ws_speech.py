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
import pathlib
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

# Import conversation evaluation
from backend.conversation_evaluation.evaluator import evaluate_conversation

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
text_history: Dict[str, List[Dict[str, str]]] = {}
PROPAGANDA_WS_URL = "ws://13.48.71.178:8000/ws/analyze_propaganda"

# Map subpage (from origin_url) to cached propaganda result file
EXPERIMENT_SUBPAGE_MAP = {
    "/dialogue/positive1": "article1.json",
    "/dialogue/positive2": "article2.json",
    "/dialogue/positive3": "article3.json",
    "/dialogue/negative1": "article1.json",
    "/dialogue/negative2": "article2.json",
    "/dialogue/negative3": "article3.json",
}

def format_error(message: str) -> Dict[str, str]:
    return {"error": message}

def is_valid_wav(audio_base64: str) -> bool:
    try:
        audio_bytes = base64.b64decode(audio_base64)
        with io.BytesIO(audio_bytes) as audio_file:
            with wave.open(audio_file, 'rb') as wav_file:
                wav_file.getparams()
        return True
    except Exception:
        return False

def ensure_valid_wav(audio_base64: str) -> str:
    """
    Checks if the provided base64 audio is a valid WAV file.
    If not, it tries to convert the audio (detecting if it is a WebM file)
    using pydub and returns a valid WAV file as base64.
    """
    audio_bytes = base64.b64decode(audio_base64)
    # First try to validate as WAV
    try:
        with io.BytesIO(audio_bytes) as audio_file:
            with wave.open(audio_file, 'rb') as wav_file:
                wav_file.getparams()
        return audio_base64
    except wave.Error:
        pass

    # If that fails, attempt to convert. Check if the file is actually a WebM file.
    try:
        if audio_bytes.startswith(b'\x1A\x45\xDF\xA3'):
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
        else:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        valid_bytes = buf.getvalue()
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
        
        # Calculate audio duration from WAV data
        audio_duration = None
        try:
            audio_bytes = base64.b64decode(audio_data)
            with io.BytesIO(audio_bytes) as audio_file:
                # Use pydub to calculate duration
                audio = AudioSegment.from_file(audio_file, format="wav")
                audio_duration = len(audio) / 1000.0  # pydub returns duration in milliseconds
                logger.info(f"Audio duration from pydub: {audio_duration:.2f} seconds")
        except Exception as e:
            logger.error(f"Failed to calculate audio duration: {e}")
            logger.error(f"Audio data length: {len(audio_bytes)} bytes")
        
        chunk_size = 20
        text_chunks = [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size)]
        logger.info("ASSISTANT: %s", transcript)
        return {
            "text_chunks": text_chunks, 
            "audio": audio_data, 
            "audio_id": audio_id,
            "full_transcript": transcript,
            "audio_duration": audio_duration
        }
    
    stream_data = await asyncio.to_thread(blocking_stream)
    
    # Store accumulated text for the transcript
    accumulated_text = ""
    
    # Stream text in chunks for smooth UI experience
    for chunk in stream_data["text_chunks"]:
        accumulated_text += chunk
        yield {"text": chunk}
        await asyncio.sleep(0.1)
    
    # Send the audio last without logging
    yield {"audio": stream_data["audio"], "audio_id": stream_data["audio_id"]}
    
    # Send the full transcript as a special final event
    yield {"full_transcript": stream_data["full_transcript"]}
    
    # Calculate timing metrics
    generation_time = time.time() - start_time
    logger.info("Model response generation time: %.2f seconds", generation_time)
    if stream_data["audio_duration"]:
        logger.info("Model audio duration: %.2f seconds", stream_data["audio_duration"])
    
    # Calculate total response time (from start to end of audio)
    total_response_time = generation_time + (stream_data["audio_duration"] or 0)
    
    yield {
        "timing": {
            "model_generation_time": generation_time,  # Time taken to generate response
            "model_audio_duration": stream_data["audio_duration"],  # Duration of audio
            "total_response_time": total_response_time  # Total time including audio playback
        }
    }

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
    
    # Initialize text history for this session
    text_history[session_id] = []
    
    conversation_sessions[session_id] = {
        "conversation": [],
        "last_response_time": None,
        "last_model_generation_time": None,
        "last_model_audio_duration": None,
        "last_total_response_time": None
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
            
        # Get the Prolific ID
        prolific_id = init_msg.get("prolific_id", "XXX")
        logger.info(f"Prolific ID: {prolific_id}")
            
        logger.info("Received article for analysis (length: %d chars)", len(article))
        
        # Save the initial session information to DynamoDB
        try:
            logger.info(f"DB: Saving session init - ID: {session_id}, Mode: {dialogue_mode}, Article: {len(article)} chars")
            save_session_init(session_id, article, dialogue_mode, origin_url, prolific_id)
        except Exception as e:
            logger.error(f"DB ERROR: Failed to save session init - ID: {session_id}, Error: {str(e)}")
        
        # Get propaganda info for all modes
        propaganda_result = None
        cached_file = None
        if origin_url:
            for subpage, filename in EXPERIMENT_SUBPAGE_MAP.items():
                if origin_url.endswith(subpage):
                    cached_file = filename
                    break
        if cached_file:
            path = pathlib.Path(__file__).parent / "model_output" / cached_file
            with open(path, "r", encoding="utf-8") as f:
                propaganda_result = json.load(f)
            logger.info(f"Loaded cached propaganda result from {cached_file} for subpage {subpage}")
        else:
            # Not a known experiment subpage, run detection
            propaganda_result = await detect_propaganda(article)
        propaganda_info = {
            cat: [
                {k: entry[k] for k in ['explanation', 'location', 'contextualize'] if k in entry}
                for entry in entries
            ]
            for cat, entries in propaganda_result.get('data', {}).items()
        }
        
        # Save propaganda analysis results to DynamoDB
        try:
            logger.info(f"DB: Saving propaganda analysis - ID: {session_id}, Results: {len(propaganda_result.get('data', {}))} categories")
            save_propaganda_analysis(session_id, propaganda_result)
        except Exception as e:
            logger.error(f"DB ERROR: Failed to save propaganda analysis - ID: {session_id}, Error: {str(e)}")
        
        # Get the appropriate system prompt based on mode
        logger.info(f"Constructing system prompt for mode: {dialogue_mode}")
        system_prompt = get_prompt(dialogue_mode, article, propaganda_info)
        logger.info(f"System prompt constructed. {system_prompt}")
        messages.append({"role": "system", "content": system_prompt})
        
        # Store system prompt in text history
        text_history[session_id].append({
            "role": "system",
            "content": system_prompt
        })
        
        # Add initial user message to conversation flow (but don't save to DB)
        initial_user_message = "Please start the conversation."
        initial_user_content = [{"type": "text", "text": initial_user_message}]
        messages.append({"role": "user", "content": initial_user_content})
        
        # Store initial user message in text history
        text_history[session_id].append({
            "role": "user",
            "content": initial_user_message
        })
        
        logger.info("Generating initial assistant response...")
        full_transcript = ""
        response_id = f"assistant_{uuid.uuid4()}"
        
        async for delta in chat_completion_streaming(messages):
            # Check if this is the timing yield
            if "timing" in delta:
                conversation_sessions[session_id]["last_model_generation_time"] = delta["timing"]["model_generation_time"]
                conversation_sessions[session_id]["last_model_audio_duration"] = delta["timing"].get("model_audio_duration")
                conversation_sessions[session_id]["last_total_response_time"] = delta["timing"]["total_response_time"]
                continue
                
            # Check if this is the full transcript yield
            if "full_transcript" in delta:
                full_transcript = delta["full_transcript"]
                continue
                
            await websocket.send_json({"type": "assistant_delta", "payload": delta})
            if "text" in delta:
                full_transcript += delta["text"]
        
        # Store assistant response in text history
        text_history[session_id].append({
            "role": "assistant",
            "content": full_transcript
        })
        
        # Save assistant message to DynamoDB with timing info
        timing_info = {
            "model_generation_time": conversation_sessions[session_id]["last_model_generation_time"],
            "model_audio_duration": conversation_sessions[session_id].get("last_model_audio_duration"),
            "total_response_time": conversation_sessions[session_id]["last_total_response_time"]
        }
        try:
            logger.info(f"DB: Saving assistant message - ID: {session_id}, Gen time: {timing_info['model_generation_time']:.2f}s, Audio duration: {timing_info.get('model_audio_duration'):.2f}s, Total: {timing_info['total_response_time']:.2f}s")
            save_message(session_id, "assistant", full_transcript, response_id, timing_info)
        except Exception as e:
            logger.error(f"DB ERROR: Failed to save assistant message - ID: {session_id}, Error: {str(e)}")
        
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
        
        # Update the last response time for the next user response
        conversation_sessions[session_id]["last_response_time"] = time.time()
        
        while True:
            user_msg = await websocket.receive_json()
            
            # Get user response time from frontend if provided
            thinking_time = None
            recording_duration = None
            total_response_time = None
            if "timing" in user_msg:
                timing = user_msg["timing"]
                if isinstance(timing, dict):
                    thinking_time = timing.get("thinking_time")  # Time from assistant response to starting recording
                    recording_duration = timing.get("recording_duration")  # Duration of recording
                    total_response_time = timing.get("total_response_time")  # Total time from assistant response to end of recording
                    logger.info(f"Received timing from frontend - Thinking: {thinking_time}, Recording: {recording_duration}, Total: {total_response_time}")
            
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
                                # Process audio without logging the data
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
            timing_info = {}
            if thinking_time is not None:
                timing_info["thinking_time"] = thinking_time
            if recording_duration is not None:
                timing_info["recording_duration"] = recording_duration
            if total_response_time is not None:
                timing_info["total_response_time"] = total_response_time

            try:
                if timing_info:
                    logger.info(f"DB: Saving user message - ID: {session_id}, Timing: {timing_info}")
                # Only save the transcript text, not the audio content
                save_message(session_id, "user", transcript_text or user_content, user_message_id, timing_info)
            except Exception as e:
                logger.error(f"DB ERROR: Failed to save user message - ID: {session_id}, Error: {str(e)}")
            
            # Keep the full content (including audio) for the conversation context
            messages.append({"role": "user", "content": user_content})
            logger.info("Appended user message to conversation. Total messages: %d", len(messages))
            
            # Store user message in text history right after receiving it
            if transcript_text:
                # If we have a transcript, use that
                text_history[session_id].append({
                    "role": "user",
                    "content": transcript_text
                })
            elif isinstance(user_content, list):
                # If it's a list (like with audio), find the text content
                for item in user_content:
                    if item.get("type") == "text":
                        text_history[session_id].append({
                            "role": "user",
                            "content": item.get("text")
                        })
                        break
            
            # Get the assistant response with transcript
            logger.info("Processing user input...")
            full_transcript = ""
            response_id = f"assistant_{uuid.uuid4()}"
            
            # Check if conversation has stalled before generating response
            logger.info(f"Text history for session:{session_id}:", "\n", text_history[session_id])
            is_stalled = evaluate_conversation(text_history[session_id])
            logger.info(f"Conversation stalled: {is_stalled}")
            
            if is_stalled:
                logger.warning(f"Conversation for session {session_id} appears to be stalled")
                # Send final message to frontend
                await websocket.send_json({
                    "type": "conversation_end",
                    "payload": {
                        "message": "Thank you for participating in our experiment. Your feedback and engagement have been valuable. The conversation will now end.",
                        "reason": "conversation_stalled"
                    }
                })
                # Save session end with stalled reason
                try:
                    logger.info(f"DB: Saving session end - ID: {session_id}, Reason: conversation_stalled")
                    save_session_end(session_id, "conversation_stalled")
                except Exception as e:
                    logger.error(f"DB ERROR: Failed to save session end - ID: {session_id}, Error: {str(e)}")
                # Clean up the session
                del text_history[session_id]
                del conversation_sessions[session_id]
                return
            
            # If not stalled, proceed with normal assistant response
            async for delta in chat_completion_streaming(messages):
                # Check if this is the timing yield
                if "timing" in delta:
                    conversation_sessions[session_id]["last_model_generation_time"] = delta["timing"]["model_generation_time"]
                    conversation_sessions[session_id]["last_model_audio_duration"] = delta["timing"].get("model_audio_duration")
                    conversation_sessions[session_id]["last_total_response_time"] = delta["timing"]["total_response_time"]
                    continue
                    
                # Check if this is the full transcript yield
                if "full_transcript" in delta:
                    full_transcript = delta["full_transcript"]
                    continue
                
                await websocket.send_json({"type": "assistant_delta", "payload": delta})
                if "text" in delta:
                    full_transcript += delta["text"]
            
            # Store assistant response in text history
            text_history[session_id].append({
                "role": "assistant",
                "content": full_transcript
            })
            
            # Save assistant message to DynamoDB with timing info
            timing_info = {
                "model_generation_time": conversation_sessions[session_id]["last_model_generation_time"],
                "model_audio_duration": conversation_sessions[session_id].get("last_model_audio_duration"),
                "total_response_time": conversation_sessions[session_id]["last_total_response_time"]
            }
            try:
                logger.info(f"DB: Saving assistant message - ID: {session_id}, Gen time: {timing_info['model_generation_time']:.2f}s, Audio duration: {timing_info.get('model_audio_duration'):.2f}s, Total: {timing_info['total_response_time']:.2f}s")
                save_message(session_id, "assistant", full_transcript, response_id, timing_info)
            except Exception as e:
                logger.error(f"DB ERROR: Failed to save assistant message - ID: {session_id}, Error: {str(e)}")
            
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
        # Log the final text history
        logger.info(f"Text history for session {session_id}:")
        for msg in text_history[session_id]:
            logger.info(f"{msg['role'].upper()}: {msg['content']}")
        # Clean up the text history
        del text_history[session_id]
        # Save session end with normal disconnection reason
        try:
            reason = "client_disconnected"
            logger.info(f"DB: Saving session end - ID: {session_id}, Reason: {reason}")
            save_session_end(session_id, reason)
        except Exception as e:
            logger.error(f"DB ERROR: Failed to save session end - ID: {session_id}, Error: {str(e)}")
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
    logger.info("Starting server on 0.0.0.0:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)