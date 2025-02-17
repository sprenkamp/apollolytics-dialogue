import asyncio
import base64
import json
import logging
import uuid
from typing import Dict, Any, List, AsyncGenerator

import websockets
from fastapi import FastAPI, Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from openai import OpenAI

client = OpenAI()

# In-memory store for conversation history per session
conversation_sessions: Dict[str, dict] = {}

# Configuration for your propaganda detection WebSocket endpoint
PROPAGANDA_WS_URL = "ws://13.48.71.178:8000/ws/analyze_propaganda"

def format_error(message: str) -> Dict[str, str]:
    return {"error": message}

# --- Helper: Propaganda Detection ---
async def detect_propaganda(input_article: str) -> Dict[str, Any]:
    data = {
        "model_name": "gpt-4o-mini",
        "contextualize": True,
        "text": input_article
    }
    
    results: List[Dict[str, Any]] = []
    
    try:
        async with websockets.connect(PROPAGANDA_WS_URL) as websocket:
            await websocket.send(json.dumps(data))
            async for message in websocket:
                try:
                    result = json.loads(message)
                    results.append(result)
                except json.JSONDecodeError:
                    print("Received an invalid JSON message:", message)
    except websockets.exceptions.ConnectionClosed as e:
        print("WebSocket connection closed:", e)
    print("propaganda results", results)
    return results[-1] if results else {}

# --- Helper: Realtime Chat Completion Streaming ---
async def chat_completion_streaming(messages: list) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Simulate a streaming chat completion call.
    
    In production, this function would yield deltas from the realtime API.
    Here, we simulate streaming by splitting the full transcript into chunks.
    """
    def blocking_stream():
        completion = client.chat.completions.create(
            model="gpt-4o-audio-preview",
            modalities=["text", "audio"],
            audio={"voice": "alloy", "format": "wav"},
            messages=messages
        )
        transcript = completion.choices[0].message.audio.transcript
        audio_data = completion.choices[0].message.audio.data
        audio_id = completion.choices[0].message.audio.id
        # Split transcript into chunks to simulate streaming.
        chunk_size = 20  # Adjust chunk size as needed.
        text_chunks = [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size)]
        return {"text_chunks": text_chunks, "audio": audio_data, "audio_id": audio_id}
    
    stream_data = await asyncio.to_thread(blocking_stream)
    # Stream text deltas.
    for chunk in stream_data["text_chunks"]:
        yield {"text": chunk}
        await asyncio.sleep(0.1)  # Simulate delay between chunks.
    # Finally, yield audio data (and its id) as part of the final delta.
    yield {"audio": stream_data["audio"], "audio_id": stream_data["audio_id"]}

# --- FastAPI App and WebSocket Endpoint ---
app = FastAPI()

# Enable CORS for your frontend domain (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/conversation")
async def realtime_conversation(websocket: WebSocket):
    await websocket.accept()
    
    # Session management: retrieve session_id from cookie (or generate a new one)
    session_id = websocket.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    conversation_sessions[session_id] = {"conversation": []}
    messages = conversation_sessions[session_id]["conversation"]
    
    try:
        # Step 1: Wait for the initial "start" message containing the article.
        init_msg = await websocket.receive_json()
        if init_msg.get("type") != "start":
            await websocket.send_json(format_error("Expected 'start' message with article"))
            return
        article = init_msg.get("article", "")
        if not article:
            await websocket.send_json(format_error("Article not provided."))
            return
        
        # Step 2: Run propaganda detection.
        propaganda_info = await detect_propaganda(article)
        # Process propaganda_info to extract only required fields.
        propaganda_info = {
            cat: [
                {k: entry[k] for k in ['explanation', 'location', 'contextualize'] if k in entry}
                for entry in entries
            ]
            for cat, entries in propaganda_info.get('data', {}).items()
        }
        
        # Step 3: Build system prompt and initial conversation history.
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
        # Use an initial user message to start the conversation.
        initial_user_message = "Please start the conversation."
        messages.append({"role": "user", "content": [{"type": "text", "text": initial_user_message}]})
        
        # Step 4: Stream the initial assistant response.
        async for delta in chat_completion_streaming(messages):
            await websocket.send_json({"type": "assistant_delta", "payload": delta})
        await websocket.send_json({"type": "assistant_final", "payload": "Initial response complete."})
        
        # Step 5: Loop to handle subsequent user messages in realtime.
        while True:
            user_msg = await websocket.receive_json()
            
            # Expecting a message of type "user" with a "content" field (text or audio).
            if user_msg.get("type") != "user":
                await websocket.send_json(format_error("Invalid message type. Expected 'user'."))
                continue
            
            user_content = user_msg.get("content")
            if not user_content:
                await websocket.send_json(format_error("No content provided in user message."))
                continue
            
            # Append the new user message to the conversation history.
            messages.append({"role": "user", "content": user_content})
            
            # Stream the assistant's response in realtime.
            async for delta in chat_completion_streaming(messages):
                await websocket.send_json({"type": "assistant_delta", "payload": delta})
            await websocket.send_json({"type": "assistant_final", "payload": "Response complete."})
    
    except Exception as e:
        logging.exception("Error during realtime conversation")
        await websocket.send_json(format_error(str(e)))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
