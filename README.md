# LocalCaption (Desktop MVP)

Live on-device captions for any audio playing on your computer.

- ASR: sherpa-onnx (streaming Zipformer tiny)
- Audio capture: sounddevice (WASAPI loopback on Windows; CoreAudio/BlackHole on macOS)
- UI: PyQt5 always-on-top overlay (draggable, Start/Stop/Save, Close button)
- Packaging: PyInstaller

## Quickstart (dev)

1) Create venv and install deps

```bash
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

2) Download a small streaming model (required)

```bash
python setup_models.py --en-tiny
```

This creates a folder under `models/` like:
- `models/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17/`

3) Run the app (dev)

```bash
python run.py
```

Notes:
- On Windows: ensure audio is playing through the system "Default" output device. The app captures the default WASAPI output via loopback.
- On macOS: route audio to a virtual device (e.g., BlackHole) and select it as the system output.

## Build and distribute

You can ship either a one-folder (recommended for portable) or one-file EXE.

### Option A: One-folder (recommended for easy shipping)

1) Ensure models exist before building (so they get bundled):
```bash
python setup_models.py --en-tiny
```

2) Build:
```bash
pyinstaller build.spec
```

3) Ship the folder:
- Distribute the entire `dist/LocalCaption/` folder
- Entry point: `dist/LocalCaption/LocalCaption.exe`
- Models are bundled under `dist/LocalCaption/models/`

### Option B: One-file (single EXE)

Build a single EXE. Startup may be slightly slower due to extraction.
```bash
pyinstaller --noconsole --onefile --name LocalCaption run.py
```
- Output: `dist/LocalCaption.exe`
- The EXE contains all dependencies and models; at first launch it extracts its contents to a temp dir.
- If you prefer to keep models next to the EXE instead, create a sibling `models/` directory next to `LocalCaption.exe` before running. The app will look in the bundled data first, then in `./models`.

### Windows SmartScreen
- Unsigned binaries may show a SmartScreen warning. Use "More info → Run anyway" or sign the binary for distribution.

## App usage

- Start: begins capturing from the default output device and streaming ASR.
- Stop: stops capture.
- Save: writes the transcript to `.txt` and a basic `.vtt`.
- The overlay is always-on-top, frameless, draggable, and has a close button.
- Metrics: bottom-left shows current ASR latency and CPU%.

## Troubleshooting

- No captions appear:
  - Ensure audio is actually playing through the Windows default output device (check Sound settings).
  - Try raising the volume and make sure no exclusive-mode apps are holding the device.
  - For macOS, route the system audio to BlackHole and set it as default output.
- "Model missing" dialog:
  - Run: `python setup_models.py --en-tiny`
  - Confirm a folder exists under `models/` with `tokens.txt` and `*.onnx` files.
  - If using one-folder build, rebuild after models are downloaded so they get included.
- First launch is slow:
  - One-file EXE extracts itself on first run; subsequent launches are faster.
- WASAPI loopback device issues:
  - Ensure you are on Windows 10/11 and the device you expect is set as Default.

## Dev notes

- The app auto-detects the model file names (tokens/encoder*/decoder*/joiner*).
- When frozen (PyInstaller), the app resolves `models/` inside the bundle; when running from source, it uses the workspace `models/`.
