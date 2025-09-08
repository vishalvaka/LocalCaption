from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtWidgets  # type: ignore

from ..audio.capture import AudioCapture
from ..utils.config import AppConfig, load_config, save_config
from ..utils.models import MODEL_REGISTRY
from ..tts.engine import LocalTTSEngine


class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure")
        self.setModal(True)
        layout = QtWidgets.QVBoxLayout(self)

        self._model_combo = QtWidgets.QComboBox()
        for mid, info in MODEL_REGISTRY.items():
            self._model_combo.addItem(info.name, mid)

        # Simplified audio source
        self._audio_source = QtWidgets.QComboBox()
        self._audio_source.addItem("Internal audio (system output)", "internal")
        self._audio_source.addItem("Microphone (default input)", "microphone")

        # STT backend controls
        self._stt_backend = QtWidgets.QComboBox()
        self._stt_backend.addItem("Local (sherpa-onnx)", "local")
        self._stt_backend.addItem("Deepgram (cloud)", "deepgram")
        self._deepgram_key = QtWidgets.QLineEdit()
        self._deepgram_key.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self._deepgram_model = QtWidgets.QComboBox()
        self._deepgram_model.addItem("Auto (server default)", "")
        self._deepgram_model.addItem("nova-2-general", "nova-2-general")
        self._deepgram_model.addItem("nova-2-meeting", "nova-2-meeting")
        self._deepgram_model.addItem("nova-2-telephony", "nova-2-telephony")
        self._deepgram_model.addItem("nova-2-conversationalai", "nova-2-conversationalai")

        # TTS controls
        self._tts_enable = QtWidgets.QCheckBox("Enable TTS (pyttsx3)")
        self._tts_partials = QtWidgets.QCheckBox("Speak partial captions")
        self._tts_rate = QtWidgets.QSpinBox()
        self._tts_rate.setRange(80, 300)
        self._tts_rate.setSingleStep(10)
        self._tts_rate.setSpecialValueText("Default")
        self._tts_rate.setValue(0)
        self._tts_voice = QtWidgets.QComboBox()
        try:
            tts = LocalTTSEngine()
            for v in tts.list_voices():
                self._tts_voice.addItem(v.get("name") or v.get("id") or "voice", v.get("id"))
        except Exception:
            pass

        form = QtWidgets.QFormLayout()
        form.addRow("Model", self._model_combo)
        form.addRow("Audio source", self._audio_source)
        form.addRow("STT backend", self._stt_backend)
        form.addRow("Deepgram API key", self._deepgram_key)
        form.addRow("Deepgram model", self._deepgram_model)
        form.addRow(self._tts_enable)
        form.addRow(self._tts_partials)
        form.addRow("TTS rate (WPM)", self._tts_rate)
        form.addRow("TTS voice", self._tts_voice)
        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_current()

    def _load_current(self) -> None:
        cfg = load_config()
        if cfg.selected_model_id:
            idx = self._model_combo.findData(cfg.selected_model_id)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)
        try:
            sidx = self._audio_source.findData(cfg.audio_source or "internal")
            if sidx >= 0:
                self._audio_source.setCurrentIndex(sidx)
        except Exception:
            pass
        try:
            bidx = self._stt_backend.findData(cfg.stt_backend or "local")
            if bidx >= 0:
                self._stt_backend.setCurrentIndex(bidx)
            if cfg.deepgram_api_key:
                self._deepgram_key.setText(cfg.deepgram_api_key)
            if cfg.deepgram_model is not None:
                midx = self._deepgram_model.findData(cfg.deepgram_model)
                if midx >= 0:
                    self._deepgram_model.setCurrentIndex(midx)
                else:
                    self._deepgram_model.addItem(cfg.deepgram_model, cfg.deepgram_model)
                    self._deepgram_model.setCurrentIndex(self._deepgram_model.count() - 1)
        except Exception:
            pass
        try:
            self._tts_enable.setChecked(bool(cfg.tts_enabled))
            self._tts_partials.setChecked(bool(cfg.tts_speak_partials))
            self._tts_rate.setValue(int(cfg.tts_rate_wpm) if cfg.tts_rate_wpm else 0)
            if cfg.tts_voice_id is not None:
                vidx = self._tts_voice.findData(cfg.tts_voice_id)
                if vidx >= 0:
                    self._tts_voice.setCurrentIndex(vidx)
        except Exception:
            pass

    def get_config(self) -> AppConfig:
        rate = self._tts_rate.value()
        return AppConfig(
            selected_model_id=self._model_combo.currentData(),
            selected_device_index=None,  # deprecated with simplified source
            audio_source=self._audio_source.currentData(),
            stt_backend=self._stt_backend.currentData(),
            deepgram_api_key=(self._deepgram_key.text().strip() or None),
            deepgram_model=(self._deepgram_model.currentData() or None),
            tts_enabled=self._tts_enable.isChecked(),
            tts_speak_partials=self._tts_partials.isChecked(),
            tts_rate_wpm=(rate if rate > 0 else None),
            tts_voice_id=self._tts_voice.currentData(),
        )

    @staticmethod
    def run_modal(parent=None) -> Optional[AppConfig]:
        dlg = ConfigDialog(parent)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            cfg = dlg.get_config()
            save_config(cfg)
            return cfg
        return None
