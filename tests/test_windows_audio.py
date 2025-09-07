#!/usr/bin/env python3
"""
Test Windows audio capture with improved device selection
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from localcaption.audio.capture import AudioCapture
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_audio_capture():
    """Test audio capture with improved device selection"""
    print("Testing Windows Audio Capture")
    print("=" * 40)
    
    # Create audio capture instance
    audio_capture = AudioCapture()
    
    # Test device selection
    print("\n1. Testing device selection...")
    default_device = audio_capture.get_default_loopback_device()
    if default_device is not None:
        print(f"✓ Selected device: {default_device}")
        
        # Test device validation
        print("\n2. Testing device validation...")
        if audio_capture._validate_device(default_device):
            print(f"✓ Device {default_device} is valid")
            
            # Test actual audio capture
            print("\n3. Testing audio capture...")
            audio_data_received = []
            
            def audio_callback(audio_data):
                audio_data_received.append(len(audio_data))
                if len(audio_data_received) <= 5:  # Log first few chunks
                    print(f"  Received audio chunk: {len(audio_data)} samples")
            
            try:
                success = audio_capture.start_capture(callback=audio_callback)
                if success:
                    print("✓ Audio capture started successfully")
                    
                    # Capture for 2 seconds
                    time.sleep(2)
                    
                    audio_capture.stop_capture()
                    print(f"✓ Audio capture stopped. Received {len(audio_data_received)} chunks")
                    
                    if audio_data_received:
                        print(f"  Average chunk size: {sum(audio_data_received) / len(audio_data_received):.1f} samples")
                        print("✓ Audio capture test PASSED!")
                    else:
                        print("⚠️  No audio data received")
                else:
                    print("✗ Failed to start audio capture")
            except Exception as e:
                print(f"✗ Error during audio capture: {e}")
        else:
            print(f"✗ Device {default_device} is not valid")
    else:
        print("✗ No suitable device found")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_audio_capture()
