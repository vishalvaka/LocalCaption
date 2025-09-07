#!/usr/bin/env python3
"""
LocalCaption Launcher Script
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    # Import and run the main application
    from localcaption.main import main
    main()
