from __future__ import annotations

import threading
import queue
from typing import Optional, Callable, Tuple


class LocalTTSEngine:
    """Threaded TTS engine using pyttsx3 with a simple speak queue.

    Avoids blocking the UI by speaking on a background worker thread.
    Provides start/stop callbacks so callers can gate ASR while speaking.
    """

    def __init__(
        self,
        voice_id: Optional[str] = None,
        rate_wpm: Optional[int] = None,
        on_speaking: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self._engine = None
        self._init_engine(voice_id=voice_id, rate_wpm=rate_wpm)
        self._queue: "queue.Queue[Tuple[str, bool]]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._on_speaking = on_speaking

    def _init_engine(self, voice_id: Optional[str], rate_wpm: Optional[int]) -> None:
        try:
            import pyttsx3  # type: ignore
        except Exception:
            self._engine = None
            return
        try:
            self._engine = pyttsx3.init()
            if voice_id is not None:
                try:
                    self._engine.setProperty("voice", voice_id)
                except Exception:
                    pass
            if rate_wpm is not None:
                try:
                    self._engine.setProperty("rate", int(rate_wpm))
                except Exception:
                    pass
        except Exception:
            self._engine = None

    def list_voices(self) -> list[dict]:
        try:
            if self._engine is None:
                return []
            voices = self._engine.getProperty("voices")  # type: ignore[attr-defined]
            result = []
            for v in voices or []:
                try:
                    result.append({
                        "id": getattr(v, "id", ""),
                        "name": getattr(v, "name", ""),
                        "languages": getattr(v, "languages", []),
                    })
                except Exception:
                    continue
            return result
        except Exception:
            return []

    def start(self) -> None:
        if self._engine is None:
            return
        if self._worker is not None:
            return
        self._running.set()
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._running.clear()
        try:
            if self._engine is not None:
                try:
                    self._engine.stop()  # type: ignore[attr-defined]
                except Exception:
                    pass
        finally:
            if self._worker is not None:
                self._worker.join(timeout=1.0)
                self._worker = None
            with self._queue.mutex:
                self._queue.queue.clear()

    def speak(self, text: str, flush: bool = False) -> None:
        """Queue text to speak. If flush=True, clear existing queue first."""
        if self._engine is None:
            return
        if flush:
            with self._queue.mutex:
                self._queue.queue.clear()
        self._queue.put((text, flush))

    def _loop(self) -> None:
        assert self._engine is not None
        while self._running.is_set():
            try:
                text, _ = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                if self._on_speaking is not None:
                    self._on_speaking(True)
                self._engine.say(text)  # type: ignore[attr-defined]
                self._engine.runAndWait()  # type: ignore[attr-defined]
            except Exception:
                pass
            finally:
                if self._on_speaking is not None:
                    self._on_speaking(False)


