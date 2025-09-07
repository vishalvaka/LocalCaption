#!/usr/bin/env python3
"""
Test ASR engine initialization specifically
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_asr_initialization():
    """Test ASR engine initialization"""
    print("Testing ASR engine initialization...")
    
    try:
        from localcaption.asr.engine import ASREngine, ModelManager
        
        # Get model config
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
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_asr_initialization()
    sys.exit(0 if success else 1)
