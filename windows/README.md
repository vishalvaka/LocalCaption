# Windows Scripts

This directory contains Windows-specific launcher scripts for LocalCaption.

## Scripts

- **`run_on_windows.bat`** - Standard Windows batch launcher
- **`run_on_windows.ps1`** - PowerShell launcher (alternative)
- **`debug_windows.bat`** - Debug launcher with verbose output

## Usage

### Standard Launch
```cmd
windows\run_on_windows.bat
```

### PowerShell Launch
```powershell
.\windows\run_on_windows.ps1
```

### Debug Mode
```cmd
windows\debug_windows.bat
```

## Requirements

- Python 3.8+ installed and in PATH
- Windows 10/11
- Audio device with loopback capability

## Troubleshooting

If the application crashes:
1. Run `debug_windows.bat` to see detailed error messages
2. Check `localcaption.log` for error details
3. Run `python tests/test_windows.py` to test components
