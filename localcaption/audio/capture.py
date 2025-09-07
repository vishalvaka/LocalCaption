import threading
import queue
import time
from typing import Callable, Optional, Tuple

import numpy as np
import sounddevice as sd


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
        self._device_index: Optional[int] = None
        self._queue: "queue.Queue[Tuple[np.ndarray, int, float]]" = queue.Queue()
        self._consumer: Optional[Callable[[np.ndarray, int, float], None]] = None
        self._consumer_thread: Optional[threading.Thread] = None
        self._running = threading.Event()

    def list_devices(self) -> list:
        """Return sounddevice devices list."""
        return sd.query_devices()

    def set_device(self, device_index: Optional[int]) -> None:
        self._device_index = device_index

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

        try:
            hostapis = sd.query_hostapis()
            wasapi_index = next((i for i, ha in enumerate(hostapis) if 'wasapi' in ha['name'].lower()), None)
            if wasapi_index is not None:
                extra = sd.WasapiSettings(loopback=True)
                if device is None:
                    device = hostapis[wasapi_index]['default_output']
                if device is not None and device >= 0:
                    dinfo = sd.query_devices(device)
                    samplerate = int(dinfo.get('default_samplerate') or 48000)
                    out_ch = int(dinfo.get('max_output_channels') or 2)
                    channels = max(1, min(2, out_ch))
                    blocksize = max(1, int(samplerate * self.block_duration_ms / 1000))
        except Exception:
            extra = None

        try:
            self._stream = sd.InputStream(
                device=device,
                channels=channels,
                dtype='float32',
                samplerate=samplerate,
                callback=self._on_audio,
                blocksize=blocksize or 0,
                latency='low',
                extra_settings=extra,
            )
        except Exception:
            # Fallback: let backend choose everything (e.g., macOS/other APIs)
            self._stream = sd.InputStream(
                device=device,
                channels=max(1, self.channels),
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
        if self._consumer_thread is not None:
            self._consumer_thread.join(timeout=1.0)
            self._consumer_thread = None
        with self._queue.mutex:
            self._queue.queue.clear()
