import asyncio
import websockets
import json
import base64
import sys
from websockets.exceptions import ConnectionClosed

async def test_websocket():
    uri = "ws://localhost:8000/ws/conversation"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket server")

            # Read the article
            with open("demo_article/left_leaning/USAID_BBC.txt", "r") as f:
                article = f.read()

            # Send initial message with article
            start_message = {
                "type": "start",
                "article": article,
                "mode": "critical"
            }
            await websocket.send(json.dumps(start_message))
            print("Sent article")

            # Wait for initial responses
            try:
                while True:
                    try:
                        response = await websocket.recv()
                        response_data = json.loads(response)
                        print(f"\nReceived message type: {response_data.get('type')}")
                        
                        if response_data.get("type") == "error":
                            print(f"Error from server: {response_data.get('payload', {}).get('message')}")
                            continue
                            
                        if response_data.get("type") == "assistant_delta":
                            if "text" in response_data.get("payload", {}):
                                print(f"Assistant delta: {response_data['payload']['text']}", end="", flush=True)
                            continue
                            
                        if response_data.get("type") == "assistant_final":
                            print(f"\nAssistant final: {response_data.get('payload', {}).get('text')}")
                            break
                            
                    except json.JSONDecodeError:
                        print(f"Received non-JSON response: {response}")
                        continue
                        
            except ConnectionClosed:
                print("Connection closed by server during initial response")
                return
            except Exception as e:
                print(f"Error receiving initial responses: {e}")
                return

            print("\nSending audio file...")
            # Read and send audio file
            try:
                with open("temp_audio.wav", "rb") as f:
                    audio_data = base64.b64encode(f.read()).decode('utf-8')

                audio_message = {
                    "type": "user",
                    "content": [{
                        "type": "input_audio",
                        "input_audio": {
                            "format": "wav",
                            "data": audio_data
                        }
                    }]
                }
                await websocket.send(json.dumps(audio_message))
                print("Sent audio")

                # Wait for responses
                while True:
                    try:
                        response = await websocket.recv()
                        response_data = json.loads(response)
                        print(f"\nReceived message type: {response_data.get('type')}")
                        
                        if response_data.get("type") == "error":
                            print(f"Error from server: {response_data.get('payload', {}).get('message')}")
                            continue
                            
                        if response_data.get("type") == "assistant_delta":
                            if "text" in response_data.get("payload", {}):
                                print(f"Assistant delta: {response_data['payload']['text']}", end="", flush=True)
                            continue
                            
                        if response_data.get("type") == "assistant_final":
                            print(f"\nAssistant final: {response_data.get('payload', {}).get('text')}")
                            print("\nConversation complete!")
                            return
                            
                    except json.JSONDecodeError:
                        print(f"Received non-JSON response: {response}")
                        continue
                    except ConnectionClosed:
                        print("Connection closed by server")
                        return
                    except Exception as e:
                        print(f"Error receiving response: {e}")
                        return

            except FileNotFoundError:
                print("Error: Could not find temp_audio.wav file")
            except Exception as e:
                print(f"Error processing audio: {e}")

    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_websocket()) 