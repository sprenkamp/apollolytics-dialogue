import os
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import uuid
import requests
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, DateTime, ForeignKey, func, select
from databases import Database
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.schema import SystemMessage
from langchain.memory import ConversationBufferMemory
from src.prompts.system_prompts import system_prompts

# Load environment variables from .env file
load_dotenv()

# Database URL (from .env file)
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize SQLAlchemy metadata and Database instance
metadata = MetaData()
database = Database(DATABASE_URL)

# Define the articles table using SQLAlchemy
articles = Table(
    "articles",
    metadata,
    Column("id", String, primary_key=True),
    Column("article_text", Text, nullable=False, unique=True),  # Ensure unique articles
    Column("detected_propaganda", Text, nullable=False),
    Column("timestamp", DateTime, server_default=func.now())
)

# Define the conversations table using SQLAlchemy
conversations = Table(
    "conversations",
    metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False),
    Column("article_id", String, ForeignKey("articles.id")),  # Foreign key to the articles table
    Column("user_message", Text),
    Column("bot_response", Text),
    Column("timestamp", DateTime, server_default=func.now())
)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow requests from different origins
origins = [
    "http://localhost:3000",  # Example frontend running on localhost
    "https://apollolytics-dialogue-frontend-76vbnmkbz.vercel.app/",
    "https://apollolytics.com/",  # Replace with your actual frontend domain
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

# Function to log the article in PostgreSQL (ensures uniqueness)
async def log_article(article_text: str, detected_propaganda: dict):
    # Check if the article already exists in the database
    query = select([articles.c.id]).where(articles.c.article_text == article_text)
    article_id = await database.fetch_one(query)
    
    if article_id:
        return article_id  # Return existing article ID if found

    # If the article doesn't exist, insert it
    query = articles.insert().values(article_text=article_text, detected_propaganda=str(detected_propaganda))
    article_id = await database.execute(query)
    return article_id

# Function to log interactions in PostgreSQL
async def log_interaction(session_id: str, article_id: str, user_message: Optional[str], bot_response: Optional[str]):
    query = conversations.insert().values(session_id=session_id, article_id=article_id, user_message=user_message, bot_response=bot_response)
    await database.execute(query)

# Endpoint for analyzing the article (article submission)
@app.post("/analyze_propaganda")
async def analyze_article(article_submission: ArticleSubmission, request: Request):
    session_id = request.cookies.get("session_id")
    if not article_submission.article_text.strip():
        raise HTTPException(status_code=400, detail="Article text cannot be empty.")
    
    detected_propaganda = detect_propaganda(article_submission.article_text)
    
    # Log the article in the database (re-use if it already exists)
    article_id = await log_article(article_submission.article_text, detected_propaganda)
    
    # Create a new conversation chain for this session
    conversation_chain = create_conversation_chain(article_submission.article_text, detected_propaganda)
    session_conversations[session_id] = conversation_chain  # Store the conversation chain by session ID
    
    # The bot should respond first
    bot_first_message = conversation_chain.predict(
        input="What are your thoughts on the key points presented in the article? Do you recognize instances of propaganda or disinformation?"
    )
    
    # Log the bot's response along with the article
    await log_interaction(session_id, article_id, None, bot_first_message)
    
    return {
        "detected_propaganda": detected_propaganda,
        "bot_message": bot_first_message  # The bot's first message
    }

# Endpoint for continuing the dialogue (conversation)
@app.post("/continue_conversation")
async def continue_conversation(user_message: UserMessage, request: Request):
    session_id = request.cookies.get("session_id")
    conversation_chain = session_conversations.get(session_id)
    
    if conversation_chain is None:
        raise HTTPException(status_code=400, detail="No conversation has been initialized. Submit an article first.")
    
    if not user_message.user_input.strip():
        raise HTTPException(status_code=400, detail="User input cannot be empty.")
    
    # Process the user input and generate a response
    bot_response = conversation_chain.predict(input=user_message.user_input)
    
    # Retrieve the article ID associated with the session
    query = text(f"SELECT article_id FROM conversations WHERE session_id = :session_id LIMIT 1")
    article_id = await database.fetch_one(query=query, values={"session_id": session_id})
    
    # Log the interaction in PostgreSQL
    await log_interaction(session_id, article_id, user_message.user_input, bot_response)
    
    return {"bot_message": bot_response}

# Startup and shutdown events for connecting/disconnecting the database
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
