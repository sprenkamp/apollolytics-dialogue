from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import uuid
import requests
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.schema import SystemMessage
from langchain.memory import ConversationBufferMemory
from src.prompts.system_prompts import system_prompts

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow requests from different origins
origins = [
    "http://localhost:3000",  # Example frontend running on localhost
    "http://your-frontend-domain.com",  # Replace with your actual frontend domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (POST, GET, etc.)
    allow_headers=["*"],  # Allow all headers
)

# In-memory storage for session-based conversation chains
session_conversations: Dict[str, ConversationChain] = {}

# Define the model for input from the frontend
class UserMessage(BaseModel):
    user_input: str

class ArticleSubmission(BaseModel):
    article_text: str

# Initialize LLM (OpenAI)
llm = ChatOpenAI(model_name="gpt-4o")

# Helper function to call propaganda detection API
def detect_propaganda(input_article):
    url = 'http://13.48.71.178:8000/analyze_propaganda'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "model_name": "gpt-4o",
        "contextualize": "true",
        "text": input_article
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail="Error analyzing propaganda.")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail="Failed to connect to propaganda detection API")

# Helper function to generate a new conversation chain for the session
def create_conversation_chain(article_text: str, detected_propaganda: dict):
    system_prompt = system_prompts["socratic"].content.format(
        input_article=article_text, result=detected_propaganda
    )

    conversation_chain = ConversationChain(
        llm=llm,
        verbose=True,
        memory=ConversationBufferMemory()
    )

    conversation_chain.memory.chat_memory.add_message(SystemMessage(content=system_prompt))
    return conversation_chain

# Middleware to assign and manage user sessions using cookies
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        session_id = str(uuid.uuid4())  # Generate a new session ID
        response = Response("New session created")
        response.set_cookie(key="session_id", value=session_id)
        response = await call_next(request)
        return response
    else:
        response = await call_next(request)
        return response

# Endpoint for analyzing the article (article submission)
@app.post("/analyze_propaganda")
async def analyze_article(article_submission: ArticleSubmission, request: Request):
    """
    Analyze the article for propaganda, return the detected propaganda, and have the bot respond first.
    """
    session_id = request.cookies.get("session_id")
    if not article_submission.article_text.strip():
        raise HTTPException(status_code=400, detail="Article text cannot be empty.")
    
    detected_propaganda = detect_propaganda(article_submission.article_text)
    
    # Create a new conversation chain for this session
    conversation_chain = create_conversation_chain(article_submission.article_text, detected_propaganda)
    session_conversations[session_id] = conversation_chain  # Store the conversation chain by session ID
    
    # The bot should respond first
    bot_first_message = conversation_chain.predict(
        input="What are your thoughts on the key points presented in the article? Do you recognize instances of propaganda or disinformation?"
    )
    
    return {
        "detected_propaganda": detected_propaganda,
        "bot_message": bot_first_message  # The bot's first message
    }

# Endpoint for continuing the dialogue (conversation)
@app.post("/continue_conversation")
async def continue_conversation(user_message: UserMessage, request: Request):
    """
    Continue the conversation with the LLM using the detected propaganda as context.
    """
    session_id = request.cookies.get("session_id")
    conversation_chain = session_conversations.get(session_id)
    
    if conversation_chain is None:
        raise HTTPException(status_code=400, detail="No conversation has been initialized. Submit an article first.")
    
    if not user_message.user_input.strip():
        raise HTTPException(status_code=400, detail="User input cannot be empty.")
    
    # Process the user input and generate a response
    response = conversation_chain.predict(input=user_message.user_input)
    
    return {"bot_message": response}