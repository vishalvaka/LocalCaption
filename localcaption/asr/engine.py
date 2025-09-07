"""
ASR Engine using sherpa-onnx for real-time speech recognition
"""

import os
import time
import threading
import queue
import logging
from typing import Optional, Callable, Dict, Any, List
import numpy as np
import sherpa_onnx

logger = logging.getLogger(__name__)


class ASREngine:
    """ASR Engine using sherpa-onnx with streaming support"""
    
    def __init__(self, model_config: Dict[str, Any]):
        self.model_config = model_config
        self.recognizer = None
        self.stream = None
        self.is_initialized = False
        self.is_running = False
        self.audio_queue = queue.Queue(maxsize=50)
        self.result_callback = None
        self.thread = None
        self.latency_history = []
        
        # Performance metrics
        self.total_audio_duration = 0.0
        self.total_processing_time = 0.0
        self.last_result_time = 0.0
        
    def initialize(self) -> bool:
        """Initialize the ASR engine"""
        try:
            # Create recognizer with direct model files
            model_dir = os.path.dirname(self.model_config['config_file'])
            
            # Check if all required files exist
            required_files = {
                'encoder': os.path.join(model_dir, "encoder-epoch-99-avg-1.onnx"),
                'decoder': os.path.join(model_dir, "decoder-epoch-99-avg-1.onnx"),
                'joiner': os.path.join(model_dir, "joiner-epoch-99-avg-1.onnx"),
                'tokens': os.path.join(model_dir, "tokens.txt"),
                'bpe_model': os.path.join(model_dir, "bpe.model"),
                'bpe_vocab': os.path.join(model_dir, "bpe.vocab")
            }
            
            for name, path in required_files.items():
                if not os.path.exists(path):
                    logger.error(f"Required file not found: {path}")
                    return False
            
            # Create recognizer using from_transducer method
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                tokens=required_files['tokens'],
                encoder=required_files['encoder'],
                decoder=required_files['decoder'],
                joiner=required_files['joiner'],
                bpe_vocab=required_files['bpe_vocab'],
                sample_rate=16000,
                feature_dim=80,
                num_threads=1,
                debug=False,
                provider='cpu'
            )
            
            # Create stream
            self.stream = self.recognizer.create_stream()
            self.is_initialized = True
            logger.info("ASR engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ASR engine: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_recognition(self, callback: Optional[Callable] = None):
        """Start real-time recognition"""
        if not self.is_initialized:
            logger.error("ASR engine not initialized")
            return False
        
        if self.is_running:
            logger.warning("ASR engine is already running")
            return False
        
        self.result_callback = callback
        self.is_running = True
        
        # Start processing thread
        self.thread = threading.Thread(target=self._process_audio, daemon=True)
        self.thread.start()
        
        logger.info("ASR recognition started")
        return True
    
    def stop_recognition(self):
        """Stop recognition"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        # Finalize stream
        if self.stream:
            self.recognizer.decode_stream(self.stream)
            result = self.recognizer.get_result(self.stream)
            if result and self.result_callback:
                self.result_callback(result.text.strip())
        
        logger.info("ASR recognition stopped")
    
    def add_audio(self, audio_data: np.ndarray):
        """Add audio data for processing"""
        if not self.is_running or not self.stream:
            return
        
        try:
            # Convert to int16 if needed
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # Add to stream
            self.stream.accept_waveform(
                sample_rate=self.model_config.get('sample_rate', 16000),
                waveform=audio_data.tolist()
            )
            
        except Exception as e:
            logger.error(f"Error adding audio to ASR: {e}")
    
    def _process_audio(self):
        """Process audio in background thread"""
        while self.is_running:
            try:
                # Decode stream
                self.recognizer.decode_stream(self.stream)
                
                # Get result
                result = self.recognizer.get_result(self.stream)
                
                if result and result.text.strip():
                    current_time = time.time()
                    
                    # Calculate latency
                    if self.last_result_time > 0:
                        latency = current_time - self.last_result_time
                        self.latency_history.append(latency)
                        
                        # Keep only last 100 measurements
                        if len(self.latency_history) > 100:
                            self.latency_history.pop(0)
                    
                    self.last_result_time = current_time
                    
                    # Call callback
                    if self.result_callback:
                        self.result_callback(result.text.strip())
                
                # Small delay to prevent busy waiting
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in ASR processing: {e}")
                time.sleep(0.1)
    
    def get_average_latency(self) -> float:
        """Get average latency in seconds"""
        if not self.latency_history:
            return 0.0
        return sum(self.latency_history) / len(self.latency_history)
    
    def get_processing_stats(self) -> Dict[str, float]:
        """Get processing statistics"""
        avg_latency = self.get_average_latency()
        
        return {
            'average_latency': avg_latency,
            'total_audio_duration': self.total_audio_duration,
            'total_processing_time': self.total_processing_time,
            'realtime_factor': self.total_audio_duration / max(self.total_processing_time, 0.001)
        }


class ModelManager:
    """Manages ASR model downloads and configuration"""
    
    MODELS = {
        'zipformer_bilingual': {
            'name': 'Zipformer Tiny (Bilingual EN-ZH)',
            'size': '~20MB',
            'url': 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2',
            'config_file': 'sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/online_config.yaml'
        }
    }
    
    @classmethod
    def get_model_config(cls, model_name: str, models_dir: str = "models") -> Optional[Dict[str, Any]]:
        """Get model configuration"""
        if model_name not in cls.MODELS:
            logger.error(f"Unknown model: {model_name}")
            return None
        
        model_info = cls.MODELS[model_name]
        config_path = os.path.join(models_dir, model_info['config_file'])
        
        if not os.path.exists(config_path):
            logger.warning(f"Model config not found: {config_path}")
            return None
        
        return {
            'config_file': config_path,
            'sample_rate': 16000,
            'model_name': model_name,
            'model_info': model_info
        }
    
    @classmethod
    def list_available_models(cls, models_dir: str = "models") -> List[str]:
        """List available models"""
        available = []
        for model_name, model_info in cls.MODELS.items():
            config_path = os.path.join(models_dir, model_info['config_file'])
            if os.path.exists(config_path):
                available.append(model_name)
        return available
    
    @classmethod
    def download_model(cls, model_name: str, models_dir: str = "models") -> bool:
        """Download model (placeholder - would implement actual download)"""
        logger.info(f"Model download not implemented yet. Please download {model_name} manually.")
        return False


def create_default_config() -> Dict[str, Any]:
    """Create default ASR configuration"""
    return {
        'model_name': 'zipformer_bilingual',
        'sample_rate': 16000,
        'chunk_size': 1024,
        'vad_threshold': 0.01,
        'min_silence_duration': 0.5,
        'max_sentence_length': 100
    }
