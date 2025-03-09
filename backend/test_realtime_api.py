#!/usr/bin/env python3
"""
Test script for OpenAI Realtime API integration
This script tests the ws_speech_real-time.py WebSocket server implementation
by connecting to it and simulating both text and audio interactions
"""

import asyncio
import base64
import json
import os
import uuid
import sys
import argparse
import websockets
import requests
import time
from pathlib import Path

# Command line arguments
parser = argparse.ArgumentParser(description='Test the OpenAI Realtime API integration')
parser.add_argument('--server', default='ws://localhost:8000/ws/conversation', 
                   help='WebSocket server URL (default: ws://localhost:8000/ws/conversation)')
parser.add_argument('--mode', default='critical', choices=['critical', 'supportive'],
                   help='Dialogue mode (default: critical)')
parser.add_argument('--audio', action='store_true',
                   help='Test with audio input (requires a test.wav file)')
parser.add_argument('--test-audio-path', default='test.wav',
                   help='Path to test audio file (default: test.wav)')
parser.add_argument('--article', default='',
                   help='Article text for testing. If not provided, a default will be used.')
args = parser.parse_args()

# Default test article if none provided
DEFAULT_ARTICLE = """
The threat from Russia is clear and present, as NATO officials have repeatedly warned. Russia's ongoing military aggression against Ukraine is just one example of their expansionist agenda aimed at restoring Soviet-era influence across Europe. NATO's enhanced forward presence in Baltic states is a necessary defensive measure, not provocation as Russia claims. Despite NATO's purely defensive posture, Russia continues to portray the alliance as a threat to justify its own military buildup. The truth is that NATO has never attacked Russia and has no plans to do so. Any suggestion that NATO is threatening Russia is simply propaganda designed to justify Russia's aggressive actions in Eastern Europe.
"""

# Use provided article or default
article_text = args.article.strip() if args.article else DEFAULT_ARTICLE

print(f"Testing Realtime API integration with server: {args.server}")
print(f"Mode: {args.mode}")

async def read_audio_file(file_path):
    """Read and encode audio file to base64"""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: Audio file {file_path} not found")
        sys.exit(1)
        
    try:
        with open(file_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            return base64.b64encode(audio_bytes).decode('utf-8')
    except Exception as e:
        print(f"Error reading audio file: {e}")
        sys.exit(1)

async def test_websocket():
    """Connect to WebSocket server and test interactions"""
    try:
        # Connect to WebSocket server
        print("Connecting to WebSocket server...")
        async with websockets.connect(args.server) as websocket:
            print("Connected!")
            
            # Send initial article
            print(f"Sending article (length: {len(article_text)} chars) in {args.mode} mode...")
            start_message = {
                "type": "start",
                "article": article_text,
                "mode": args.mode
            }
            await websocket.send(json.dumps(start_message))
            
            # Process assistant's response to article
            print("Waiting for assistant response...")
            transcript = ""
            received_audio = False
            
            # Process initial response
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
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
                        print("\nAssistant response complete.")
                        print(f"\nFinal transcript: \n{transcript}\n")
                        break
                        
                    elif data.get("type") == "error":
                        print(f"\nError: {data.get('payload', {}).get('message', 'Unknown error')}")
                        return
                        
                except asyncio.TimeoutError:
                    print("\nTimeout waiting for assistant response")
                    break
            
            # Test with audio input if requested
            if args.audio:
                print(f"Testing audio input using file: {args.test_audio_path}")
                audio_base64 = await read_audio_file(args.test_audio_path)
                
                # Send audio message
                audio_message = {
                    "type": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "format": "wav",
                                "data": audio_base64
                            }
                        }
                    ]
                }
                await websocket.send(json.dumps(audio_message))
                print("Audio sent, waiting for transcription and response...")
                
                # Process response to audio
                user_transcript = ""
                assistant_transcript = ""
                received_audio = False
                saw_user_transcript = False
                
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        data = json.loads(response)
                        
                        if data.get("type") == "user_transcript":
                            user_transcript = data.get("payload", {}).get("transcript", "")
                            print(f"\nUser audio transcribed: {user_transcript}")
                            saw_user_transcript = True
                            
                        elif data.get("type") == "assistant_delta":
                            payload = data.get("payload", {})
                            if "text" in payload:
                                assistant_transcript += payload["text"]
                                print(".", end="", flush=True)
                            if "audio" in payload and not received_audio:
                                received_audio = True
                                print("\nReceived audio response from assistant")
                        
                        elif data.get("type") == "assistant_final":
                            print("\nAssistant response to audio complete.")
                            print(f"\nFinal assistant transcript: \n{assistant_transcript}\n")
                            break
                            
                        elif data.get("type") == "error":
                            print(f"\nError: {data.get('payload', {}).get('message', 'Unknown error')}")
                            break
                            
                    except asyncio.TimeoutError:
                        print("\nTimeout waiting for response to audio")
                        break
                
                if not saw_user_transcript:
                    print("Warning: Did not receive user transcript - audio transcription may have failed")
            
            print("Test completed successfully!")
            
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection closed unexpectedly: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_websocket())