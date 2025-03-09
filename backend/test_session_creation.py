#!/usr/bin/env python3
"""
Simple test script to verify OpenAI Realtime API session creation
"""

import os
import requests
import json

# Get API key from environment
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Configuration
REALTIME_MODEL = "gpt-4o-realtime"

def create_realtime_session():
    """
    Create a new OpenAI Realtime API session
    """
    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": REALTIME_MODEL,
        "modalities": ["audio", "text"],
        "voice": "alloy",  # Default voice
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "input_audio_transcription": {
            "model": "whisper-1"
        }
    }
    
    print(f"Creating session with payload: {json.dumps(payload, indent=2)}")
    print(f"Using API key ending with: ...{api_key[-5:]}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        session_data = response.json()
        session_id = session_data.get("id")
        client_secret = session_data.get("client_secret", {}).get("value")
        
        print(f"Session created successfully!")
        print(f"Session ID: {session_id}")
        print(f"Client secret: {client_secret[:5]}...")
        print(f"Voice: {session_data.get('voice')}")
        print(f"Model: {session_data.get('model')}")
        return True
    
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {response.text}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = create_realtime_session()
    if success:
        print("\nTest passed! Your API key can successfully create Realtime API sessions.")
    else:
        print("\nTest failed. Please check your API key and model availability.")