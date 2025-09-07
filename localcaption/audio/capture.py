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
                logger.info(f"Found loopback device: {device['name']} (index: {device['index']})")
                return device['index']
        
        # Try to find a working device by testing them
        working_devices = []
        for device in devices:
            if self._validate_device(device['index']):
                working_devices.append(device)
                logger.info(f"Found working device: {device['name']} (index: {device['index']})")
        
        if working_devices:
            # Prefer Microsoft Sound Mapper or similar system devices
            for device in working_devices:
                if 'sound mapper' in device['name'].lower() or 'primary' in device['name'].lower():
                    logger.info(f"Using preferred system device: {device['name']} (index: {device['index']})")
                    return device['index']
            
            # Use first working device
            logger.info(f"Using first working device: {working_devices[0]['name']} (index: {working_devices[0]['index']})")
            return working_devices[0]['index']
        
        # Fallback to default input device
        try:
            default_input = sd.default.device[0]  # Input device
            logger.info(f"Using default input device: {default_input}")
            return default_input
        except Exception as e:
            logger.warning(f"Could not get default input device: {e}")
        
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
        
        # Validate device before attempting to use it
        if not self._validate_device(device_index):
            logger.error(f"Device {device_index} is not valid or accessible")
            return False
        
        self.callback = callback
        
        try:
            # Get device info to check supported sample rates
            device_info = sd.query_devices(device_index)
            device_sample_rate = device_info['default_samplerate']
            
            # Use device's preferred sample rate if it's close to our target
            if abs(device_sample_rate - self.sample_rate) < 1000:  # Within 1kHz
                actual_sample_rate = device_sample_rate
            else:
                actual_sample_rate = self.sample_rate
            
            logger.info(f"Using sample rate: {actual_sample_rate} (device default: {device_sample_rate})")
            
            # Create audio stream with platform-specific parameters
            stream_params = {
                'device': device_index,
                'channels': 1,
                'samplerate': actual_sample_rate,
                'blocksize': self.chunk_size,
                'callback': self._audio_callback,
                'dtype': np.float32
            }
            
            # Add platform-specific parameters
            if self.platform == "windows":
                # For Windows, we need to set the API before creating the stream
                sd.default.device = device_index
                sd.default.samplerate = actual_sample_rate
                # Try to use WASAPI by setting the default API
                try:
                    sd.default.api = self.api
                except:
                    logger.warning(f"Could not set API to {self.api}, using default")
            
            self.stream = sd.InputStream(**stream_params)
            
            self.stream.start()
            self.is_capturing = True
            logger.info(f"Started audio capture on device {device_index}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            return False
    
    def _validate_device(self, device_index: int) -> bool:
        """Validate that a device index is valid and accessible"""
        try:
            # Check if device exists
            device_info = sd.query_devices(device_index)
            if device_info is None:
                return False
            
            # Check if device has input channels
            if device_info['max_input_channels'] == 0:
                logger.warning(f"Device {device_index} has no input channels")
                return False
            
            # Try different sample rates for Windows compatibility
            sample_rates = [16000, 44100, 48000]
            for sample_rate in sample_rates:
                try:
                    # Try to create a test stream with different sample rates
                    test_stream = sd.InputStream(
                        device=device_index,
                        channels=1,
                        samplerate=sample_rate,
                        blocksize=64,
                        dtype=np.float32
                    )
                    test_stream.close()
                    logger.info(f"Device {device_index} validated with sample rate {sample_rate}")
                    return True
                except Exception as e:
                    logger.debug(f"Device {device_index} failed with sample rate {sample_rate}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.warning(f"Device {device_index} validation failed: {e}")
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
