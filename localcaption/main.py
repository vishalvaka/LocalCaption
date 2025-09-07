"""
LocalCaption - Main application entry point
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from localcaption.ui.main_window import main as ui_main


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('localcaption.log')
        ]
    )


def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import sounddevice
    except ImportError:
        missing_deps.append("sounddevice")
    
    try:
        import sherpa_onnx
    except ImportError:
        missing_deps.append("sherpa-onnx")
    
    try:
        from PyQt6 import QtWidgets
    except ImportError:
        missing_deps.append("PyQt6")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import psutil
    except ImportError:
        missing_deps.append("psutil")
    
    if missing_deps:
        print("Missing dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install missing dependencies:")
        print(f"pip install {' '.join(missing_deps)}")
        return False
    
    return True


def check_models():
    """Check if ASR models are available"""
    models_dir = Path("models")
    if not models_dir.exists():
        print("Models directory not found. Creating...")
        models_dir.mkdir(exist_ok=True)
        return False
    
    # Check for specific model files
    model_files = list(models_dir.glob("**/*.yaml")) + list(models_dir.glob("**/*.onnx"))
    if not model_files:
        print("No ASR models found in models/ directory.")
        print("Please download models from:")
        print("https://github.com/k2-fsa/sherpa-onnx/releases")
        return False
    
    return True


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description="LocalCaption - Live captions for any audio")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies and exit")
    parser.add_argument("--check-models", action="store_true", help="Check models and exit")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    if args.check_deps:
        if check_dependencies():
            print("All dependencies are available.")
            sys.exit(0)
        else:
            sys.exit(1)
    
    if args.check_models:
        if check_models():
            print("ASR models are available.")
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Missing dependencies. Please install them first.")
        sys.exit(1)
    
    # Check models
    if not check_models():
        logger.warning("ASR models not found. Some features may not work.")
    
    # Start the application
    try:
        logger.info("Starting LocalCaption...")
        ui_main()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
