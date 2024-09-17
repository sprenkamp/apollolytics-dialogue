import os
import uuid
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text, DateTime, func
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from src.apollo_dialogue import ApollolyticsDialogueAsync  # Importing the async class
import logging

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

# Add CORS middleware to allow requests from different origins
origins = [
    "http://localhost:3000",
    "https://apollolytics-dialogue-frontend-76vbnmkbz.vercel.app/",
    "https://apollolytics.com/", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# @app.middleware("http")
# async def session_middleware(request: Request, call_next):
#     # Skip session creation for preflight (OPTIONS) requests
#     if request.method == "OPTIONS":
#         return await call_next(request)

#     # Retrieve the session ID from cookies
#     session_id = request.cookies.get("session_id")
    
#     # If no session ID, create a new one and set it in the response cookies
#     if not session_id:
#         session_id = str(uuid.uuid4())
#         print(f"Generated new session ID: {session_id}", flush=True)
#     else:
#         print(f"Existing session ID found: {session_id}", flush=True)
    
#     # Set session ID in request state so that it is available throughout the request lifecycle
#     request.state.session_id = session_id

#     # Call the next middleware or route handler
#     response = await call_next(request)

#     # Set the cookie with appropriate settings (make it secure and long-lived)
#     response.set_cookie(
#         key="session_id", 
#         value=session_id, 
#         httponly=True, 
#         max_age=60 * 60 * 24,  # 1 day
#         secure=False,  # Set to True for HTTPS
#         samesite="None"
#     )

#     print(f"Session Middleware: {request.state.session_id}", flush=True)
#     return response




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

@app.post("/analyze_propaganda")
async def analyze_article(article_submission: ArticleSubmission, request: Request, db=Depends(get_db)):
    # Retrieve session ID from request.state (set by middleware)
    session_id = request.state.session_id
    print("Session ID Analyze Propaganda: ", session_id, flush=True)
    
    if not article_submission.article_text.strip():
        raise HTTPException(status_code=400, detail="Article text cannot be empty.")
    
    # Initialize ApollolyticsDialogueAsync class only for the first time (on article submission)
    dialogue = ApollolyticsDialogueAsync(dialogue_type="socratic")

    # Detect propaganda in the article asynchronously
    detected_propaganda = await dialogue.detect_propaganda(article_submission.article_text)

    if "error" in detected_propaganda:
        raise HTTPException(status_code=400, detail=detected_propaganda["error"])

    # Create a conversation chain with the system prompt asynchronously
    system_prompt, conversation_chain, initial_response = await dialogue.create_conversation_chain(
        input_article=article_submission.article_text, 
        detected_propaganda=detected_propaganda
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
async def continue_conversation(user_message: UserMessage, request: Request, db=Depends(get_db)):
    session_id = request.state.session_id  # Get the session ID from request state
    # print(user_message, flush=True)
    # print(user_message.user_input)
    print("continue conversation: ", session_id, flush=True)
    # if not user_message.user_input.strip():
    #     raise HTTPException(status_code=400, detail="User input cannot be empty.")
    
    # # Retrieve the conversation chain and dialogue for this session
    # if session_id not in active_conversations:
    #     raise HTTPException(status_code=400, detail="No active conversation found for this session.")
    
    print(active_conversations, flush=True)

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
    print(bot_response)
    return {"bot_message": bot_response}


# Startup and shutdown events for managing database connections
@app.on_event("startup")
async def startup():
    metadata.create_all(engine)

@app.on_event("shutdown")
async def shutdown():
    pass  # SQLAlchemy sessions close automatically with the 'get_db' dependency
