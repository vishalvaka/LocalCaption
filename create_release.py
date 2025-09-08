#!/usr/bin/env python3
"""
Release creation script for LocalCaption
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path
import datetime
import time
import stat

def run_command(cmd, cwd=None):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {cmd}")
            print(f"Error output: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Exception running command {cmd}: {e}")
        return False


def kill_localcaption_processes():
    """Attempt to kill any running LocalCaption executables (Windows-safe)."""
    print("Ensuring no running LocalCaption processes...")
    if os.name == 'nt':
        # Try multiple ways quietly
        commands = [
            'taskkill /IM LocalCaption.exe /F /T >nul 2>&1',
            'powershell -NoProfile -Command "Get-Process LocalCaption -ErrorAction SilentlyContinue | Stop-Process -Force"'
        ]
        for cmd in commands:
            try:
                subprocess.run(cmd, shell=True)
            except Exception:
                pass
        time.sleep(0.3)


def _on_remove_error(func, path, exc_info):
    """Make files writable and retry removal on Windows."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def robust_remove(path):
    """Remove a file if it exists, handling Windows locking."""
    if not os.path.exists(path):
        return True
    for _ in range(3):
        try:
            os.remove(path)
            return True
        except PermissionError:
            kill_localcaption_processes()
            time.sleep(0.4)
        except Exception:
            break
    print(f"Warning: Could not remove file: {path}")
    return False


def robust_rmtree(path):
    """Remove a directory tree if it exists, retrying on Windows locks."""
    if not os.path.exists(path):
        return True
    for _ in range(3):
        try:
            shutil.rmtree(path, onerror=_on_remove_error)
            print(f"Removed {path}")
            return True
        except PermissionError:
            kill_localcaption_processes()
            time.sleep(0.6)
        except Exception:
            break
    print(f"Warning: Could not remove directory: {path}")
    return False

def clean_build():
    """Clean previous build artifacts"""
    print("Cleaning previous build artifacts...")
    kill_localcaption_processes()
    # First try to remove the main exe if it exists to unlock the folder
    robust_remove(os.path.join('dist', 'LocalCaption.exe'))
    # Then remove standard build dirs
    for dir_name in ['build', 'dist', '__pycache__', 'LocalCaption-Release']:
        robust_rmtree(dir_name)
    
    # Clean .pyc files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable with PyInstaller...")
    
    # Update PyInstaller spec file
    spec_file = "build.spec"
    if not os.path.exists(spec_file):
        print(f"Error: {spec_file} not found!")
        return False
    
    # Run PyInstaller
    cmd = f"pyinstaller {spec_file} --clean --noconfirm --log-level=WARN"
    if not run_command(cmd):
        print("Failed to build executable")
        return False
    
    print("Executable built successfully!")
    return True

def create_portable_package():
    """Create a portable package"""
    print("Creating portable package...")
    
    # Create release directory
    release_dir = "LocalCaption-Release"
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)
    
    # Copy executable
    exe_path = "dist/LocalCaption.exe"
    if os.path.exists(exe_path):
        shutil.copy2(exe_path, release_dir)
        print(f"Copied {exe_path} to {release_dir}")
    else:
        print(f"Error: {exe_path} not found!")
        return False
    
    # Copy models directory
    if os.path.exists("models"):
        shutil.copytree("models", os.path.join(release_dir, "models"))
        print("Copied models directory")
    
    # Copy documentation
    files_to_copy = ["README.md", "requirements.txt", "LICENSE"]
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, release_dir)
            print(f"Copied {file}")
    
    # Create run script
    run_script = os.path.join(release_dir, "run_localcaption.bat")
    with open(run_script, "w") as f:
        f.write("""@echo off
echo Starting LocalCaption...
LocalCaption.exe
pause
""")
    print("Created run script")
    
    # Create version info
    version_file = os.path.join(release_dir, "VERSION.txt")
    with open(version_file, "w") as f:
        f.write(f"""LocalCaption v1.0.0
Build Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Python Version: {sys.version}
Platform: {sys.platform}

This is a portable version of LocalCaption.
Simply run LocalCaption.exe to start the application.

For more information, see README.md
""")
    print("Created version info")
    
    return release_dir

def create_zip_package(release_dir):
    """Create a ZIP package of the release"""
    print("Creating ZIP package...")
    
    zip_filename = f"LocalCaption-v1.0.0-Windows-{datetime.datetime.now().strftime('%Y%m%d')}.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, os.path.dirname(release_dir))
                zipf.write(file_path, arc_path)
    
    print(f"Created ZIP package: {zip_filename}")
    return zip_filename

def create_installer_script():
    """Create an installer script"""
    print("Creating installer script...")
    
    installer_script = "install_localcaption.bat"
    with open(installer_script, "w") as f:
        f.write("""@echo off
echo LocalCaption Installer
echo =====================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Installing LocalCaption...
pip install -e .

echo.
echo Installation complete!
echo You can now run LocalCaption with: python -m localcaption
echo.
pause
""")
    print(f"Created installer script: {installer_script}")

def main():
    """Main release creation process"""
    print("LocalCaption Release Creator")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("localcaption") or not os.path.exists("run.py"):
        print("Error: Please run this script from the LocalCaption project root directory")
        return False
    
    # Clean previous builds
    clean_build()
    
    # Build executable
    if not build_executable():
        print("Failed to build executable")
        return False
    
    # Create portable package
    release_dir = create_portable_package()
    if not release_dir:
        print("Failed to create portable package")
        return False
    
    # Create ZIP package
    zip_file = create_zip_package(release_dir)
    
    # Create installer script
    create_installer_script()
    
    print("\n" + "=" * 40)
    print("RELEASE CREATION COMPLETE!")
    print("=" * 40)
    print(f"Portable package: {release_dir}/")
    print(f"ZIP package: {zip_file}")
    print(f"Installer script: install_localcaption.bat")
    print("\nTo distribute:")
    print(f"1. Share the ZIP file: {zip_file}")
    print("2. Or share the portable folder: LocalCaption-Release/")
    print("3. Or use the installer script for Python users")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
