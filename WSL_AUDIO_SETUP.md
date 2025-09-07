# WSL Audio Setup for LocalCaption

Since WSL doesn't have direct access to Windows audio devices, you need to set up an audio bridge. Here are the best options:

## Option 1: VB-Cable (Recommended - Easiest)

### Windows Setup:
1. **Download VB-Cable**: https://vb-audio.com/Cable/
2. **Install VB-Cable** (restart required)
3. **Configure Windows Audio**:
   - Right-click speaker icon → "Open Sound settings"
   - Set "Choose your output device" to "CABLE Input (VB-Audio Virtual Cable)"
   - Go to "Sound Control Panel" → "Recording" tab
   - Set "CABLE Output (VB-Audio Virtual Cable)" as default recording device

### WSL Setup:
```bash
# Install audio tools
sudo apt update
sudo apt install -y alsa-utils pulseaudio

# Start PulseAudio
pulseaudio --start

# Check if VB-Cable is detected
aplay -l
arecord -l
```

## Option 2: VoiceMeeter (Advanced)

### Windows Setup:
1. **Download VoiceMeeter**: https://vb-audio.com/Voicemeeter/
2. **Install VoiceMeeter** (restart required)
3. **Configure VoiceMeeter**:
   - Set Hardware Input to your microphone
   - Set Hardware Output to your speakers
   - Enable "A1" output to route to WSL

### WSL Setup:
```bash
# Same as Option 1
sudo apt install -y alsa-utils pulseaudio
pulseaudio --start
```

## Option 3: PulseAudio for Windows

### Windows Setup:
1. **Download PulseAudio for Windows**: https://www.freedesktop.org/wiki/Software/PulseAudio/Ports/Windows/
2. **Install and configure** to route audio to WSL

## Option 4: Use Windows Executable (Simplest)

Since you're in WSL, the easiest solution is to run the Windows executable directly:

```bash
# Build Windows executable from WSL
pyinstaller build.spec

# Run the Windows executable
./dist/LocalCaption.exe
```

## Testing Audio in WSL

After setting up audio bridge:

```bash
# Test playback
speaker-test -t wav

# Test recording
arecord -f cd -d 5 test.wav
aplay test.wav

# Check available devices
python -c "import sounddevice; print(sounddevice.query_devices())"
```

## Troubleshooting

1. **No audio devices found**: Make sure VB-Cable is installed and configured
2. **Permission denied**: Run `sudo usermod -a -G audio $USER` and restart WSL
3. **PulseAudio issues**: Try `pulseaudio --kill && pulseaudio --start`

## Alternative: Run on Windows

The simplest approach is to run LocalCaption directly on Windows:

1. Install Python on Windows
2. Copy the LocalCaption folder to Windows
3. Run `pip install -r requirements.txt`
4. Run `python run.py`

This gives you direct access to Windows audio devices without any bridge setup.
