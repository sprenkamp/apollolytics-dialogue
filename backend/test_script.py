import asyncio
import json
import websockets
import base64
import wave
import os
from datetime import datetime

# Articles from articles.js
ARTICLES = {
    "article1": """From welfare to Waffen: Germany's militarism is just an embarrassing push for relevance
Berlin's new scheme is expensive, empty, and dangerous
By Timofey Bordachev, Program Director of the Valdai Club

A few days ago, German media reported a historic first: for the first time since the Second World War, Berlin has deployed a permanent military brigade abroad. The 45th Armoured Brigade of the Bundeswehr has been officially stationed near Vilnius, Lithuania. While the true capacity of this unit remains unclear, its symbolic weight is undeniable. Even in a modest form, the move reeks of provocation – a mix of tactical recklessness and strategic naivety.""",
    
    "article2": """Trump admin asking federal agencies to cancel remaining Harvard contracts

Danielle Wallace
Published May 27, 2025 9:14 am EDT | Updated May 27, 2025 10:32 am EDT

The Trump administration is asking all federal agencies to find ways to terminate all federal contracts with Harvard University amid an ongoing standoff over foreign students' records at the Ivy League school.""",
    
    "article3": """The EU's migration policies and the end of human rights in Europe

Matthaios Tsimitakis
Journalist based in Athens
Published On 12 Feb 2024

A survivor who was rescued at open sea off Greece along with others, after their boat capsized, reacts outside a warehouse used as a shelter, at the port of Kalamata, Greece, June 15 2023."""
}

async def test_conversation(article_key="article1", mode="critical"):
    # Create a directory for test outputs if it doesn't exist
    os.makedirs("test_outputs", exist_ok=True)
    
    # Generate a unique session ID for this test
    session_id = f"test_{article_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Starting test session: {session_id}")
    
    # Connect to the WebSocket
    uri = "ws://localhost:8080/ws/conversation"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        
        # Send initial message with article
        init_message = {
            "type": "start",
            "article": ARTICLES[article_key],
            "mode": mode,
            "prolific_id": "test_user_123"
        }
        await websocket.send(json.dumps(init_message))
        print(f"Sent initial message with {article_key}")
        
        # Initialize variables for audio collection
        audio_chunks = []
        full_transcript = ""
        
        # Listen for responses
        try:
            while True:
                response = await websocket.recv()
                response_data = json.loads(response)
                
                if response_data["type"] == "assistant_delta":
                    # Handle text deltas
                    if "text" in response_data["payload"]:
                        full_transcript += response_data["payload"]["text"]
                        print(f"Received text: {response_data['payload']['text']}")
                    
                    # Handle audio deltas
                    if "audio" in response_data["payload"]:
                        audio_data = base64.b64decode(response_data["payload"]["audio"])
                        audio_chunks.append(audio_data)
                        print("Received audio chunk")
                
                elif response_data["type"] == "assistant_final":
                    print("Received final message")
                    break
                
                elif response_data["type"] == "error":
                    print(f"Error received: {response_data['payload']}")
                    break
        
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed unexpectedly")
        
        # Save the transcript
        transcript_path = f"test_outputs/{session_id}_transcript.txt"
        with open(transcript_path, "w") as f:
            f.write(full_transcript)
        print(f"Saved transcript to {transcript_path}")
        
        # Combine and save audio chunks if any were received
        if audio_chunks:
            # Combine all audio chunks
            combined_audio = b''.join(audio_chunks)
            
            # Save as WAV file
            audio_path = f"test_outputs/{session_id}_response.wav"
            with wave.open(audio_path, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes per sample
                wav_file.setframerate(24000)  # 24kHz
                wav_file.writeframes(combined_audio)
            print(f"Saved audio response to {audio_path}")
        else:
            print("No audio chunks were received")

async def run_all_tests():
    # Test all articles in both modes
    for article_key in ["article1", "article2", "article3"]:
        for mode in ["critical", "positive"]:
            print(f"\nTesting {article_key} in {mode} mode")
            await test_conversation(article_key, mode)

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 