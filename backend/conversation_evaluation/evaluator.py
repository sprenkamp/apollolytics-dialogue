from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import logging
from typing import List, Dict
import json
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def evaluate_conversation(text_history: List[Dict[str, str]]) -> int:
    """
    Evaluate if a conversation is stalled.
    Returns 1 if stalled, 0 if active.
    
    Args:
        text_history: List of dictionaries containing 'role' and 'content' for each message
        
    Returns:
        1 if conversation is stalled, 0 if active
    """
    if not text_history:
        return 0
    
    # Format conversation for classification
    conversation_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in text_history
    ])
    
    # Define classification criteria
    system_message = """You are a conversation analyst evaluating a discussion about propaganda in news media. Your task is to determine if the conversation is stalled (1) or active (0).

A conversation is considered STALLED (return 1) if:
1. User repeatedly expresses disinterest or refuses to engage (e.g., multiple "I don't care" responses)
2. No meaningful exchange of ideas or information
3. Clear disengagement from the topic
4. No progression in understanding or analysis

A conversation is considered ACTIVE (return 0) if ANY of these are true:
1. Initial setup of the conversation (first few messages)
2. Discussion of propaganda techniques or media analysis
3. User shows interest
4. Natural flow of conversation with engagement
5. User is learning or gaining new insights

Return ONLY 0 or 1 as your answer."""

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "Conversation to analyze:\n{conversation}")
    ])

    # Initialize model and chain
    model = ChatOpenAI(model="gpt-4o")
    classification_chain = prompt | model | StrOutputParser()
    
    # Get classification
    try:
        result = classification_chain.invoke({"conversation": conversation_text})
        return int(result.strip())
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return 0  # Default to active if classification fails

def load_test_conversations(file_path: str = "test_conversations.json") -> List[Dict]:
    """
    Load test conversations from a JSON file.
    
    Args:
        file_path: Path to the JSON file containing test conversations
        
    Returns:
        List of conversation dictionaries
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data.get('conversations', [])
    except FileNotFoundError:
        logger.error(f"Test conversations file not found: {file_path}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in test conversations file: {file_path}")
        return []

def test_conversations():
    """Test the evaluator with conversations loaded from JSON file."""
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_file = os.path.join(current_dir, "test_conversations.json")
    
    # Load conversations from file
    conversations = load_test_conversations(test_file)
    
    if not conversations:
        logger.error("No conversations found to test")
        return
    
    # Evaluate each conversation
    for conversation in conversations:
        name = conversation.get('name', 'Unnamed conversation')
        messages = conversation.get('messages', [])
        
        logger.info(f"\nTesting conversation: {name}")
        result = evaluate_conversation(messages)
        logger.info(f"Status: {'STALLED' if result == 1 else 'ACTIVE'}")


if __name__ == "__main__":
    test_conversations()


