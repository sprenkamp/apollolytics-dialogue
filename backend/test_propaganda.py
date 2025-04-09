import asyncio
import json
import websockets
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROPAGANDA_WS_URL = "ws://13.48.71.178:8000/ws/analyze_propaganda"

async def test_propaganda_detection():
    """Test the propaganda detection service"""
    test_article = """The media is lying to you about climate change. 
    Scientists are being paid by big corporations to hide the truth. 
    Only we can tell you what's really happening."""
    
    data = {
        "model_name": "gpt-4o-mini",
        "contextualize": True,
        "text": test_article
    }
    
    try:
        logger.info("Attempting to connect to propaganda detection service...")
        async with websockets.connect(PROPAGANDA_WS_URL) as websocket:
            logger.info("Connected successfully!")
            
            # Send the test data
            logger.info(f"Sending test article: {test_article[:50]}...")
            await websocket.send(json.dumps(data))
            
            # Wait for and print response
            logger.info("Waiting for response...")
            async for message in websocket:
                try:
                    result = json.loads(message)
                    logger.info(f"Received result: {json.dumps(result, indent=2)}")
                except json.JSONDecodeError as e:
                    logger.error(f"Received invalid JSON: {message}")
                    logger.error(f"Error: {e}")
                
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"Connection closed unexpectedly: {e}")
    except Exception as e:
        logger.error(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_propaganda_detection()) 