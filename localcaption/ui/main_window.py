from __future__ import annotations

import os
import sys
import threading
import time
from typing import Optional, Any, cast

import numpy as np
import psutil
from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore

from ..audio.capture import AudioCapture
from ..asr.engine import StreamingASREngine, RecognitionResult


class MainWindow(QtWidgets.QWidget):
    caption_updated = QtCore.pyqtSignal(str)  # type: ignore

    def __init__(self) -> None:
        super().__init__()
        QT: Any = cast(Any, QtCore.Qt)
        self.setWindowTitle("LocalCaption")
        self.setWindowFlags(
            QT.WindowStaysOnTopHint
            | QT.FramelessWindowHint
            | QT.Tool
        )
        self.setAttribute(QT.WA_TranslucentBackground)

        self._caption_label = QtWidgets.QLabel("")
        self._caption_label.setWordWrap(True)
        font = QtGui.QFont("Segoe UI", 14)
        self._caption_label.setFont(font)
        self._caption_label.setStyleSheet("color: white; background-color: rgba(0,0,0,160); padding: 8px; border-radius: 6px;")

        self._start_btn = QtWidgets.QPushButton("Start")
        self._stop_btn = QtWidgets.QPushButton("Stop")
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
        buttons.addStretch(1)
        buttons.addWidget(self._metrics_label)
        buttons.addSpacing(8)
        buttons.addWidget(self._close_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(buttons)
        layout.addWidget(self._caption_label)

        self.resize(800, 160)

        # State
        self._capture = AudioCapture()
        self._capture.set_consumer(self._on_pcm)
        self._asr: Optional[StreamingASREngine] = None
        self._transcript_lines: list[str] = []
        self._last_latency_ms: float = 0.0
        self._metrics_timer = QtCore.QTimer(self)
        self._metrics_timer.timeout.connect(self._update_metrics)
        self._metrics_timer.start(500)

        self._drag_offset: Optional[QtCore.QPoint] = None

        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn.clicked.connect(self._on_stop)
        self._save_btn.clicked.connect(self._on_save)
        self._close_btn.clicked.connect(self._on_close_clicked)

        # Signals
        self.caption_updated.connect(self._caption_label.setText)

        self._QT = QT

    @QtCore.pyqtSlot()
    def _on_close_clicked(self) -> None:  # type: ignore[no-untyped-def]
        self.close()

    def _models_root(self) -> str:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base = sys._MEIPASS  # type: ignore[attr-defined]
        else:
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        return os.path.join(base, "models")

    def _ensure_asr(self) -> None:
        if self._asr is not None:
            return
        model_dir = os.path.join(self._models_root(), "sherpa-onnx-streaming-zipformer-en-20M-2023-02-17")
        try:
            self._asr = StreamingASREngine(model_dir=model_dir)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Model missing", f"{e}\nRun: python setup_models.py --en-tiny")

    def _on_start(self) -> None:
        self._ensure_asr()
        if self._asr is None:
            return
        self._transcript_lines.clear()
        self._capture.start()

    def _on_stop(self) -> None:
        self._capture.stop()

    def _on_save(self) -> None:
        if not self._transcript_lines:
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
        res: Optional[RecognitionResult] = self._asr.accept_pcm(pcm.astype(np.float32), sample_rate, timestamp)
        if res is None:
            return
        self._last_latency_ms = res.latency_ms
        if res.is_final:
            if res.text:
                self._transcript_lines.append(res.text)
            self._set_caption("")
        else:
            self._set_caption(res.text)

    @QtCore.pyqtSlot()
    def _update_metrics(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        self._metrics_label.setText(f"Latency: {int(self._last_latency_ms)} ms | CPU: {int(cpu)} %")

    def _set_caption(self, text: str) -> None:
        self.caption_updated.emit(text)

    # Drag to move
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == self._QT.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if (event.buttons() & self._QT.LeftButton) and self._drag_offset is not None:
            self.move(event.globalPos() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        self._drag_offset = None
        super().mouseReleaseEvent(event)
