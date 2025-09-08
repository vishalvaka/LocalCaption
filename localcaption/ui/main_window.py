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
from ..utils.config import load_config
from ..utils.models import ensure_model_downloaded


class MainWindow(QtWidgets.QWidget):
    caption_updated = QtCore.pyqtSignal(str)  # type: ignore

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
        self._close_btn = QtWidgets.QPushButton("×")
        self._close_btn.setFixedWidth(28)
        self._close_btn.setToolTip("Close")

        self._metrics_label = QtWidgets.QLabel("Latency: -- ms | CPU: -- %")
        self._metrics_label.setStyleSheet("color: #ddd;")

        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self._start_btn)
        buttons.addWidget(self._stop_btn)
        buttons.addWidget(self._save_btn)
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
        self._asr: Optional[StreamingASREngine] = None
        self._transcript_lines: list[str] = []
        self._current_partial: str = ""
        self._last_latency_ms: float = 0.0
        self._config_dirty: bool = False
        self._metrics_timer = QtCore.QTimer(self)
        self._metrics_timer.timeout.connect(self._update_metrics)
        self._metrics_timer.start(500)

        self._drag_offset: Optional[QtCore.QPoint] = None

        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn.clicked.connect(self._on_stop)
        self._save_btn.clicked.connect(self._on_save)
        self._close_btn.clicked.connect(self._on_close_clicked)
        self._config_btn.clicked.connect(self._on_configure)

        # Signals
        self.caption_updated.connect(self._on_caption_updated)

        # Cache Qt namespace for readability
        self._QT = QtCore.Qt
        self._update_save_enabled()

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
            self._asr = StreamingASREngine(model_dir=model_dir)
            self._config_dirty = False
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Model missing", f"{e}\nRun: python setup_models.py")

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
        self._capture.start()

    def _on_stop(self) -> None:
        self._capture.stop()
        # Finalize any partial to allow saving
        if self._current_partial.strip():
            self._transcript_lines.append(self._current_partial.strip())
            self._current_partial = ""
        self._render_captions()
        self._update_save_enabled()

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
                self._update_save_enabled()
            self._current_partial = ""
            self._render_captions()
        else:
            self._set_caption(res.text)

    @QtCore.pyqtSlot()
    def _update_metrics(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        self._metrics_label.setText(f"Latency: {int(self._last_latency_ms)} ms | CPU: {int(cpu)} %")

    def _set_caption(self, text: str) -> None:
        self.caption_updated.emit(text)

    def _on_caption_updated(self, text: str) -> None:
        self._current_partial = text
        self._render_captions()

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
