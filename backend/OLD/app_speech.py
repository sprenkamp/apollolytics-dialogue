import asyncio
import base64
import json
import logging
import uuid
from typing import Dict, Any, List
import base64, io, wave

import websockets
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from openai import OpenAI

client = OpenAI()

# In-memory store for conversation history per session
conversation_sessions: Dict[str, list] = {}

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
    
    return results[-1] if results else {}

# --- Helper: OpenAI Chat Completion ---
async def chat_completion(messages: list) -> Dict[str, Any]:
    def blocking_call():
        completion = client.chat.completions.create(
            model="gpt-4o-audio-preview",
            modalities=["text", "audio"],
            audio={"voice": "alloy", "format": "wav"},
            messages=messages
        )
        # completion = completion.to_dict()
        # with open("output.json", "w") as file:
        #     json.dump(completion, file)
        return {
            "text": completion.choices[0].message.audio.transcript,
            "audio": completion.choices[0].message.audio.data,
            "audio_id": completion.choices[0].message.audio.id,
        }
    return await asyncio.to_thread(blocking_call)

# --- Helper: Session ID from Cookies ---
def get_or_create_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=True,   # Allow HTTP for local dev
            samesite="None"  # Allow cross-origin cookie sending
        )
    return session_id

# --- FastAPI App and Endpoints ---
app = FastAPI()

# Enable CORS for your frontend domain (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# class ConversationRequest(BaseModel):
#     message: str

@app.post("/conversation/start")
async def start_conversation(request: Request, response: Response):
    body = await request.json()
    article = body.get("article", "")
    session_id = get_or_create_session_id(request, response)
    #check propaganda
    propaganda_info = await detect_propaganda(article)
    #save propaganda info
    propaganda_info = {
        cat: [
            {k: entry[k] for k in ['explanation', 'location', 'contextualize'] if k in entry}
            for entry in entries
        ]
        for cat, entries in propaganda_info.get('data', {}).items()
    }
    with open(f"{article[:20]}.json", "w") as file:
        json.dump(propaganda_info, file)

    with open(f"{article[:20]}.json", "r") as file:
        propaganda_info = json.load(file)
    
    system_prompt = f'''**PERSONA**: Socratic Dialogue with Informative Support

**Description**: Engage the user in thoughtful conversations that promote critical thinking. 
Begin the dialogue with an open-ended question about the topic. In subsequent responses, if possible, 
debunk the user's input using facts, and end with a follow-up question. Debate any viewpoint of the article that user gives to you, 
focusing on the ARTICLE at hand. Use the detected propaganda to guide the conversation and challenge the user's assumptions. 
Also use your own knowledge on historical events and answer in a detailed manner.

**ANSWER STRUCTURE**:
- always take the message given by the user and provide a rebuttal using historical context or facts regarding the article and the users opinion
- use the detected propaganda to challenge the user's assumptions
- use your own knowledge on historical events and answer in a detailed manner
- do not provided canned responses, always provide a unique response to the user's input

**ARTICLE**: PLEASE ARGUE AGAINST THE ARTICLE BELOW
{article}

**DETECTED PROPAGANDA**: USE THIS INFORMATION TO GUIDE YOUR ARGUMENTATION
{propaganda_info} needed to be formatted properly

Engage in a thoughtful dialogue'''
    
    messages = [{"role": "system", "content": system_prompt}]
    initial_user_message = "Please start the conversation."
    messages.append({"role": "user", "content": [{"type": "text", "text": initial_user_message}]})
    
    output = await chat_completion(messages)
    messages.append({"role": "assistant", "content": output["text"]})
    
    return_payload = {
        # "session_id": session_id,
        "conversation": messages,
        "audio": output["audio"],
        "audio_id": output["audio_id"],
    }

    conversation_sessions[session_id] = return_payload
    

    return return_payload

@app.post("/conversation/respond")
async def conversation_respond(request: Request, response: Response):
    """
    Receives a user's follow-up audio message (as a base64 string), updates the conversation history,
    and streams the next assistant audio response.
    """
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in conversation_sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    request = await request.json()
    
    user_audio = request["message"]

    wav_bytes = base64.b64decode(user_audio)
    
    encoded_audio = base64.b64encode(wav_bytes).decode("utf-8")


    convesation_session = conversation_sessions[session_id]
    messages = convesation_session["conversation"]
    last_audio_id = convesation_session["audio_id"]
    
    user_message = {
            "role": "user",
            "content": [
                { "type": "input_audio", "input_audio": {
                    "data": encoded_audio,
                    "format": "wav"
                } }
            ]
        }
    messages.append(user_message)

    messages.append({"role": "assistant", "audio": {"id": last_audio_id}})

    output = await chat_completion(messages)

    return_payload = {
        # "session_id": session_id,
        "conversation": messages,
        "audio": output["audio"],
        "audio_id": output["audio_id"],
    }

    conversation_sessions[session_id] = return_payload

    return return_payload



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
