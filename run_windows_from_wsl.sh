#!/bin/bash
# LocalCaption - Run Windows version from WSL

echo "LocalCaption - WSL to Windows Bridge"
echo "===================================="

# Get Windows path
WINDOWS_PATH="/mnt/c/Users/$USER/Desktop/LocalCaption"

# Check if Windows path exists
if [ ! -d "$WINDOWS_PATH" ]; then
    echo "Windows path not found: $WINDOWS_PATH"
    echo "Please copy LocalCaption to your Windows Desktop"
    echo "Or update the WINDOWS_PATH variable in this script"
    exit 1
fi

# Copy current files to Windows
echo "Copying files to Windows..."
cp -r . "$WINDOWS_PATH/"

# Run Windows batch file
echo "Running LocalCaption on Windows..."
cd "$WINDOWS_PATH"
cmd.exe /c "run_on_windows.bat"
