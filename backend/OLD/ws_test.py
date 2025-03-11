import asyncio
import json
import base64
import io
import wave
import numpy as np
import sounddevice as sd
import threading
import websockets
from pynput import keyboard

#########################################
# Global event for tracking space state #
#########################################

# This event will be set when space is pressed and cleared on release.
space_pressed = threading.Event()

def on_press(key):
    try:
        if key == keyboard.Key.space:
            space_pressed.set()
    except Exception as e:
        print("on_press error:", e)

def on_release(key):
    try:
        if key == keyboard.Key.space:
            space_pressed.clear()
    except Exception as e:
        print("on_release error:", e)

# Start the pynput keyboard listener in a separate thread.
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

#########################################################
# Asynchronous Audio Player for Real-Time Streaming     #
#########################################################

class AudioPlayerAsync:
    def __init__(self, sample_rate=24000, channels=1, block_size=480):
        # block_size: number of frames per callback (~20ms of audio)
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size
        self.queue = []  # holds PCM audio chunks as NumPy arrays
        self.lock = threading.Lock()
        self.pcm_format = None  # to store format info if a WAV header is detected

        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='int16',
            blocksize=self.block_size,
            callback=self.callback
        )
        self.stream.start()
        print("Audio output stream started.")

    def callback(self, outdata, frames, time, status):
        with self.lock:
            if self.queue:
                data = self.queue.pop(0)
                # If the chunk is larger than needed, output only the first 'frames' frames
                if len(data) > frames:
                    outchunk = data[:frames]
                    remainder = data[frames:]
                    self.queue.insert(0, remainder)
                elif len(data) < frames:
                    outchunk = np.pad(data, (0, frames - len(data)), mode='constant')
                else:
                    outchunk = data
            else:
                outchunk = np.zeros(frames, dtype=np.int16)
        outdata[:] = outchunk.reshape(-1, self.channels)

    def add_data(self, data: bytes):
        # Check if the data appears to be a WAV file (by checking for "RIFF" header)
        if data[:4] == b'RIFF':
            audio_buffer = io.BytesIO(data)
            try:
                with wave.open(audio_buffer, 'rb') as wf:
                    if self.pcm_format is None:
                        self.pcm_format = {
                            'channels': wf.getnchannels(),
                            'sample_rate': wf.getframerate(),
                            'sample_width': wf.getsampwidth()
                        }
                        print("Parsed WAV header:", self.pcm_format)
                    pcm_data = wf.readframes(wf.getnframes())
                np_data = np.frombuffer(pcm_data, dtype=np.int16)
            except Exception as e:
                print("Error processing WAV data:", e)
                return
        else:
            # Otherwise, assume raw PCM.
            np_data = np.frombuffer(data, dtype=np.int16)
        with self.lock:
            self.queue.append(np_data)
            print("Audio chunk added; current queue length:", len(self.queue))

    def stop(self):
        self.stream.stop()
        self.stream.close()
        print("Audio stream stopped.")

#########################################################
# Function to Record Audio While Space is Pressed       #
#########################################################

async def record_and_send_audio_while_space(ws):
    sample_rate = 24000
    channels = 1
    print("Space pressed: Recording started...")

    recorded_frames = []

    # Define a callback to accumulate audio data.
    def audio_callback(indata, frames, time, status):
        recorded_frames.append(indata.copy())

    # Open an input stream to record audio.
    stream = sd.InputStream(channels=channels, samplerate=sample_rate, dtype='int16', callback=audio_callback)
    try:
        stream.start()
        # Record until the space bar is released.
        while space_pressed.is_set():
            await asyncio.sleep(0.01)
    finally:
        stream.stop()
        stream.close()
    print("Space released: Recording stopped.")

    # Concatenate recorded chunks.
    if recorded_frames:
        audio_array = np.concatenate(recorded_frames, axis=0)
    else:
        audio_array = np.empty((0, channels), dtype=np.int16)

    # Write the recording to an in-memory WAV file.
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(audio_array.tobytes())
    audio_bytes = buffer.getvalue()
    b64_audio = base64.b64encode(audio_bytes).decode('utf-8')

    # Create and send a JSON message with the recorded audio.
    message = {
        "type": "user",
        "content": [
            {
                "type": "input_audio",
                "input_audio": {
                    "data": b64_audio,
                    "format": "wav"
                }
            }
        ]
    }
    await ws.send(json.dumps(message))
    print("Audio message sent.")

#########################################################
# Function to Monitor Space for Recording (Using pynput)  #
#########################################################

async def monitor_space_for_recording(ws):
    while True:
        # If space is pressed, record until it's released.
        if space_pressed.is_set():
            await record_and_send_audio_while_space(ws)
        await asyncio.sleep(0.1)

#########################################################
# Function to Read Text Messages from Console           #
#########################################################

async def read_text_message(ws):
    while True:
        text = await asyncio.to_thread(input, "Enter text message (or just press Enter to skip): ")
        if text.strip():
            message = {
                "type": "user",
                "content": [{"type": "text", "text": text}]
            }
            await ws.send(json.dumps(message))
            print("Text message sent.")

#########################################################
# WebSocket Client for Real-Time Streaming              #
#########################################################

async def connect_and_run():
    uri = "ws://localhost:8000/ws/conversation"
    extra_headers = {"Cookie": "session_id=test-session-123"}

    # Instantiate the realtime audio player.
    audio_player = AudioPlayerAsync(sample_rate=24000, channels=1, block_size=int(24000 * 0.02))

    async with websockets.connect(uri, extra_headers=extra_headers) as ws:
        # Send the initial start message with your article.
        start_message = {
            "type": "start",
            "article": "This is a test article to analyze propaganda content."
        }
        await ws.send(json.dumps(start_message))
        print("Start message sent; waiting for assistant response...")

        # Start background tasks: one for monitoring the space bar, one for reading text messages.
        monitor_space_task = asyncio.create_task(monitor_space_for_recording(ws))
        read_text_task = asyncio.create_task(read_text_message(ws))

        # Listen for incoming messages from the server.
        while True:
            try:
                msg = await ws.recv()
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed.")
                break

            data = json.loads(msg)
            msg_type = data.get("type")
            payload = data.get("payload")
            if msg_type == "assistant_delta":
                if "text" in payload:
                    print("Text delta:", payload["text"])
                if "audio" in payload:
                    try:
                        audio_bytes = base64.b64decode(payload["audio"])
                        audio_player.add_data(audio_bytes)
                        print("Audio delta processed.")
                    except Exception as e:
                        print("Error processing audio delta:", e)
            elif msg_type == "assistant_final":
                print("Final message from assistant:", payload)
            else:
                print("Received message:", data)

        # Cancel background tasks if the connection is closed.
        monitor_space_task.cancel()
        read_text_task.cancel()
        audio_player.stop()

# Outer loop to automatically reconnect if the connection closes.
async def run_client():
    while True:
        try:
            await connect_and_run()
        except Exception as e:
            print("Error in connection:", e)
        print("Reconnecting in 1 second...")
        await asyncio.sleep(1)

asyncio.run(run_client())
