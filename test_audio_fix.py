#!/usr/bin/env python3
"""
Test script to verify audio capture fixes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from localcaption.audio.capture import AudioCapture
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_audio_capture():
    """Test audio capture functionality"""
    print("Testing AudioCapture...")
    
    # Create audio capture instance
    audio_capture = AudioCapture()
    
    # Test device enumeration
    print("\n1. Testing device enumeration...")
    devices = audio_capture.get_audio_devices()
    print(f"Found {len(devices)} audio devices:")
    for device in devices:
        print(f"  - {device['name']} (channels: {device['channels']}, loopback: {device['is_loopback']})")
    
    # Test default device selection
    print("\n2. Testing default device selection...")
    default_device = audio_capture.get_default_loopback_device()
    if default_device is not None:
        print(f"Default loopback device: {default_device}")
    else:
        print("No default loopback device found")
    
    # Test audio capture (brief test)
    print("\n3. Testing audio capture...")
    def audio_callback(audio_data):
        print(f"Received audio data: {len(audio_data)} samples")
    
    try:
        success = audio_capture.start_capture(callback=audio_callback)
        if success:
            print("✓ Audio capture started successfully")
            import time
            time.sleep(1)  # Capture for 1 second
            audio_capture.stop_capture()
            print("✓ Audio capture stopped successfully")
        else:
            print("✗ Failed to start audio capture")
    except Exception as e:
        print(f"✗ Error during audio capture test: {e}")
    
    print("\nAudio capture test completed!")

if __name__ == "__main__":
    test_audio_capture()
