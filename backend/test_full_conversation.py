#!/usr/bin/env python3
"""
Full conversation test for OpenAI Realtime API integration
This script tests a complete multi-turn conversation with the ws_speech_real-time.py server
by simulating a full dialogue sequence with text prompts (to avoid audio dependency)
"""

import asyncio
import json
import argparse
import websockets
import time
from datetime import datetime

# Command line arguments
parser = argparse.ArgumentParser(description='Test a full conversation with the Realtime API integration')
parser.add_argument('--server', default='ws://localhost:8000/ws/conversation', 
                   help='WebSocket server URL (default: ws://localhost:8000/ws/conversation)')
parser.add_argument('--mode', default='critical', choices=['critical', 'supportive'],
                   help='Dialogue mode (default: critical)')
parser.add_argument('--log', default='conversation_log.txt',
                   help='File to save the conversation log (default: conversation_log.txt)')
parser.add_argument('--turns', type=int, default=3,
                   help='Number of conversation turns to simulate (default: 3)')
parser.add_argument('--article', default='',
                   help='Article text for testing. If not provided, a default will be used.')
args = parser.parse_args()

# Default test article if none provided
DEFAULT_ARTICLE = """
The threat from Russia is clear and present, as NATO officials have repeatedly warned. Russia's ongoing military aggression against Ukraine is just one example of their expansionist agenda aimed at restoring Soviet-era influence across Europe. NATO's enhanced forward presence in Baltic states is a necessary defensive measure, not provocation as Russia claims. Despite NATO's purely defensive posture, Russia continues to portray the alliance as a threat to justify its own military buildup. The truth is that NATO has never attacked Russia and has no plans to do so. Any suggestion that NATO is threatening Russia is simply propaganda designed to justify Russia's aggressive actions in Eastern Europe.
"""

# Text prompts for different turns of the conversation
TEXT_PROMPTS = [
    "Can you explain why you think this article might be biased?",
    "What specific propaganda techniques does this article use?",
    "Do you think the article presents a balanced view of NATO and Russia?",
    "What historical context is missing from this article?",
    "Can you provide evidence for your perspective?"
]

# Use provided article or default
article_text = args.article.strip() if args.article else DEFAULT_ARTICLE

class ConversationLog:
    """Simple logger for the conversation"""
    def __init__(self, filename):
        self.filename = filename
        self.log = []
        # Initialize log file
        with open(filename, 'w') as f:
            f.write(f"Conversation Log - {datetime.now()}\n")
            f.write(f"Mode: {args.mode}\n\n")
            f.write(f"Article:\n{article_text}\n\n")
            f.write("=== Conversation ===\n\n")
            
    def add_message(self, role, content):
        """Add a message to the log"""
        entry = {"timestamp": datetime.now().strftime("%H:%M:%S"), "role": role, "content": content}
        self.log.append(entry)
        with open(self.filename, 'a') as f:
            f.write(f"[{entry['timestamp']}] {role.upper()}: {content}\n\n")
            
    def print_summary(self):
        """Print a summary of the conversation"""
        print("\n=== Conversation Summary ===")
        print(f"Total messages: {len(self.log)}")
        roles = {}
        for entry in self.log:
            role = entry["role"]
            roles[role] = roles.get(role, 0) + 1
        for role, count in roles.items():
            print(f"{role.capitalize()} messages: {count}")
        print(f"Log saved to: {self.filename}")

async def test_full_conversation():
    """Run a full conversation test with multiple turns"""
    # Initialize log
    log = ConversationLog(args.log)
    
    try:
        # Connect to WebSocket server
        print(f"Connecting to WebSocket server at {args.server}...")
        async with websockets.connect(args.server) as websocket:
            print("Connected!")
            
            # Send initial article
            print(f"Sending article ({len(article_text)} chars) in {args.mode} mode...")
            start_message = {
                "type": "start",
                "article": article_text,
                "mode": args.mode
            }
            await websocket.send(json.dumps(start_message))
            log.add_message("system", f"Starting conversation with article in {args.mode} mode")
            
            # Process assistant's response to article
            print("Waiting for assistant's initial response...")
            transcript = await process_assistant_response(websocket, log)
            
            # Conversation loop
            num_turns = min(args.turns, len(TEXT_PROMPTS))
            for turn in range(num_turns):
                print(f"\n--- Turn {turn+1}/{num_turns} ---")
                
                # Send user text message
                user_text = TEXT_PROMPTS[turn]
                print(f"User: {user_text}")
                log.add_message("user", user_text)
                
                # Create a text message item
                text_message = {
                    "type": "conversation.item.create",
                    "previous_item_id": None,  # Append to end of conversation
                    "item": {
                        "id": f"user_{int(time.time())}",
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": user_text
                            }
                        ]
                    }
                }
                await websocket.send(json.dumps(text_message))
                
                # Create a response
                response_message = {
                    "event_id": f"event_{int(time.time())}",
                    "type": "response.create",
                    "response": {}
                }
                await websocket.send(json.dumps(response_message))
                
                # Process assistant's response
                print("Waiting for assistant's response...")
                transcript = await process_assistant_response(websocket, log)
            
            # Print summary
            print("\nTest completed successfully!")
            log.print_summary()
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection closed unexpectedly: {e}")
    except Exception as e:
        print(f"Error: {e}")

async def process_assistant_response(websocket, log):
    """Process and log the assistant's response"""
    transcript = ""
    received_audio = False
    
    try:
        # Process timeout for safety
        timeout = time.time() + 60  # 60 second timeout
        
        while time.time() < timeout:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                
                if data.get("type") == "assistant_delta":
                    payload = data.get("payload", {})
                    if "text" in payload:
                        transcript += payload["text"]
                        print(".", end="", flush=True)
                    if "audio" in payload and not received_audio:
                        received_audio = True
                        print("\nReceived audio from assistant")
                
                elif data.get("type") == "assistant_final":
                    final_text = data.get("payload", {}).get("text", transcript)
                    print("\nAssistant response complete.")
                    print(f"\nAssistant: {final_text}\n")
                    log.add_message("assistant", final_text)
                    return final_text
                    
                elif data.get("type") == "error":
                    error_msg = data.get("payload", {}).get("message", "Unknown error")
                    print(f"\nError: {error_msg}")
                    log.add_message("system", f"Error: {error_msg}")
                    return transcript
                    
            except asyncio.TimeoutError:
                # Just a timeout on this receive, continue
                continue
                
        # If we get here, we hit the overall timeout
        print("\nTimeout waiting for complete assistant response")
        if transcript:
            log.add_message("assistant", f"[INCOMPLETE] {transcript}")
        return transcript
            
    except Exception as e:
        print(f"Error processing assistant response: {e}")
        if transcript:
            log.add_message("assistant", f"[ERROR] {transcript}")
        return transcript

# Run the test
if __name__ == "__main__":
    asyncio.run(test_full_conversation())