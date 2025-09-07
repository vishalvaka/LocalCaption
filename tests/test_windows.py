#!/usr/bin/env python3
"""
Test script for Windows to debug LocalCaption issues
"""

import sys
import os
import traceback
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test if all modules can be imported"""
    print("Testing imports...")
    
    try:
        import sounddevice as sd
        print("✓ sounddevice imported")
    except Exception as e:
        print(f"✗ sounddevice import failed: {e}")
        return False
    
    try:
        import sherpa_onnx
        print("✓ sherpa-onnx imported")
    except Exception as e:
        print(f"✗ sherpa-onnx import failed: {e}")
        return False
    
    try:
        from PyQt6 import QtWidgets
        print("✓ PyQt6 imported")
    except Exception as e:
        print(f"✗ PyQt6 import failed: {e}")
        return False
    
    try:
        from localcaption.audio.capture import AudioCapture
        print("✓ AudioCapture imported")
    except Exception as e:
        print(f"✗ AudioCapture import failed: {e}")
        return False
    
    try:
        from localcaption.asr.engine import ASREngine, ModelManager
        print("✓ ASREngine imported")
    except Exception as e:
        print(f"✗ ASREngine import failed: {e}")
        return False
    
    return True

def test_audio_devices():
    """Test audio devices on Windows"""
    print("\nTesting audio devices...")
    
    try:
        import sounddevice as sd
        
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
        except Exception as e:
            print(f"Default device error: {e}")
        
        return len(devices) > 0
        
    except Exception as e:
        print(f"Error testing audio devices: {e}")
        traceback.print_exc()
        return False

def test_asr_engine():
    """Test ASR engine initialization"""
    print("\nTesting ASR engine...")
    
    try:
        from localcaption.asr.engine import ASREngine, ModelManager
        
        # Check if model exists
        model_config = ModelManager.get_model_config('zipformer_bilingual')
        if not model_config:
            print("❌ No model config found")
            return False
        
        print(f"✓ Model config found: {model_config['config_file']}")
        
        # Check if model files exist
        model_dir = os.path.dirname(model_config['config_file'])
        required_files = [
            "encoder-epoch-99-avg-1.onnx",
            "decoder-epoch-99-avg-1.onnx", 
            "joiner-epoch-99-avg-1.onnx",
            "tokens.txt",
            "bpe.model",
            "bpe.vocab"
        ]
        
        for file in required_files:
            file_path = os.path.join(model_dir, file)
            if os.path.exists(file_path):
                print(f"✓ Found {file}")
            else:
                print(f"❌ Missing {file}")
                return False
        
        # Try to initialize ASR engine
        print("Initializing ASR engine...")
        asr_engine = ASREngine(model_config)
        if asr_engine.initialize():
            print("✓ ASR engine initialized successfully!")
            asr_engine.stop_recognition()
            return True
        else:
            print("❌ ASR engine initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing ASR: {e}")
        traceback.print_exc()
        return False

def test_audio_capture():
    """Test audio capture"""
    print("\nTesting audio capture...")
    
    try:
        from localcaption.audio.capture import AudioCapture
        
        capture = AudioCapture()
        
        # Test device enumeration
        devices = capture.get_audio_devices()
        print(f"✓ Found {len(devices)} audio devices")
        
        # Test availability
        if capture.is_available():
            print("✓ Audio capture is available")
        else:
            print("⚠ Audio capture not available")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing audio capture: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("LocalCaption Windows Debug Test")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Audio Devices", test_audio_devices),
        ("Audio Capture", test_audio_capture),
        ("ASR Engine", test_asr_engine),
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
        print("✓ All tests passed! LocalCaption should work.")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
