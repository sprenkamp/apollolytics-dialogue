#!/usr/bin/env python3
"""
Generate a test WAV file for testing the Realtime API integration
This creates a simple sine wave audio file that can be used with test_realtime_api.py
"""

import numpy as np
import wave
import struct
import argparse

# Command line arguments
parser = argparse.ArgumentParser(description='Generate a test WAV file')
parser.add_argument('--filename', default='test.wav', help='Output filename (default: test.wav)')
parser.add_argument('--duration', type=float, default=3.0, help='Duration in seconds (default: 3.0)')
parser.add_argument('--frequency', type=int, default=440, help='Frequency in Hz (default: 440)')
parser.add_argument('--sample-rate', type=int, default=24000, help='Sample rate (default: 24000)')
args = parser.parse_args()

def generate_wav_file(filename, duration=3.0, freq=440, sample_rate=24000):
    """
    Generate a WAV file with a sine wave
    
    Args:
        filename: Output WAV file path
        duration: Length of the audio in seconds
        freq: Frequency of the sine wave in Hz
        sample_rate: Sample rate in Hz
    """
    print(f"Generating {duration}s test WAV file at {sample_rate}Hz...")
    
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio_data = np.sin(2 * np.pi * freq * t)
    
    # Apply fade in/out to avoid clicks
    fade_duration = min(0.1, duration/10)
    fade_samples = int(fade_duration * sample_rate)
    
    # Fade in
    if fade_samples > 0:
        fade_in = np.linspace(0, 1, fade_samples)
        audio_data[:fade_samples] *= fade_in
        
        # Fade out
        fade_out = np.linspace(1, 0, fade_samples)
        audio_data[-fade_samples:] *= fade_out
    
    # Scale to int16 range
    audio_data = audio_data * 32767
    audio_data = audio_data.astype(np.int16)
    
    # Write WAV file
    with wave.open(filename, 'w') as wav_file:
        # Set WAV file parameters:
        # nchannels (1 for mono), sampwidth (2 bytes for int16), framerate, nframes (0 for now)
        wav_file.setparams((1, 2, sample_rate, 0, 'NONE', 'not compressed'))
        
        # Convert audio data to byte string
        packed_audio = struct.pack('<%dh' % len(audio_data), *audio_data)
        wav_file.writeframes(packed_audio)
    
    print(f"Successfully created {filename}")
    print(f"Parameters: {sample_rate}Hz sample rate, {freq}Hz frequency, {duration}s duration")

if __name__ == "__main__":
    generate_wav_file(
        args.filename, 
        duration=args.duration, 
        freq=args.frequency,
        sample_rate=args.sample_rate
    )