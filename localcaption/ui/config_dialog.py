from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtWidgets  # type: ignore

from ..audio.capture import AudioCapture
from ..utils.config import AppConfig, load_config, save_config
from ..utils.models import MODEL_REGISTRY


class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure")
        self.setModal(True)
        layout = QtWidgets.QVBoxLayout(self)

        self._model_combo = QtWidgets.QComboBox()
        for mid, info in MODEL_REGISTRY.items():
            self._model_combo.addItem(info.name, mid)

        self._device_combo = QtWidgets.QComboBox()
        self._device_combo.addItem("Default output (WASAPI)", -1)
        cap = AudioCapture()
        try:
            devices = cap.list_devices()
            for idx, d in enumerate(devices):
                name = d.get('name', f'Device {idx}')
                self._device_combo.addItem(name, idx)
        except Exception:
            pass

        form = QtWidgets.QFormLayout()
        form.addRow("Model", self._model_combo)
        form.addRow("Input device", self._device_combo)
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
        if cfg.selected_device_index is not None:
            idx = self._device_combo.findData(cfg.selected_device_index)
            if idx >= 0:
                self._device_combo.setCurrentIndex(idx)

    def get_config(self) -> AppConfig:
        return AppConfig(
            selected_model_id=self._model_combo.currentData(),
            selected_device_index=self._device_combo.currentData(),
        )

    @staticmethod
    def run_modal(parent=None) -> Optional[AppConfig]:
        dlg = ConfigDialog(parent)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            cfg = dlg.get_config()
            save_config(cfg)
            return cfg
        return None
