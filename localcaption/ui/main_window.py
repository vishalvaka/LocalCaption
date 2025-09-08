from __future__ import annotations

import os
import sys
import threading
import time
from typing import Optional, Any, cast

import numpy as np
import psutil
from PyQt6 import QtCore, QtGui, QtWidgets  # type: ignore

from ..audio.capture import AudioCapture
from ..asr.engine import StreamingASREngine, RecognitionResult
from ..asr.engine import DeepgramStreamingASR
from ..utils.config import load_config
from ..utils.models import ensure_model_downloaded
from ..tts.engine import LocalTTSEngine


class MainWindow(QtWidgets.QWidget):
    caption_updated = QtCore.pyqtSignal(str)  # type: ignore
    tts_speaking_changed = QtCore.pyqtSignal(bool)  # type: ignore

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LocalCaption")
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self._caption_view = QtWidgets.QPlainTextEdit()
        self._caption_view.setReadOnly(True)
        self._caption_view.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self._caption_view.setWordWrapMode(QtGui.QTextOption.WrapMode.WordWrap)
        font = QtGui.QFont("Segoe UI", 14)
        self._caption_view.setFont(font)
        self._caption_view.setStyleSheet("color: white; background-color: rgba(0,0,0,160); padding: 8px; border-radius: 6px;")

        self._start_btn = QtWidgets.QPushButton("Start")
        self._stop_btn = QtWidgets.QPushButton("Stop")
        self._config_btn = QtWidgets.QPushButton("Configure…")
        self._save_btn = QtWidgets.QPushButton("Save")
        self._speak_btn = QtWidgets.QPushButton("Speak")
        self._stop_speak_btn = QtWidgets.QPushButton("Stop")
        self._restart_speak_btn = QtWidgets.QPushButton("Restart")
        self._close_btn = QtWidgets.QPushButton("×")
        self._close_btn.setFixedWidth(28)
        self._close_btn.setToolTip("Close")

        self._metrics_label = QtWidgets.QLabel("Latency: -- ms | CPU: -- %")
        self._metrics_label.setStyleSheet("color: #ddd;")

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self._start_btn)
        buttons.addWidget(self._stop_btn)
        buttons.addWidget(self._save_btn)
        buttons.addWidget(self._speak_btn)
        buttons.addWidget(self._stop_speak_btn)
        buttons.addWidget(self._restart_speak_btn)
        buttons.addWidget(self._config_btn)
        buttons.addStretch(1)
        buttons.addWidget(self._metrics_label)
        buttons.addSpacing(8)
        buttons.addWidget(self._close_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(buttons)
        layout.addWidget(self._caption_view)

        self.resize(800, 160)

        # State
        self._capture = AudioCapture()
        self._capture.set_consumer(self._on_pcm)
        self._asr: Optional[Any] = None
        self._transcript_lines: list[str] = []
        self._current_partial: str = ""
        self._last_latency_ms: float = 0.0
        self._config_dirty: bool = False
        self._is_tts_speaking: bool = False
        self._tts: Optional[LocalTTSEngine] = None
        self._manual_tts_active: bool = False
        self._metrics_timer = QtCore.QTimer(self)
        self._metrics_timer.timeout.connect(self._update_metrics)
        self._metrics_timer.start(500)

        self._drag_offset: Optional[QtCore.QPoint] = None

        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn.clicked.connect(self._on_stop)
        self._save_btn.clicked.connect(self._on_save)
        self._speak_btn.clicked.connect(self._on_speak)
        self._stop_speak_btn.clicked.connect(self._on_stop_speaking)
        self._restart_speak_btn.clicked.connect(self._on_restart_speaking)
        self._close_btn.clicked.connect(self._on_close_clicked)
        self._config_btn.clicked.connect(self._on_configure)

        # Signals
        self.caption_updated.connect(self._on_caption_updated)
        self.tts_speaking_changed.connect(self._on_tts_speaking_ui)

        # Cache Qt namespace for readability
        self._QT = QtCore.Qt
        self._update_save_enabled()
        try:
            self._speak_btn.setEnabled(False)
            self._stop_speak_btn.setEnabled(False)
            self._restart_speak_btn.setEnabled(False)
        except Exception:
            pass
        try:
            self._caption_view.installEventFilter(self)
        except Exception:
            pass

    @QtCore.pyqtSlot()
    def _on_close_clicked(self) -> None:  # type: ignore[no-untyped-def]
        self.close()

    @QtCore.pyqtSlot()
    def _on_configure(self) -> None:  # type: ignore[no-untyped-def]
        try:
            from .config_dialog import ConfigDialog
            from ..utils.config import load_config
            from ..utils.models import ensure_model_downloaded
        except Exception:
            return
        cfg = ConfigDialog.run_modal(self)
        if not cfg:
            return
        # Apply device selection immediately
        if cfg.selected_device_index is not None:
            self._capture.set_preferred_device_index(cfg.selected_device_index)
        # Ensure model exists, and if engine already running, re-init on next start
        if cfg.selected_model_id:
            ensure_model_downloaded(cfg.selected_model_id)
        # Mark that configuration changed so Start will re-init ASR
        self._config_dirty = True
        # Update Speak button state based on new config
        try:
            self._update_speak_enabled()
        except Exception:
            pass

    # Ensure full shutdown when the window is closed
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        try:
            if hasattr(self, "_metrics_timer") and self._metrics_timer is not None:
                self._metrics_timer.stop()
        except Exception:
            pass
        try:
            if hasattr(self, "_capture") and self._capture is not None:
                self._capture.stop()
        except Exception:
            pass
        try:
            QtWidgets.QApplication.quit()
        except Exception:
            pass
        super().closeEvent(event)

    def _models_root(self) -> str:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base = sys._MEIPASS  # type: ignore[attr-defined]
        else:
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        return os.path.join(base, "models")

    def _ensure_asr(self) -> None:
        # Reinitialize if requested by config change
        if self._asr is not None and not self._config_dirty:
            return
        cfg = load_config()
        model_dir: Optional[str] = None
        if cfg.selected_model_id:
            try:
                model_dir = ensure_model_downloaded(cfg.selected_model_id)
            except Exception:
                model_dir = None
        if not model_dir:
            model_dir = os.path.join(self._models_root(), "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17")
        try:
            # Choose backend
            if cfg.stt_backend == "deepgram" and cfg.deepgram_api_key:
                self._asr = DeepgramStreamingASR(api_key=cfg.deepgram_api_key, model=cfg.deepgram_model)
            else:
                self._asr = StreamingASREngine(model_dir=model_dir)
            self._config_dirty = False
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "ASR init error", f"{e}")

        # Do not initialize TTS here; TTS is only used via Speak button when capture is stopped

    def _on_start(self) -> None:
        # Apply latest config (force device switch by restarting capture)
        cfg = load_config()
        desired = None if cfg.selected_device_index in (None, -1) else cfg.selected_device_index
        if self._capture.is_active():
            self._capture.stop()
        self._capture.set_preferred_device_index(desired)
        self._ensure_asr()
        if self._asr is None:
            return
        self._transcript_lines.clear()
        self._update_save_enabled()
        try:
            # Disable Speak during capture, or when TTS is disabled
            self._speak_btn.setEnabled(False)
        except Exception:
            pass
        self._capture.start()

    def _on_stop(self) -> None:
        self._capture.stop()
        # Finalize any partial to allow saving
        if self._current_partial.strip():
            self._transcript_lines.append(self._current_partial.strip())
            self._current_partial = ""
        self._render_captions()
        self._update_save_enabled()
        try:
            self._update_speak_enabled()
        except Exception:
            pass
        try:
            if self._tts is not None:
                self._tts.stop()
                self._tts = None
        except Exception:
            pass
        # Reset ASR if Deepgram to allow fresh connection on next Start
        try:
            from ..asr.engine import DeepgramStreamingASR as _DG
            if isinstance(self._asr, _DG):
                try:
                    self._asr.close()
                except Exception:
                    pass
                self._asr = None
        except Exception:
            pass
        try:
            self._stop_speak_btn.setEnabled(False)
            self._restart_speak_btn.setEnabled(self._can_speak())
        except Exception:
            pass

    def _on_speak(self) -> None:
        # Only allow when capture is stopped
        if self._capture.is_active():
            QtWidgets.QMessageBox.information(self, "Busy", "Stop captioning before using Speak.")
            return
        # Respect TTS enabled flag
        cfg = load_config()
        if not cfg.tts_enabled:
            QtWidgets.QMessageBox.information(self, "TTS disabled", "Enable TTS in Configure to use Speak.")
            return
        # Build full transcript including current partial
        lines = list(self._transcript_lines)
        if self._current_partial.strip():
            lines.append(self._current_partial.strip())
        full_text = "\n".join([ln for ln in lines if ln.strip()])
        if not full_text:
            QtWidgets.QMessageBox.information(self, "Nothing to speak", "There is no transcript yet.")
            return
        # Ensure TTS is available and start
        self._speak_full_text(full_text, cfg)

    def _on_stop_speaking(self) -> None:
        try:
            if self._tts is not None:
                self._tts.stop()
                self._tts = None
        except Exception:
            pass
        self._is_tts_speaking = False
        self._manual_tts_active = False
        try:
            self._speak_btn.setEnabled(self._can_speak())
            self._stop_speak_btn.setEnabled(False)
            self._restart_speak_btn.setEnabled(self._can_speak())
        except Exception:
            pass

    def _on_restart_speaking(self) -> None:
        if self._capture.is_active():
            return
        cfg = load_config()
        if not cfg.tts_enabled:
            return
        full_text = "\n".join([ln for ln in self._transcript_lines if ln.strip()])
        if self._current_partial.strip():
            full_text += ("\n" if full_text else "") + self._current_partial.strip()
        if not full_text:
            return
        self._on_stop_speaking()
        self._speak_full_text(full_text, cfg)

    def _speak_full_text(self, full_text: str, cfg) -> None:
        try:
            try:
                if self._tts is not None:
                    self._tts.stop()
            except Exception:
                pass
            self._tts = None
            self._tts = LocalTTSEngine(
                voice_id=cfg.tts_voice_id,
                rate_wpm=cfg.tts_rate_wpm,
                on_speaking=self._on_tts_speaking,
            )
            self._tts.start()
            self._manual_tts_active = True
            self._tts.speak(full_text, flush=True)
            try:
                self._speak_btn.setEnabled(False)
                self._stop_speak_btn.setEnabled(True)
                self._restart_speak_btn.setEnabled(True)
            except Exception:
                pass
        except Exception:
            pass

    def _on_save(self) -> None:
        if not self._transcript_lines:
            QtWidgets.QMessageBox.information(self, "Nothing to save", "There are no captions to save yet.")
            return
        txt_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save transcript", "transcript.txt", "Text Files (*.txt)")
        if txt_path:
            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(self._transcript_lines))
            except Exception:
                pass
        vtt_path = os.path.splitext(txt_path)[0] + ".vtt" if txt_path else ""
        if vtt_path:
            try:
                with open(vtt_path, "w", encoding="utf-8") as f:
                    f.write("WEBVTT\n\n")
                    t = 0.0
                    for line in self._transcript_lines:
                        start_ms = int(t * 1000)
                        end_ms = int((t + 2.0) * 1000)
                        f.write(f"00:00:{start_ms//1000:02d}.{start_ms%1000:03d} --> 00:00:{end_ms//1000:02d}.{end_ms%1000:03d}\n")
                        f.write(line + "\n\n")
                        t += 2.0
            except Exception:
                pass

    def _on_pcm(self, pcm: np.ndarray, sample_rate: int, timestamp: float) -> None:
        if self._asr is None:
            return
        if sample_rate is None or sample_rate <= 0:
            return
        # No TTS during live captioning; ignore any TTS state
        try:
            res: Optional[RecognitionResult] = self._asr.accept_pcm(pcm.astype(np.float32), sample_rate, timestamp)
        except Exception:
            return
        if res is None:
            return
        self._last_latency_ms = res.latency_ms
        if res.is_final:
            if res.text:
                self._transcript_lines.append(res.text)
            # request UI thread to clear partial and render
            self._set_caption("")
        else:
            self._set_caption(res.text)
            # No speaking of partials during live captioning

    @QtCore.pyqtSlot()
    def _update_metrics(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        self._metrics_label.setText(f"Latency: {int(self._last_latency_ms)} ms | CPU: {int(cpu)} %")

    def _set_caption(self, text: str) -> None:
        self.caption_updated.emit(text)

    def _on_caption_updated(self, text: str) -> None:
        self._current_partial = text
        self._render_captions()
        self._update_save_enabled()

    def _render_captions(self) -> None:
        try:
            lines = list(self._transcript_lines)
            if self._current_partial:
                lines.append(self._current_partial)
            content = "\n".join(lines)
            # Preserve bottom scroll; set then move cursor to end
            self._caption_view.setPlainText(content)
            cursor = self._caption_view.textCursor()
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
            self._caption_view.setTextCursor(cursor)
            self._caption_view.ensureCursorVisible()
        except Exception:
            pass

    def _update_save_enabled(self) -> None:
        try:
            self._save_btn.setEnabled(len(self._transcript_lines) > 0)
        except Exception:
            pass

    def _can_speak(self) -> bool:
        try:
            if self._capture.is_active():
                return False
            cfg = load_config()
            if not bool(cfg.tts_enabled):
                return False
            return len(self._transcript_lines) > 0 or bool(self._current_partial.strip())
        except Exception:
            return False

    def _update_speak_enabled(self) -> None:
        try:
            self._speak_btn.setEnabled(self._can_speak())
        except Exception:
            pass

    # TTS speaking state callback (called from worker thread)
    def _on_tts_speaking(self, speaking: bool) -> None:
        # Emit signal to be handled in UI thread
        try:
            self.tts_speaking_changed.emit(bool(speaking))
        except Exception:
            pass

    # Runs in UI thread
    def _on_tts_speaking_ui(self, speaking: bool) -> None:
        self._is_tts_speaking = bool(speaking)
        if not speaking:
            self._manual_tts_active = False
            try:
                if not self._capture.is_active():
                    self._speak_btn.setEnabled(self._can_speak())
                    # If controls exist, update them; guard for attributes
                    if hasattr(self, "_stop_speak_btn"):
                        self._stop_speak_btn.setEnabled(False)
                    if hasattr(self, "_restart_speak_btn"):
                        self._restart_speak_btn.setEnabled(self._can_speak())
            except Exception:
                pass

    # Event filter to allow dragging from child widgets
    def eventFilter(self, obj: Any, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        try:
            if event.type() == QtCore.QEvent.Type.MouseButtonPress and isinstance(event, QtGui.QMouseEvent):
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    global_pos = event.globalPosition().toPoint()
                    self._drag_offset = global_pos - self.frameGeometry().topLeft()
                    return True
            if event.type() == QtCore.QEvent.Type.MouseMove and isinstance(event, QtGui.QMouseEvent):
                if (event.buttons() & QtCore.Qt.MouseButton.LeftButton) and self._drag_offset is not None:
                    global_pos = event.globalPosition().toPoint()
                    self.move(global_pos - self._drag_offset)
                    return True
            if event.type() == QtCore.QEvent.Type.MouseButtonRelease and isinstance(event, QtGui.QMouseEvent):
                self._drag_offset = None
                return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    # Drag to move
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            self._drag_offset = global_pos - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if (event.buttons() & QtCore.Qt.MouseButton.LeftButton) and self._drag_offset is not None:
            global_pos = event.globalPosition().toPoint()
            self.move(global_pos - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        self._drag_offset = None
        super().mouseReleaseEvent(event)
