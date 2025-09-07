#!/usr/bin/env python3
"""
Simple test script for LocalCaption
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test if all modules can be imported"""
    print("Testing imports...")
    
    try:
        from localcaption.audio.capture import AudioCapture, AudioProcessor
        print("✓ Audio capture module imported")
    except ImportError as e:
        print(f"✗ Audio capture import failed: {e}")
        return False
    
    try:
        from localcaption.asr.engine import ASREngine, ModelManager
        print("✓ ASR engine module imported")
    except ImportError as e:
        print(f"✗ ASR engine import failed: {e}")
        return False
    
    try:
        from localcaption.utils.export import TranscriptExporter
        print("✓ Export utilities imported")
    except ImportError as e:
        print(f"✗ Export utilities import failed: {e}")
        return False
    
    try:
        from localcaption.utils.performance import PerformanceMonitor
        print("✓ Performance monitoring imported")
    except ImportError as e:
        print(f"✗ Performance monitoring import failed: {e}")
        return False
    
    return True

def test_audio_capture():
    """Test audio capture functionality"""
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
            print("⚠ Audio capture not available (may need audio drivers)")
        
        return True
        
    except Exception as e:
        print(f"✗ Audio capture test failed: {e}")
        return False

def test_asr_engine():
    """Test ASR engine functionality"""
    print("\nTesting ASR engine...")
    
    try:
        from localcaption.asr.engine import ModelManager, create_default_config
        
        # Test model manager
        available_models = ModelManager.list_available_models()
        print(f"✓ Found {len(available_models)} available models: {available_models}")
        
        # Test default config
        config = create_default_config()
        print(f"✓ Default config created: {config['model_name']}")
        
        return True
        
    except Exception as e:
        print(f"✗ ASR engine test failed: {e}")
        return False

def test_export_utilities():
    """Test export utilities"""
    print("\nTesting export utilities...")
    
    try:
        from localcaption.utils.export import TranscriptExporter, export_simple_txt
        
        # Test simple export
        test_text = "This is a test transcript."
        success = export_simple_txt(test_text, "test_output.txt")
        
        if success and os.path.exists("test_output.txt"):
            print("✓ Simple text export works")
            os.remove("test_output.txt")  # Clean up
        else:
            print("✗ Simple text export failed")
            return False
        
        # Test transcript exporter
        exporter = TranscriptExporter()
        exporter.start_recording()
        exporter.add_segment("Test segment 1")
        exporter.add_segment("Test segment 2")
        
        success = exporter.export_txt("test_transcript.txt")
        if success and os.path.exists("test_transcript.txt"):
            print("✓ Transcript exporter works")
            os.remove("test_transcript.txt")  # Clean up
        else:
            print("✗ Transcript exporter failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Export utilities test failed: {e}")
        return False

def test_performance_monitoring():
    """Test performance monitoring"""
    print("\nTesting performance monitoring...")
    
    try:
        from localcaption.utils.performance import PerformanceMonitor, LatencyTracker
        
        # Test performance monitor
        monitor = PerformanceMonitor()
        monitor.start_monitoring(interval=0.1)
        
        import time
        time.sleep(0.5)  # Let it collect some data
        
        stats = monitor.get_current_stats()
        print(f"✓ Performance monitoring works - CPU: {stats['cpu_percent']:.1f}%")
        
        monitor.stop_monitoring()
        
        # Test latency tracker
        tracker = LatencyTracker()
        timing_id = tracker.start_timing("test_operation")
        time.sleep(0.01)  # Simulate some work
        duration = tracker.end_timing(timing_id)
        
        if duration is not None:
            print(f"✓ Latency tracking works - measured: {duration*1000:.1f}ms")
        else:
            print("✗ Latency tracking failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Performance monitoring test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("LocalCaption Test Suite")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_audio_capture,
        test_asr_engine,
        test_export_utilities,
        test_performance_monitoring,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! LocalCaption is ready to use.")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
