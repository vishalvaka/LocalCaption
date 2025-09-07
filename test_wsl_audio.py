#!/usr/bin/env python3
"""
Test WSL audio setup and LocalCaption functionality
"""

import sys
import os
import time
import numpy as np
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_audio_devices():
    """Test available audio devices"""
    print("Testing audio devices...")
    
    try:
        import sounddevice as sd
        
        # List all devices
        devices = sd.query_devices()
        print(f"Found {len(devices)} audio devices:")
        
        for i, device in enumerate(devices):
            print(f"  {i}: {device['name']} - {device['max_input_channels']} inputs, {device['max_output_channels']} outputs")
        
        # Test default device
        try:
            default_input = sd.default.device[0]
            default_output = sd.default.device[1]
            print(f"Default input: {default_input}")
            print(f"Default output: {default_output}")
        except:
            print("No default devices available")
        
        return len(devices) > 0
        
    except Exception as e:
        print(f"Error testing audio devices: {e}")
        return False

def test_audio_capture():
    """Test audio capture with simulated data"""
    print("\nTesting audio capture with simulated data...")
    
    try:
        from localcaption.audio.capture import AudioCapture
        
        capture = AudioCapture()
        
        # Test with simulated audio data
        def test_callback(audio_data):
            print(f"Received audio data: {len(audio_data)} samples, max: {np.max(audio_data):.3f}")
        
        # Simulate audio data
        sample_rate = 16000
        duration = 1.0
        frequency = 440.0  # A4 note
        
        # Generate sine wave
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        # Test audio processing
        from localcaption.audio.capture import AudioProcessor
        
        # Test normalization
        normalized = AudioProcessor.normalize_audio(audio_data)
        print(f"Normalized audio: max={np.max(normalized):.3f}")
        
        # Test VAD
        has_voice = AudioProcessor.apply_vad(audio_data, threshold=0.1)
        print(f"Voice activity detected: {has_voice}")
        
        # Test resampling
        resampled = AudioProcessor.resample_audio(audio_data, sample_rate, 8000)
        print(f"Resampled audio: {len(resampled)} samples")
        
        return True
        
    except Exception as e:
        print(f"Error testing audio capture: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_asr_with_simulated_audio():
    """Test ASR with simulated audio data"""
    print("\nTesting ASR with simulated audio data...")
    
    try:
        from localcaption.asr.engine import ASREngine, ModelManager
        
        # Get model config
        model_config = ModelManager.get_model_config('zipformer_bilingual')
        if not model_config:
            print("❌ No model config found")
            return False
        
        # Initialize ASR engine
        asr_engine = ASREngine(model_config)
        if not asr_engine.initialize():
            print("❌ ASR engine initialization failed")
            return False
        
        print("✓ ASR engine initialized successfully")
        
        # Test with simulated audio
        def asr_callback(text):
            print(f"ASR Result: {text}")
        
        asr_engine.start_recognition(callback=asr_callback)
        
        # Generate test audio (sine wave)
        sample_rate = 16000
        duration = 2.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        # Convert to int16 for ASR
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # Add audio to ASR
        asr_engine.add_audio(audio_int16)
        
        # Wait a bit for processing
        time.sleep(1.0)
        
        asr_engine.stop_recognition()
        print("✓ ASR test completed")
        
        return True
        
    except Exception as e:
        print(f"Error testing ASR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all WSL audio tests"""
    print("WSL Audio Setup Test")
    print("=" * 40)
    
    tests = [
        ("Audio Devices", test_audio_devices),
        ("Audio Capture (Simulated)", test_audio_capture),
        ("ASR Engine (Simulated)", test_asr_with_simulated_audio),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            print(f"✓ {test_name} passed")
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! LocalCaption is ready to use.")
        print("\nNext steps:")
        print("1. Set up audio bridge (see WSL_AUDIO_SETUP.md)")
        print("2. Or run the Windows executable directly")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
