# LocalCaption Release Guide

This guide explains how to create and distribute releases of LocalCaption.

## Quick Start

### For All Platforms (Python Script)
```bash
# Run the comprehensive release script
python create_release.py
```

## Release Types

### 1. Portable Release
- **What**: Single executable with all dependencies
- **Platform**: Windows, macOS, Linux
- **Size**: ~200-500MB (includes models)
- **Use case**: End users who want a simple download-and-run experience

### 2. Python Package
- **What**: Installable Python package
- **Platform**: Any platform with Python 3.8+
- **Size**: ~50MB (models downloaded separately)
- **Use case**: Developers and advanced users

### 3. Source Code
- **What**: Raw source code
- **Platform**: Any platform with Python 3.8+
- **Size**: ~5MB
- **Use case**: Developers who want to modify the code

## Building Releases

### Prerequisites
- Python 3.8 or higher
- All dependencies installed (`pip install -r requirements.txt`)
- PyInstaller (`pip install pyinstaller`)
```

### Cross-Platform Release
```bash
# Use the Python script for all platforms
python create_release.py
```

## Release Contents

### Portable Release Structure
```
LocalCaption-Release/
├── LocalCaption.exe          # Main executable (Windows)
├── LocalCaption              # Main executable (macOS/Linux)
├── models/                   # ASR models
│   └── sherpa-onnx-.../
├── run_localcaption.bat      # Windows run script
├── run_localcaption.sh       # Unix run script
├── README.md                 # Documentation
├── requirements.txt          # Python dependencies
├── VERSION.txt              # Version information
└── LICENSE                  # License file
```

## Distribution

### 1. ZIP Package
- Create a ZIP file of the `LocalCaption-Release` folder
- Name it: `LocalCaption-v1.0.0-Windows-YYYYMMDD.zip`
- Upload to GitHub Releases or your distribution platform

### 2. GitHub Releases
- Tag your release: `git tag v1.0.0`
- Push tags: `git push origin v1.0.0`
- GitHub Actions will automatically build and create a release

### 3. Direct Distribution
- Share the `LocalCaption-Release` folder directly
- Users can run `LocalCaption.exe` (Windows) or `./LocalCaption` (Unix)

## Version Management

### Semantic Versioning
- **Major** (1.0.0): Breaking changes
- **Minor** (1.1.0): New features, backward compatible
- **Patch** (1.0.1): Bug fixes, backward compatible

### Release Checklist
- [ ] Update version in `setup.py`
- [ ] Update version in `build.spec`
- [ ] Update `VERSION.txt`
- [ ] Test the build on target platform
- [ ] Update `CHANGELOG.md`
- [ ] Create git tag
- [ ] Push to repository

## Automated Releases

### GitHub Actions
The repository includes a GitHub Actions workflow (`.github/workflows/release.yml`) that automatically:
- Builds releases for Windows, macOS, and Linux
- Creates portable packages
- Uploads to GitHub Releases when you push a tag

### Triggering Automated Release
```bash
# Create and push a tag
git tag v1.0.0
git push origin v1.0.0
```

## Troubleshooting

### Common Issues

1. **PyInstaller fails to find modules**
   - Add missing modules to `hiddenimports` in `build.spec`
   - Run `pyinstaller --debug=all` for detailed logs

2. **Executable is too large**
   - Use `--exclude-module` to exclude unnecessary modules
   - Consider using `--onefile` for single file distribution

3. **Models not included**
   - Ensure `models` directory is in `datas` section of `build.spec`
   - Check that models are downloaded before building

4. **Audio device issues on target system**
   - Include audio device setup instructions
   - Provide troubleshooting guide for common audio issues

### Build Optimization

1. **Reduce executable size**
   ```python
   # In build.spec, add to excludes:
   excludes=['tkinter', 'matplotlib', 'pandas', 'scipy']
   ```

2. **Faster startup**
   ```python
   # Use --onedir instead of --onefile
   # This creates a folder with multiple files but faster startup
   ```

3. **Debug builds**
   ```bash
   pyinstaller build.spec --debug=all --console
   ```

## Release Notes Template

```markdown
# LocalCaption v1.0.0

## What's New
- Initial release
- Real-time speech recognition
- Cross-platform support
- Portable executable

## Features
- Live captions for any audio
- Local processing (no internet required)
- Customizable UI
- Multiple audio device support

## System Requirements
- Windows 10/11, macOS 10.15+, or Linux
- 4GB RAM minimum
- 1GB free disk space

## Installation
1. Download the appropriate package for your platform
2. Extract the ZIP file
3. Run `LocalCaption.exe` (Windows) or `./LocalCaption` (Unix)

## Known Issues
- Audio device detection may require manual configuration on some systems
- Large model files may take time to download on first run

## Support
- GitHub Issues: [link]
- Documentation: [link]
```

## Security Considerations

1. **Code Signing** (Windows)
   - Sign executables with a valid certificate
   - Prevents Windows SmartScreen warnings

2. **Virus Scanning**
   - Scan all release files with antivirus software
   - Some antivirus software may flag PyInstaller executables as false positives

3. **Checksums**
   - Provide SHA256 checksums for all release files
   - Allow users to verify file integrity

## License and Legal

- Ensure all dependencies are properly licensed
- Include license information in the release
- Consider creating a `NOTICES.txt` file with third-party licenses
