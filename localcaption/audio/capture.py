import threading
import queue
import time
from typing import Callable, Optional, Tuple, Any, List, Dict, cast

import numpy as np
import sounddevice as sd
try:
    import soundcard as sc  # type: ignore
except Exception:
    sc = None  # type: ignore


class AudioCapture:
    """Capture system audio and forward PCM frames to a consumer callback.

    On Windows, uses WASAPI loopback to capture system output.
    On macOS, capture from a selected input device (e.g., BlackHole).
    """

    def __init__(
        self,
        target_sample_rate: int = 16000,
        channels: int = 1,
        block_duration_ms: int = 50,
    ) -> None:
        self.target_sample_rate = target_sample_rate
        self.channels = channels
        self.block_duration_ms = block_duration_ms

        self._stream: Optional[sd.InputStream] = None
        self._sc_mic = None
        self._device_index: Optional[int] = None
        self._queue: "queue.Queue[Tuple[np.ndarray, int, float]]" = queue.Queue()
        self._consumer: Optional[Callable[[np.ndarray, int, float], None]] = None
        self._consumer_thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        # 'internal' (system output loopback) or 'microphone' (default input)
        self._source_mode: str = "internal"

    def list_devices(self) -> List[Dict[str, Any]]:
        """Return sounddevice devices list as a list of dicts."""
        try:
            return cast(List[Dict[str, Any]], list(sd.query_devices()))
        except Exception:
            return []

    def set_device(self, device_index: Optional[int]) -> None:
        self._device_index = device_index

    # Backward-compat alias for UI wiring
    def set_preferred_device_index(self, device_index: Optional[int]) -> None:
        self.set_device(device_index)

    def set_source_mode(self, mode: str) -> None:
        """Set capture source: 'internal' for system loopback, 'microphone' for default input.

        If a specific device is set via set_device(), that overrides this mode.
        """
        if mode in ("internal", "microphone"):
            self._source_mode = mode

    def _find_stereo_mix_device(self) -> Optional[int]:
        """Return the first device index that looks like a Stereo Mix/system capture.

        This is a fallback used when WASAPI loopback is unavailable.
        """
        try:
            devices = list(sd.query_devices())
            for idx in range(len(devices)):
                try:
                    dinfo = sd.query_devices(idx)
                    name = str(dinfo['name']).lower() if isinstance(dinfo, dict) else str(getattr(dinfo, 'name', '')).lower()
                    in_ch = int(dinfo['max_input_channels'] if isinstance(dinfo, dict) else getattr(dinfo, 'max_input_channels', 0) or 0)
                except Exception:
                    continue
                if in_ch > 0 and ('stereo mix' in name or 'stereomix' in name or 'wave' in name):
                    return idx
        except Exception:
            return None
        return None

    def is_active(self) -> bool:
        """Return True if a stream is currently open and running."""
        return self._stream is not None and self._running.is_set()

    def set_consumer(self, consumer: Callable[[np.ndarray, int, float], None]) -> None:
        self._consumer = consumer

    def _on_audio(self, indata: np.ndarray, frames: int, time_info, status) -> None:  # type: ignore[override]
        if status:
            # Drop status messages silently for MVP
            pass
        if indata.size == 0:
            return
        timestamp = time.time()
        # Copy to avoid referencing the ring buffer after callback returns
        pcm = np.copy(indata)
        self._queue.put((pcm, int(self._stream.samplerate) if self._stream else 0, timestamp))

    def _consumer_loop(self) -> None:
        assert self._consumer is not None
        while self._running.is_set():
            try:
                pcm, sample_rate, timestamp = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self._consumer(pcm, sample_rate, timestamp)
            except Exception:
                # Avoid crashing the thread due to consumer issues
                continue

    def start(self) -> None:
        if self._stream is not None:
            return

        self._running.set()

        device = self._device_index
        extra = None
        samplerate = None
        channels = 2
        blocksize = None

        # Determine if selected device is an OUTPUT (loopback) or INPUT (microphone)
        is_output = False
        dinfo = None
        try:
            hostapis = cast(List[Dict[str, Any]], list(sd.query_hostapis()))
            wasapi_index = next((i for i, ha in enumerate(hostapis) if 'wasapi' in ha['name'].lower()), None)

            def is_wasapi_dev(d: Dict[str, Any]) -> bool:
                try:
                    return 'wasapi' in hostapis[int(d.get('hostapi', -1))]['name'].lower()
                except Exception:
                    return False

            # If no explicit device, choose based on source mode
            if device is None:
                if self._source_mode == "microphone":
                    if wasapi_index is not None:
                        device = int(hostapis[wasapi_index]['default_input'])
                    is_output = False
                else:
                    # Internal/system audio
                    if wasapi_index is not None:
                        device = int(hostapis[wasapi_index]['default_output'])
                        is_output = True
                    else:
                        # Fallback to Stereo Mix-like input device
                        sm_idx = self._find_stereo_mix_device()
                        if sm_idx is not None:
                            device = sm_idx
                            is_output = False

            if device is not None and device >= 0:
                dinfo = cast(Dict[str, Any], sd.query_devices(device))
                out_ch = int(dinfo.get('max_output_channels') or 0)
                in_ch = int(dinfo.get('max_input_channels') or 0)
                is_output = out_ch > 0 and (in_ch == 0 or out_ch >= in_ch)

                # For output devices that are not WASAPI, switch to default WASAPI output
                if is_output and wasapi_index is not None and dinfo is not None and not is_wasapi_dev(dinfo):
                    device = int(hostapis[wasapi_index]['default_output'])
                    dinfo = cast(Dict[str, Any], sd.query_devices(device))
                    out_ch = int(dinfo.get('max_output_channels') or 2)

                samplerate = int((dinfo.get('default_samplerate') or 48000))
                channels = max(1, min(2, out_ch if is_output else (in_ch or 2)))
                blocksize = max(1, int((samplerate or 48000) * self.block_duration_ms / 1000))

            # Use WASAPI loopback for speakers/output devices
            if is_output and wasapi_index is not None:
                extra = sd.WasapiSettings(loopback=True)  # type: ignore[call-arg]
        except Exception:
            extra = None

        # If internal audio, first prefer explicit Stereo Mix-like input if available
        if self._source_mode == "internal":
            sm_idx_pref = self._find_stereo_mix_device()
            if sm_idx_pref is not None:
                try:
                    dinfo = cast(Dict[str, Any], sd.query_devices(sm_idx_pref))
                    samplerate = int(dinfo.get('default_samplerate') or 48000)
                except Exception:
                    samplerate = None
                try:
                    self._stream = sd.InputStream(
                        device=sm_idx_pref,
                        dtype='float32',
                        callback=self._on_audio,
                        blocksize=0,
                        latency='low',
                        samplerate=samplerate,
                    )
                    self._stream.start()
                    if self._consumer is not None and self._consumer_thread is None:
                        self._consumer_thread = threading.Thread(target=self._consumer_loop, daemon=True)
                        self._consumer_thread.start()
                    return
                except Exception:
                    self._stream = None

        # If internal and soundcard is available, prefer soundcard loopback to avoid mic bleed
        if self._source_mode == "internal" and sc is not None:
            try:
                default_speaker = sc.default_speaker()
                if default_speaker is not None:
                    # soundcard uses Speaker/Recorder APIs; use get_microphone with loopback
                    self._sc_mic = sc.get_microphone(str(default_speaker.name), include_loopback=True)

                    def _sc_worker() -> None:
                        try:
                            # soundcard Microphone has a context manager for recorder()
                            mic = self._sc_mic
                            if mic is None:
                                return
                            with mic.recorder(samplerate=samplerate or 48000, channels=channels or 2) as rec:
                                while self._running.is_set():
                                    data = rec.record(numframes=blocksize or int((samplerate or 48000) * self.block_duration_ms / 1000))
                                    if data is None:
                                        continue
                                    timestamp = time.time()
                                    self._queue.put((data.astype(np.float32), int(samplerate or 48000), timestamp))
                        except Exception:
                            pass

                    t = threading.Thread(target=_sc_worker, daemon=True)
                    t.start()
                    # Also start consumer thread if needed
                    if self._consumer is not None and self._consumer_thread is None:
                        self._consumer_thread = threading.Thread(target=self._consumer_loop, daemon=True)
                        self._consumer_thread.start()
                    return
            except Exception:
                # Fall back to sounddevice path below
                self._sc_mic = None

        # Try a couple of safe channel counts to avoid PaErrorCode -9998
        tried = []
        for ch in (channels, 2, 1):
            if ch in tried:
                continue
            tried.append(ch)
            try:
                self._stream = sd.InputStream(
                    device=device,
                    channels=ch,
                    dtype='float32',
                    samplerate=samplerate,
                    callback=self._on_audio,
                    blocksize=blocksize or 0,
                    latency='low',
                    extra_settings=extra,
                )
                break
            except Exception:
                self._stream = None
                continue
        if self._stream is None:
            # Final fallback order: try Stereo Mix device explicitly for internal audio
            if self._source_mode == "internal":
                sm_idx = self._find_stereo_mix_device()
                if sm_idx is not None:
                    try:
                        dinfo = cast(Dict[str, Any], sd.query_devices(sm_idx))
                        samplerate = int(dinfo.get('default_samplerate') or 48000)
                    except Exception:
                        samplerate = None
                    try:
                        self._stream = sd.InputStream(
                            device=sm_idx,
                            dtype='float32',
                            callback=self._on_audio,
                            blocksize=0,
                            latency='low',
                            samplerate=samplerate,
                        )
                    except Exception:
                        self._stream = None
            # Generic fallback: let backend choose everything
            if self._stream is None:
                self._stream = sd.InputStream(
                    device=device,
                    dtype='float32',
                    callback=self._on_audio,
                    blocksize=0,
                    latency='low',
                )

        self._stream.start()

        if self._consumer is not None:
            self._consumer_thread = threading.Thread(target=self._consumer_loop, daemon=True)
            self._consumer_thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
        # Stop soundcard loopback if used
        # soundcard recorder uses context manager; no close on microphone handle is needed
        self._sc_mic = None
        if self._consumer_thread is not None:
            self._consumer_thread.join(timeout=1.0)
            self._consumer_thread = None
        with self._queue.mutex:
            self._queue.queue.clear()
