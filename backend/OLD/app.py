import os
import uuid
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, DateTime, func
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from backend.apollo_dialogue import ApollolyticsDialogueAsync  # Importing the async class
import logging
from typing import Optional


# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Database URL (from .env file)
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize SQLAlchemy metadata
metadata = MetaData()

# Define a single table for both articles and conversations
interaction_table = Table(
    "interactions",
    metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False),  # Tracks sessions
    Column("article_text", Text, nullable=True),  # Nullable, will be populated when article is submitted
    Column("detected_propaganda", Text, nullable=True),  # Nullable, filled after article analysis
    Column("user_message", Text, nullable=True),  # Stores the user's input
    Column("bot_response", Text, nullable=False),  # Stores bot responses
    Column("timestamp", DateTime, server_default=func.now())  # Tracks when the interaction occurred
)

# Initialize FastAPI app
app = FastAPI()

#Add CORS middleware to allow requests from different origins
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://apollolytics-dialogue-frontend-bp1u3rkjl.vercel.app"
    "https://apollolytics-dialogue-frontend.vercel.app",
    "https://a50f-16-170-227-168.ngrok-free.app",
    "https://apollolytics.com"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://apollolytics-dialogue-frontend-ac6bi8v0r.vercel.app", "https://apollolytics-dialogue-frontend-65u905sea.vercel.app", "https://apollolytics-dialogue.vercel.app", "http://localhost:3000", "https://localhost:8000"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Store active conversations per session (in-memory)
active_conversations = {}

# Define the model for input from the frontend
class UserMessage(BaseModel):
    user_input: str

class ArticleSubmission(BaseModel):
    article_text: str
    dialogue_type: str 
    use_fake_data: Optional[bool] = False  # New field to decide whether to use fake data

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to log the interaction in a single table (both user message and bot response)
async def log_interaction(db, session_id: str, user_message: str = None, article_text: str = None, detected_propaganda: str = None, bot_response: str = None):
    try:
        query = interaction_table.insert().values(
            id=str(uuid.uuid4()),
            session_id=session_id,
            article_text=article_text,
            detected_propaganda=detected_propaganda,
            user_message=user_message,  # Log the user's message
            bot_response=bot_response
        )
        db.execute(query)
        db.commit()
    except Exception as e:
        logging.error(f"Error logging interaction: {e}")
        raise HTTPException(status_code=500, detail="Error logging interaction.")

# Helper function to generate or retrieve session ID from cookies
def get_or_create_session_id(request: Request, response: Response):
    session_id = request.cookies.get("session_id")
    if not session_id:
        # Generate a new session ID if one doesn't exist
        session_id = str(uuid.uuid4())
        # Set the session_id in a cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=True,   # Allow HTTP for local dev
            samesite="None"  # Allow cross-origin cookie sending
        )


    return session_id


# Endpoint to analyze propaganda and initialize a conversation
@app.post("/analyze_propaganda")
async def analyze_article(article_submission: ArticleSubmission, request: Request, response: Response, db=Depends(get_db)):
    session_id = get_or_create_session_id(request, response)

    if not article_submission.article_text.strip():
        raise HTTPException(status_code=400, detail="Article text cannot be empty.")
    
    print(f"analyze session id {session_id}", flush=True)
    # Initialize ApollolyticsDialogueAsync class with dialogue_type from article_submission
    dialogue = ApollolyticsDialogueAsync(dialogue_type=article_submission.dialogue_type)
    
    # Decide whether to detect propaganda or use fake data based on use_fake_data
    if article_submission.use_fake_data:
        # Load fake detected propaganda from JSON file
        import json
        with open("backend/fake.json", "r") as file:
            detected_propaganda = json.load(file)
    else:
        # Detect propaganda in the article asynchronously
        detected_propaganda = await dialogue.detect_propaganda(article_submission.article_text)

    if "error" in detected_propaganda:
        raise HTTPException(status_code=400, detail=detected_propaganda["error"])

    # Create a conversation chain with the system prompt asynchronously
    system_prompt, conversation_chain, initial_response = await dialogue.create_conversation_chain(
        input_article=article_submission.article_text,
        detected_propaganda=detected_propaganda['data']
    )
    
    # Store the initialized conversation chain in memory for this session
    active_conversations[session_id] = {
        "dialogue": dialogue,
        "conversation_chain": conversation_chain
    }

    # Log the article and the bot's first response
    await log_interaction(
        db=db,
        session_id=session_id,
        article_text=article_submission.article_text,
        detected_propaganda=str(detected_propaganda),
        bot_response=initial_response
    )
    
    return {
        "detected_propaganda": detected_propaganda,
        "bot_message": initial_response
    }


@app.post("/analyze_propaganda_fake")
async def analyze_article(article_submission: ArticleSubmission, request: Request, response: Response, db=Depends(get_db)):
    session_id = get_or_create_session_id(request, response)

    if not article_submission.article_text.strip():
        raise HTTPException(status_code=400, detail="Article text cannot be empty.")
    
    print(f"analyze session id", session_id, flush=True)
    # Initialize ApollolyticsDialogueAsync class only for the first time (on article submission)
    dialogue = ApollolyticsDialogueAsync(dialogue_type="socratic")

    import json
    # Detect propaganda in the article asynchronously
    with open("backend/fake.json", "r") as file:
        detected_propaganda = json.load(file)

    if "error" in detected_propaganda:
        raise HTTPException(status_code=400, detail=detected_propaganda["error"])

    # Create a conversation chain with the system prompt asynchronously
    system_prompt, conversation_chain, initial_response = await dialogue.create_conversation_chain(
        input_article=article_submission.article_text, 
        detected_propaganda=detected_propaganda['data']
    )
    
    # Store the initialized conversation chain in memory for this session
    active_conversations[session_id] = {
        "dialogue": dialogue,
        "conversation_chain": conversation_chain
    }

    # Log the article and the bot's first response
    await log_interaction(
        db=db,
        session_id=session_id,
        article_text=article_submission.article_text,
        detected_propaganda=str(detected_propaganda),
        bot_response=initial_response
    )
    
    return {
        "detected_propaganda": detected_propaganda,
        "bot_message": initial_response
    }


# Endpoint for continuing the dialogue (conversation)
@app.post("/continue_conversation")
async def continue_conversation(user_message: UserMessage, request: Request, response: Response, db=Depends(get_db)):
    # Log all the headers in the request

    session_id = get_or_create_session_id(request, response)

    if not user_message.user_input.strip():
        raise HTTPException(status_code=400, detail="User input cannot be empty.")
    
    # Retrieve the conversation chain and dialogue for this session
    if session_id not in active_conversations:
        raise HTTPException(status_code=400, detail="No active conversation found for this session.")
    
    conversation_data = active_conversations[session_id]
    conversation_chain = conversation_data["conversation_chain"]
    dialogue = conversation_data["dialogue"]

    # Process the user input and generate a response using the conversation chain asynchronously
    bot_response = await dialogue.process_user_input(conversation_chain, user_message.user_input)
    
    # Log the user input and bot response
    await log_interaction(
        db=db,
        session_id=session_id,
        user_message=user_message.user_input,  # Log the user's input
        bot_response=bot_response  # Log the bot's response
    )
    
    return {"bot_message": bot_response}


# Startup and shutdown events for managing database connections
@app.on_event("startup")
async def startup():
    metadata.create_all(engine)

@app.on_event("shutdown")
async def shutdown():
    pass  # SQLAlchemy sessions close automatically with the 'get_db' dependency
