"""
Audio capture module for LocalCaption
Supports WASAPI loopback on Windows and CoreAudio on macOS
"""

import sounddevice as sd
import numpy as np
import threading
import queue
import time
import platform
from typing import Optional, Callable, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AudioCapture:
    """Audio capture class with platform-specific optimizations"""
    
    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.is_capturing = False
        self.audio_queue = queue.Queue(maxsize=100)
        self.stream = None
        self.thread = None
        self.callback = None
        self.platform = platform.system().lower()
        
        # Platform-specific settings
        self._setup_platform_settings()
    
    def _setup_platform_settings(self):
        """Setup platform-specific audio settings"""
        if self.platform == "windows":
            # Use WASAPI for better loopback support
            self.api = "wasapi"
            self.wasapi_shared = True
        elif self.platform == "darwin":
            # Use CoreAudio on macOS
            self.api = "coreaudio"
            self.wasapi_shared = False
        else:
            # Fallback to default
            self.api = None
            self.wasapi_shared = False
    
    def get_audio_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio devices"""
        devices = []
        try:
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                if device['max_input_channels'] > 0:
                    devices.append({
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'sample_rate': device['default_samplerate'],
                        'is_loopback': 'loopback' in device['name'].lower() or 'stereo mix' in device['name'].lower()
                    })
        except Exception as e:
            logger.error(f"Error querying audio devices: {e}")
        
        return devices
    
    def get_default_loopback_device(self) -> Optional[int]:
        """Get the default loopback device for system audio capture"""
        devices = self.get_audio_devices()
        
        # Look for loopback devices first
        for device in devices:
            if device['is_loopback']:
                return device['index']
        
        # Fallback to default input device
        try:
            return sd.default.device[0]  # Input device
        except:
            return None
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback function for audio stream"""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        if self.callback:
            # Convert to mono if stereo
            if indata.shape[1] > 1:
                audio_data = np.mean(indata, axis=1)
            else:
                audio_data = indata[:, 0]
            
            # Convert to float32
            audio_data = audio_data.astype(np.float32)
            
            try:
                self.callback(audio_data)
            except Exception as e:
                logger.error(f"Error in audio callback: {e}")
    
    def start_capture(self, device_index: Optional[int] = None, callback: Optional[Callable] = None):
        """Start audio capture"""
        if self.is_capturing:
            logger.warning("Audio capture is already running")
            return False
        
        if device_index is None:
            device_index = self.get_default_loopback_device()
            if device_index is None:
                logger.error("No suitable audio device found")
                return False
        
        self.callback = callback
        
        try:
            # Create audio stream
            self.stream = sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
                dtype=np.float32,
                api=self.api,
                wasapi_shared=self.wasapi_shared
            )
            
            self.stream.start()
            self.is_capturing = True
            logger.info(f"Started audio capture on device {device_index}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            return False
    
    def stop_capture(self):
        """Stop audio capture"""
        if not self.is_capturing:
            return
        
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            self.is_capturing = False
            self.callback = None
            logger.info("Stopped audio capture")
            
        except Exception as e:
            logger.error(f"Error stopping audio capture: {e}")
    
    def is_available(self) -> bool:
        """Check if audio capture is available on this platform"""
        try:
            devices = self.get_audio_devices()
            return len(devices) > 0
        except:
            return False
    
    def get_latency(self) -> float:
        """Get current audio stream latency in seconds"""
        if self.stream and self.is_capturing:
            try:
                return self.stream.latency[0]  # Input latency
            except:
                return 0.0
        return 0.0


class AudioProcessor:
    """Audio processing utilities"""
    
    @staticmethod
    def normalize_audio(audio: np.ndarray) -> np.ndarray:
        """Normalize audio to [-1, 1] range"""
        if len(audio) == 0:
            return audio
        
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return audio / max_val
        return audio
    
    @staticmethod
    def apply_vad(audio: np.ndarray, threshold: float = 0.01) -> bool:
        """Simple Voice Activity Detection"""
        if len(audio) == 0:
            return False
        
        rms = np.sqrt(np.mean(audio ** 2))
        return rms > threshold
    
    @staticmethod
    def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Resample audio to target sample rate"""
        if orig_sr == target_sr:
            return audio
        
        # Simple linear interpolation resampling
        ratio = target_sr / orig_sr
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio)
