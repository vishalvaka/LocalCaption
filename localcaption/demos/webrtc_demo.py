from __future__ import annotations

import asyncio
import os
import sys
import signal
from typing import Optional

import numpy as np
import sounddevice as sd
from aiortc import RTCPeerConnection, MediaStreamTrack
from aiortc.mediastreams import MediaStreamError
from av import AudioFrame

# Import ASR backends from the app
from ..asr.engine import StreamingASREngine, DeepgramStreamingASR, RecognitionResult


def models_root() -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base, "models")


class MicrophoneTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, sample_rate: int = 48000, channels: int = 1, block_duration_ms: int = 20) -> None:
        super().__init__()
        # Larger queue; we'll drop frames when full to avoid backpressure explosions
        self._queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=50)
        self._sample_rate = sample_rate
        self._channels = channels
        self._block_size = max(1, int(sample_rate * block_duration_ms / 1000))
        self._running = True

        loop = asyncio.get_event_loop()

        def _cb(indata, frames, time_info, status):  # type: ignore[no-untyped-def]
            if not self._running:
                return
            if status:
                # Ignore over/underflows for demo
                pass
            pcm = np.copy(indata).astype(np.float32)
            # Mix to mono if needed
            if pcm.ndim == 2 and pcm.shape[1] > 1:
                pcm = np.mean(pcm, axis=1, keepdims=True)
            elif pcm.ndim == 1:
                pcm = pcm.reshape(-1, 1)
            # Schedule a safe put that drops when full to prevent QueueFull exceptions
            def _safe_put() -> None:
                try:
                    self._queue.put_nowait(pcm)
                except asyncio.QueueFull:  # type: ignore[attr-defined]
                    # Drop frame if consumer is slow
                    pass
                except Exception:
                    pass
            try:
                loop.call_soon_threadsafe(_safe_put)
            except Exception:
                pass

        self._stream = sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype='float32',
            blocksize=self._block_size,
            callback=_cb,
        )
        self._stream.start()

    async def recv(self) -> AudioFrame:
        try:
            pcm = await self._queue.get()
        except asyncio.CancelledError:
            raise MediaStreamError
        # pcm shape: (N, 1) float32 in [-1,1]
        samples = (pcm.squeeze().astype(np.float32))
        # Convert to 16-bit signed integers for AudioFrame
        pcm_i16 = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
        frame = AudioFrame(format='s16', layout='mono', samples=len(pcm_i16))
        frame.sample_rate = self._sample_rate
        for plane in frame.planes:
            plane.update(pcm_i16.tobytes())
        return frame

    def stop(self) -> None:  # type: ignore[override]
        self._running = False
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            pass
        try:
            super().stop()
        except Exception:
            pass


class ASRReceiver:
    def __init__(self, backend: str = "auto") -> None:
        self._asr = None
        if backend == "deepgram" or (backend == "auto" and os.environ.get("DEEPGRAM_API_KEY")):
            key = os.environ.get("DEEPGRAM_API_KEY")
            if not key:
                raise RuntimeError("DEEPGRAM_API_KEY not set in environment")
            self._asr = DeepgramStreamingASR(api_key=key, model=os.environ.get("DEEPGRAM_MODEL") or None)
            self._target_sr = 16000
        else:
            model_dir = os.path.join(models_root(), "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17")
            self._asr = StreamingASREngine(model_dir=model_dir)
            self._target_sr = 16000

    async def handle_track(self, track: MediaStreamTrack) -> None:
        from av import AudioFrame as _AF
        try:
            print("[webrtc] Audio track received, starting ASR…")
            while True:
                frame = await track.recv()
                if not isinstance(frame, _AF):
                    continue
                # Convert to mono float32 numpy at 48kHz
                pcm = frame.to_ndarray()
                # shape may be (channels, samples) for planar; ensure 1D mono
                if pcm.ndim == 2:
                    if pcm.shape[0] > 1:
                        pcm = np.mean(pcm, axis=0)
                    else:
                        pcm = pcm[0]
                # Normalize based on format
                if frame.format.name.startswith('s16'):
                    pcm_f32 = (pcm.astype(np.float32) / 32768.0)
                else:
                    pcm_f32 = pcm.astype(np.float32)

                # Feed to ASR (will resample internally if needed)
                res: Optional[RecognitionResult] = self._asr.accept_pcm(pcm_f32, int(frame.sample_rate), frame.time or 0.0)  # type: ignore[arg-type]
                if res is not None:
                    prefix = "FINAL" if res.is_final else "PART"
                    print(f"[{prefix}] {res.text}")
        except MediaStreamError:
            return
        except Exception as e:
            print(f"ASRReceiver error: {e}")


async def run_demo() -> None:
    pc_sender = RTCPeerConnection()
    pc_receiver = RTCPeerConnection()

    # Wire receiver to print captions
    asr = ASRReceiver(backend="auto")

    @pc_receiver.on("track")
    def on_track(track: MediaStreamTrack) -> None:
        if track.kind == "audio":
            asyncio.create_task(asr.handle_track(track))

    # Create microphone track and add to sender
    # Use default input device; to select specific index, set SD_INPUT_DEVICE
    dev_str = os.environ.get("SD_INPUT_DEVICE")
    if dev_str is not None and dev_str.strip() != "":
        try:
            sd.default.device = (int(dev_str), None)
            print(f"[webrtc] Using input device index {dev_str}")
        except Exception as e:
            print(f"[webrtc] Failed to set input device {dev_str}: {e}")
    mic = MicrophoneTrack(sample_rate=48000, channels=1, block_duration_ms=20)
    pc_sender.addTrack(mic)

    # Ensure receiver is prepared to accept audio
    pc_receiver.addTransceiver("audio")

    # Connect peers locally (in-process signaling)
    offer = await pc_sender.createOffer()
    await pc_sender.setLocalDescription(offer)
    await pc_receiver.setRemoteDescription(pc_sender.localDescription)
    answer = await pc_receiver.createAnswer()
    await pc_receiver.setLocalDescription(answer)
    await pc_sender.setRemoteDescription(pc_receiver.localDescription)

    print("WebRTC demo running. Speak into your microphone.")
    print("Press Ctrl+C to stop.")

    stop_event = asyncio.Event()

    def _on_sigint(*_args) -> None:
        try:
            stop_event.set()
        except Exception:
            pass

    try:
        signal.signal(signal.SIGINT, _on_sigint)
    except Exception:
        pass

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass

    # Cleanup
    try:
        await mic.stop()
    except Exception:
        pass
    try:
        await pc_sender.close()
    except Exception:
        pass
    try:
        await pc_receiver.close()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(run_demo())


