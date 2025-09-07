"""
Main window for LocalCaption
"""

import sys
import os
import time
import logging
from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QTextEdit, QCheckBox,
    QSpinBox, QGroupBox, QProgressBar, QSystemTrayIcon, QMenu,
    QMessageBox, QFileDialog, QSplitter, QFrame
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSettings, QSize
)
from PyQt6.QtGui import QFont, QIcon, QAction, QPalette, QColor

from ..audio.capture import AudioCapture, AudioProcessor
from ..asr.engine import ASREngine, ModelManager, create_default_config

logger = logging.getLogger(__name__)


class CaptionDisplay(QFrame):
    """Always-on-top caption display widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_styling()
        
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Caption text
        self.caption_label = QLabel("Ready to start captions...")
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption_label.setWordWrap(True)
        self.caption_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        
        # Metrics display
        self.metrics_label = QLabel("")
        self.metrics_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.metrics_label.setFont(QFont("Arial", 10))
        
        layout.addWidget(self.caption_label)
        layout.addWidget(self.metrics_label)
        
        self.setLayout(layout)
        
    def setup_styling(self):
        """Setup styling for the caption display"""
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Semi-transparent background
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 180);
                border-radius: 10px;
                border: 2px solid rgba(255, 255, 255, 100);
            }
            QLabel {
                color: white;
                background-color: transparent;
            }
        """)
        
    def update_caption(self, text: str):
        """Update caption text"""
        self.caption_label.setText(text)
        
    def update_metrics(self, latency: float, cpu_percent: float):
        """Update metrics display"""
        self.metrics_label.setText(f"Latency: {latency:.1f}ms | CPU: {cpu_percent:.1f}%")
        
    def set_opacity(self, opacity: float):
        """Set window opacity (0.0 to 1.0)"""
        self.setWindowOpacity(opacity)


class AudioWorker(QThread):
    """Worker thread for audio processing"""
    
    audio_ready = pyqtSignal(object)  # Emits audio data
    caption_ready = pyqtSignal(str)   # Emits caption text
    metrics_request = pyqtSignal()    # Request metrics update
    
    def __init__(self, audio_capture: AudioCapture, asr_engine: ASREngine):
        super().__init__()
        self.audio_capture = audio_capture
        self.asr_engine = asr_engine
        self.is_running = False
        
    def run(self):
        """Main worker loop"""
        try:
            self.is_running = True
            
            def audio_callback(audio_data):
                if self.is_running:
                    self.audio_ready.emit(audio_data)
            
            def asr_callback(text):
                if self.is_running:
                    self.caption_ready.emit(text)
            
            # Start audio capture and ASR
            if not self.audio_capture.start_capture(callback=audio_callback):
                logger.error("Failed to start audio capture")
                return
                
            if not self.asr_engine.start_recognition(callback=asr_callback):
                logger.error("Failed to start ASR recognition")
                return
            
            # Process audio
            while self.is_running:
                self.msleep(10)
            
        except Exception as e:
            logger.error(f"Error in AudioWorker: {e}", exc_info=True)
        finally:
            # Cleanup
            try:
                self.audio_capture.stop_capture()
                self.asr_engine.stop_recognition()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
    
    def stop(self):
        """Stop the worker"""
        self.is_running = False
        self.wait(3000)  # Wait up to 3 seconds
    
    def get_metrics(self):
        """Get current performance metrics"""
        if not self.is_running:
            return 0.0, 0.0
            
        import psutil
        latency = self.asr_engine.get_average_latency() * 1000  # Convert to ms
        cpu_percent = psutil.cpu_percent()
        return latency, cpu_percent


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.audio_capture = None
        self.asr_engine = None
        self.audio_worker = None
        self.caption_display = None
        self.settings = QSettings("LocalCaption", "Settings")
        
        # Metrics timer (must be in main thread)
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self.update_metrics)
        
        self.setup_ui()
        self.setup_audio()
        self.setup_asr()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("LocalCaption - Live Captions")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Left panel - Controls
        controls_panel = self.create_controls_panel()
        
        # Right panel - Caption display and logs
        display_panel = self.create_display_panel()
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(controls_panel)
        splitter.addWidget(display_panel)
        splitter.setSizes([300, 500])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def create_controls_panel(self) -> QWidget:
        """Create the controls panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Audio source selection
        audio_group = QGroupBox("Audio Source")
        audio_layout = QVBoxLayout()
        
        self.audio_device_combo = QComboBox()
        self.refresh_devices_btn = QPushButton("Refresh")
        self.refresh_devices_btn.clicked.connect(self.refresh_audio_devices)
        
        audio_layout.addWidget(QLabel("Audio Device:"))
        audio_layout.addWidget(self.audio_device_combo)
        audio_layout.addWidget(self.refresh_devices_btn)
        audio_group.setLayout(audio_layout)
        
        # ASR model selection
        model_group = QGroupBox("ASR Model")
        model_layout = QVBoxLayout()
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["zipformer_bilingual"])
        
        model_layout.addWidget(QLabel("Model:"))
        model_layout.addWidget(self.model_combo)
        model_group.setLayout(model_layout)
        
        # Control buttons
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout()
        
        self.start_btn = QPushButton("Start Captions")
        self.start_btn.clicked.connect(self.toggle_captions)
        
        self.stop_btn = QPushButton("Stop Captions")
        self.stop_btn.clicked.connect(self.stop_captions)
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_group.setLayout(control_layout)
        
        # Display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(80)
        self.opacity_slider.valueChanged.connect(self.update_opacity)
        
        self.always_on_top_cb = QCheckBox("Always on Top")
        self.always_on_top_cb.setChecked(True)
        self.always_on_top_cb.toggled.connect(self.toggle_always_on_top)
        
        display_layout.addWidget(QLabel("Opacity:"))
        display_layout.addWidget(self.opacity_slider)
        display_layout.addWidget(self.always_on_top_cb)
        display_group.setLayout(display_layout)
        
        # Export controls
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout()
        
        self.export_txt_btn = QPushButton("Export as TXT")
        self.export_vtt_btn = QPushButton("Export as VTT")
        self.export_srt_btn = QPushButton("Export as SRT")
        
        self.export_txt_btn.clicked.connect(lambda: self.export_transcript("txt"))
        self.export_vtt_btn.clicked.connect(lambda: self.export_transcript("vtt"))
        self.export_srt_btn.clicked.connect(lambda: self.export_transcript("srt"))
        
        export_layout.addWidget(self.export_txt_btn)
        export_layout.addWidget(self.export_vtt_btn)
        export_layout.addWidget(self.export_srt_btn)
        export_group.setLayout(export_layout)
        
        # Add all groups to layout
        layout.addWidget(audio_group)
        layout.addWidget(model_group)
        layout.addWidget(control_group)
        layout.addWidget(display_group)
        layout.addWidget(export_group)
        layout.addStretch()
        
        return panel
    
    def create_display_panel(self) -> QWidget:
        """Create the display panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Caption display
        self.caption_text = QTextEdit()
        self.caption_text.setReadOnly(True)
        self.caption_text.setFont(QFont("Arial", 12))
        self.caption_text.setPlaceholderText("Captions will appear here...")
        
        # Performance metrics
        metrics_group = QGroupBox("Performance")
        metrics_layout = QVBoxLayout()
        
        self.latency_label = QLabel("Latency: -- ms")
        self.cpu_label = QLabel("CPU: -- %")
        self.memory_label = QLabel("Memory: -- MB")
        
        metrics_layout.addWidget(self.latency_label)
        metrics_layout.addWidget(self.cpu_label)
        metrics_layout.addWidget(self.memory_label)
        metrics_group.setLayout(metrics_layout)
        
        layout.addWidget(QLabel("Live Captions:"))
        layout.addWidget(self.caption_text)
        layout.addWidget(metrics_group)
        
        return panel
    
    def setup_audio(self):
        """Setup audio capture"""
        self.audio_capture = AudioCapture()
        self.refresh_audio_devices()
    
    def setup_asr(self):
        """Setup ASR engine"""
        config = create_default_config()
        model_config = ModelManager.get_model_config(config['model_name'])
        
        if model_config:
            self.asr_engine = ASREngine(model_config)
            if not self.asr_engine.initialize():
                QMessageBox.warning(self, "ASR Error", "Failed to initialize ASR engine")
        else:
            QMessageBox.warning(self, "Model Error", "ASR model not found. Please download models.")
    
    def refresh_audio_devices(self):
        """Refresh audio device list"""
        if not self.audio_capture:
            return
        
        self.audio_device_combo.clear()
        devices = self.audio_capture.get_audio_devices()
        
        for device in devices:
            device_name = device['name']
            if device['is_loopback']:
                device_name += " (Loopback)"
            self.audio_device_combo.addItem(device_name, device['index'])
    
    def toggle_captions(self):
        """Toggle caption capture"""
        if self.audio_worker and self.audio_worker.isRunning():
            self.stop_captions()
        else:
            self.start_captions()
    
    def start_captions(self):
        """Start caption capture"""
        try:
            if not self.audio_capture or not self.asr_engine:
                QMessageBox.warning(self, "Error", "Audio or ASR not initialized")
                return
            
            # Get selected device
            device_index = self.audio_device_combo.currentData()
            if device_index is None:
                QMessageBox.warning(self, "Error", "Please select an audio device")
                return
            
            # Create worker thread
            self.audio_worker = AudioWorker(self.audio_capture, self.asr_engine)
            self.audio_worker.audio_ready.connect(self.process_audio)
            self.audio_worker.caption_ready.connect(self.update_caption)
            
            # Start worker
            self.audio_worker.start()
            
            # Start metrics timer in main thread
            self.metrics_timer.start(1000)  # Update every second
            
            # Update UI
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.statusBar().showMessage("Capturing audio...")
            
            # Show caption display
            self.show_caption_display()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start captions: {str(e)}")
            logger.error(f"Error starting captions: {e}", exc_info=True)
    
    def stop_captions(self):
        """Stop caption capture"""
        if self.audio_worker:
            self.audio_worker.stop()
            self.audio_worker = None
        
        # Stop metrics timer
        self.metrics_timer.stop()
        
        # Update UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("Stopped")
        
        # Hide caption display
        if self.caption_display:
            self.caption_display.hide()
    
    def process_audio(self, audio_data):
        """Process incoming audio data"""
        if self.asr_engine:
            self.asr_engine.add_audio(audio_data)
    
    def update_caption(self, text: str):
        """Update caption display"""
        self.caption_text.append(text)
        
        # Update caption display
        if self.caption_display:
            self.caption_display.update_caption(text)
    
    def update_metrics(self):
        """Update performance metrics"""
        if self.audio_worker and self.audio_worker.is_running:
            latency, cpu_percent = self.audio_worker.get_metrics()
            self.latency_label.setText(f"Latency: {latency:.1f} ms")
            self.cpu_label.setText(f"CPU: {cpu_percent:.1f} %")
            
            # Update memory usage
            import psutil
            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            self.memory_label.setText(f"Memory: {memory_mb:.1f} MB")
            
            # Update caption display metrics
            if self.caption_display:
                self.caption_display.update_metrics(latency, cpu_percent)
    
    def show_caption_display(self):
        """Show the always-on-top caption display"""
        if not self.caption_display:
            self.caption_display = CaptionDisplay()
        
        # Position at top of screen
        screen = QApplication.primaryScreen().geometry()
        self.caption_display.move(screen.x() + 50, screen.y() + 50)
        self.caption_display.resize(600, 100)
        
        # Set opacity
        opacity = self.opacity_slider.value() / 100.0
        self.caption_display.set_opacity(opacity)
        
        self.caption_display.show()
    
    def update_opacity(self, value: int):
        """Update caption display opacity"""
        if self.caption_display:
            opacity = value / 100.0
            self.caption_display.set_opacity(opacity)
    
    def toggle_always_on_top(self, checked: bool):
        """Toggle always on top for caption display"""
        if self.caption_display:
            if checked:
                self.caption_display.setWindowFlags(
                    self.caption_display.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
                )
            else:
                self.caption_display.setWindowFlags(
                    self.caption_display.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint
                )
            self.caption_display.show()
    
    def export_transcript(self, format_type: str):
        """Export transcript in specified format"""
        text = self.caption_text.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "Export", "No transcript to export")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, f"Export Transcript as {format_type.upper()}", 
            f"transcript.{format_type}", 
            f"{format_type.upper()} files (*.{format_type})"
        )
        
        if filename:
            try:
                if format_type == "txt":
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(text)
                elif format_type == "vtt":
                    self.export_vtt(filename, text)
                elif format_type == "srt":
                    self.export_srt(filename, text)
                
                QMessageBox.information(self, "Export", f"Transcript exported to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")
    
    def export_vtt(self, filename: str, text: str):
        """Export as WebVTT format"""
        lines = text.split('\n')
        vtt_content = "WEBVTT\n\n"
        
        for i, line in enumerate(lines):
            if line.strip():
                start_time = i * 5  # 5 seconds per line
                end_time = start_time + 5
                vtt_content += f"{start_time:02d}:00:00.000 --> {end_time:02d}:00:00.000\n"
                vtt_content += f"{line.strip()}\n\n"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(vtt_content)
    
    def export_srt(self, filename: str, text: str):
        """Export as SRT format"""
        lines = text.split('\n')
        srt_content = ""
        
        for i, line in enumerate(lines):
            if line.strip():
                start_time = i * 5  # 5 seconds per line
                end_time = start_time + 5
                srt_content += f"{i + 1}\n"
                srt_content += f"00:00:{start_time:02d},000 --> 00:00:{end_time:02d},000\n"
                srt_content += f"{line.strip()}\n\n"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(srt_content)
    
    def load_settings(self):
        """Load application settings"""
        # Load window geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Load other settings
        opacity = self.settings.value("opacity", 80, type=int)
        self.opacity_slider.setValue(opacity)
        
        always_on_top = self.settings.value("always_on_top", True, type=bool)
        self.always_on_top_cb.setChecked(always_on_top)
    
    def save_settings(self):
        """Save application settings"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("opacity", self.opacity_slider.value())
        self.settings.setValue("always_on_top", self.always_on_top_cb.isChecked())
    
    def closeEvent(self, event):
        """Handle application close"""
        self.stop_captions()
        self.save_settings()
        event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("LocalCaption")
    app.setApplicationVersion("0.1.0")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
