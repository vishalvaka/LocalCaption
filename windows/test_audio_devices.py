#!/usr/bin/env python3
"""
Windows Audio Device Test Script
Tests audio device enumeration and validation on Windows
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sounddevice as sd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_audio_devices():
    """Test audio device enumeration and validation"""
    print("Windows Audio Device Test")
    print("=" * 40)
    
    try:
        # Get all devices
        print("\n1. Enumerating all audio devices...")
        devices = sd.query_devices()
        print(f"Found {len(devices)} total devices:")
        
        input_devices = []
        for i, device in enumerate(devices):
            device_type = []
            if device['max_input_channels'] > 0:
                device_type.append("INPUT")
                input_devices.append(i)
            if device['max_output_channels'] > 0:
                device_type.append("OUTPUT")
            
            print(f"  [{i:2d}] {device['name']}")
            print(f"       Type: {'/'.join(device_type) if device_type else 'NONE'}")
            print(f"       Input channels: {device['max_input_channels']}")
            print(f"       Output channels: {device['max_output_channels']}")
            print(f"       Sample rate: {device['default_samplerate']}")
            print(f"       Host API: {device['hostapi']}")
            print()
        
        # Test input devices
        print(f"\n2. Testing {len(input_devices)} input devices...")
        working_devices = []
        
        for device_idx in input_devices:
            device = devices[device_idx]
            print(f"\nTesting device {device_idx}: {device['name']}")
            
            try:
                # Test device validation
                test_stream = sd.InputStream(
                    device=device_idx,
                    channels=1,
                    samplerate=16000,
                    blocksize=64,
                    dtype='float32'
                )
                test_stream.close()
                print(f"  ✓ Device {device_idx} is accessible")
                working_devices.append(device_idx)
                
            except Exception as e:
                print(f"  ✗ Device {device_idx} failed: {e}")
        
        # Test default devices
        print(f"\n3. Testing default devices...")
        try:
            default_input = sd.default.device[0]
            print(f"Default input device: {default_input}")
            if default_input in working_devices:
                print("  ✓ Default input device is working")
            else:
                print("  ✗ Default input device is not working")
        except Exception as e:
            print(f"  ✗ Could not get default input device: {e}")
        
        # Test WASAPI specifically
        print(f"\n4. Testing WASAPI...")
        try:
            sd.default.api = 'wasapi'
            print("  ✓ WASAPI API is available")
            
            # Try to get WASAPI devices
            wasapi_devices = sd.query_devices(api='wasapi')
            print(f"  Found {len(wasapi_devices)} WASAPI devices")
            
        except Exception as e:
            print(f"  ✗ WASAPI not available: {e}")
        
        # Summary
        print(f"\n5. Summary:")
        print(f"  Total devices: {len(devices)}")
        print(f"  Input devices: {len(input_devices)}")
        print(f"  Working input devices: {len(working_devices)}")
        
        if working_devices:
            print(f"  Recommended device: {working_devices[0]} ({devices[working_devices[0]]['name']})")
        else:
            print("  ⚠️  No working input devices found!")
            print("     This may be due to:")
            print("     - No audio devices connected")
            print("     - Audio drivers not installed")
            print("     - Audio device permissions")
            print("     - Device already in use by another application")
        
    except Exception as e:
        print(f"Error during audio device test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_audio_devices()
