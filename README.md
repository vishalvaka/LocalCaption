# LocalCaption

Live captions for any audio playing on your computer - fully on-device, no cloud required.

## Features

- **Real-time captions** with <800ms latency target
- **Fully on-device** - no internet connection required
- **Cross-platform** - Windows (WASAPI loopback) and macOS (CoreAudio/BlackHole)
- **Always-on-top overlay** with configurable opacity
- **Multiple export formats** - TXT, VTT, SRT
- **Performance monitoring** - latency and CPU usage tracking
- **Streaming ASR** using sherpa-onnx with Zipformer/Paraformer models

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Windows 10/11 or macOS 10.15+
- Audio device with loopback capability (Windows) or BlackHole (macOS)

### WSL Users

If you're running in WSL, you have two options:

1. **Run on Windows (Recommended)**: Use the provided scripts to run LocalCaption directly on Windows
2. **Set up audio bridge**: Follow the WSL audio setup guide (see `WSL_AUDIO_SETUP.md`)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/LocalCaption.git
   cd LocalCaption
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download ASR models:**
   ```bash
   python setup_models.py
   ```

4. **Run the application:**
   ```bash
   python -m localcaption.main
   ```

### WSL Users - Quick Start

**Option 1: Run on Windows (Easiest)**
```bash
# Copy to Windows Desktop
cp -r . /mnt/c/Users/$USER/Desktop/LocalCaption

# Run Windows version
cd /mnt/c/Users/$USER/Desktop/LocalCaption
cmd.exe /c "run_on_windows.bat"
```

**Option 2: Set up audio bridge**
```bash
# Follow the detailed guide
cat WSL_AUDIO_SETUP.md

# Test audio setup
python test_wsl_audio.py
```

### Building Standalone Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller build.spec

# The executable will be in dist/LocalCaption/
```

## Usage

### Basic Usage

1. **Launch LocalCaption**
2. **Select audio source** - choose your system audio or specific device
3. **Click "Start Captions"** - begin real-time transcription
4. **View captions** - see live captions in the always-on-top overlay
5. **Export transcript** - save as TXT, VTT, or SRT format

### Audio Sources

#### Windows
- **System Audio (Loopback)** - Captures all system audio including applications
- **Microphone** - Captures microphone input
- **Specific Applications** - Use Windows audio routing tools

#### macOS
- **BlackHole** - Virtual audio device for system audio capture
- **Built-in Microphone** - Direct microphone input
- **Audio Hijack** - For advanced audio routing

### Configuration

#### ASR Models
- **Zipformer Tiny** (~20MB) - Fast, good accuracy
- **Paraformer Tiny** (~30MB) - Better accuracy, slightly slower

#### Display Settings
- **Opacity** - Adjust caption overlay transparency
- **Always on Top** - Keep captions visible over other windows
- **Position** - Drag to reposition caption overlay

## Architecture

```
LocalCaption/
├── localcaption/
│   ├── audio/          # Audio capture and processing
│   ├── asr/            # Speech recognition engine
│   ├── ui/             # User interface components
│   ├── utils/          # Utilities and helpers
│   └── main.py         # Application entry point
├── models/             # ASR model files
├── requirements.txt    # Python dependencies
├── setup_models.py     # Model download script
└── build.spec          # PyInstaller configuration
```

### Key Components

- **AudioCapture** - Platform-specific audio capture with WASAPI/CoreAudio
- **ASREngine** - Streaming speech recognition using sherpa-onnx
- **MainWindow** - PyQt6-based user interface
- **CaptionDisplay** - Always-on-top caption overlay
- **PerformanceMonitor** - Real-time metrics tracking

## Performance

### Latency Targets
- **Target**: <800ms end-to-end latency
- **Typical**: 200-500ms on modern hardware
- **Factors**: Model size, CPU performance, audio buffer size

### System Requirements
- **CPU**: 2+ cores recommended
- **RAM**: 4GB+ available memory
- **Storage**: 100MB for models and application
- **Audio**: Loopback-capable audio device

### Optimization Tips
1. **Use smaller models** for lower latency
2. **Close unnecessary applications** to free CPU
3. **Use SSD storage** for faster model loading
4. **Adjust audio buffer size** in settings

## Troubleshooting

### Common Issues

#### No Audio Devices Found
- **Windows**: Ensure Windows Audio Service is running
- **macOS**: Install BlackHole for system audio capture
- **Linux**: Check ALSA/PulseAudio configuration

#### High Latency
- Try smaller ASR model (Zipformer Tiny)
- Close other CPU-intensive applications
- Check audio buffer settings

#### Poor Recognition Accuracy
- Ensure clear audio input
- Try different ASR model
- Check microphone/audio source quality

#### Application Crashes
- Check Python version (3.8+ required)
- Verify all dependencies installed
- Check system audio drivers

### Debug Mode

Run with verbose logging:
```bash
python -m localcaption.main --verbose
```

Check dependencies:
```bash
python -m localcaption.main --check-deps
```

## Development

### Project Structure
- **Modular design** - Easy to extend and modify
- **Platform abstraction** - Clean separation of platform-specific code
- **Async processing** - Non-blocking audio and ASR processing
- **Configurable** - Easy to adjust settings and parameters

### Adding New Features
1. **Audio Sources** - Extend `AudioCapture` class
2. **ASR Models** - Add to `ModelManager`
3. **Export Formats** - Extend `TranscriptExporter`
4. **UI Components** - Add to PyQt6 interface

### Building for Distribution
```bash
# Create distribution package
python setup.py sdist bdist_wheel

# Build standalone executable
pyinstaller build.spec

# Test on target platform
./dist/LocalCaption/LocalCaption.exe
```

## Roadmap

### Phase 1 (Current)
- [x] Desktop MVP with PyQt6
- [x] Windows WASAPI loopback support
- [x] Streaming ASR with sherpa-onnx
- [x] Basic export functionality

### Phase 2 (Next)
- [ ] macOS CoreAudio/BlackHole support
- [ ] Advanced audio routing options
- [ ] Custom model support
- [ ] Plugin system

### Phase 3 (Future)
- [ ] Android app using shared components
- [ ] Cloud sync for transcripts
- [ ] Advanced editing features
- [ ] Multi-language support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) - Streaming ASR engine
- [sounddevice](https://github.com/spatialaudio/python-sounddevice) - Audio capture
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [BlackHole](https://github.com/ExistentialAudio/BlackHole) - macOS audio routing